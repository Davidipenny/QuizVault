from __future__ import annotations

import json
import os
import random
import base64
import tempfile
import io
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .config import API_PREFIX, APP_NAME, data_dir, database_path, frontend_dist_dir, legacy_banks_dir
from .backups import MAX_BACKUP_SIZE, backup_info, create_backup as create_database_backup, restore_database, validate_database
from .database import Base, engine, get_db
from .domain import grade_answer, question_fingerprint, validate_question
from .importers import load_legacy_bank, parse_source
from .models import (
    Choice, Collection, CollectionQuestion, ImportJob, LegacyMapping, Question,
    QuestionBank, QuizAnswer, QuizSession, StudyState, User, Workspace, now,
)
from .serializers import bank_dict, question_dict, session_dict, state_dict


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title=APP_NAME, version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def local_token_guard(request: Request, call_next):
    token = os.getenv("QUIZVAULT_ACCESS_TOKEN")
    if token and request.url.path.startswith(API_PREFIX):
        supplied = request.headers.get("X-QuizVault-Token") or request.query_params.get("token")
        if supplied != token:
            return Response(status_code=401, content="Unauthorized")
    return await call_next(request)


def initialize_database():
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        workspace = db.scalar(select(Workspace).limit(1))
        if not workspace:
            workspace = Workspace(name="本地空间")
            db.add(workspace)
            db.flush()
        if not db.scalar(select(User).limit(1)):
            db.add(User(workspace_id=workspace.id, display_name="本地用户"))
        db.commit()
    today = datetime.now().strftime("%Y%m%d")
    if database_path().exists() and not any((data_dir() / "backups").glob(f"quizvault-{today}-*.db")):
        create_backup()


def local_user(db: Session) -> User:
    user = db.scalar(select(User).limit(1))
    if not user:
        initialize_database()
        user = db.scalar(select(User).limit(1))
    return user


def get_bank(db: Session, bank_id: str) -> QuestionBank:
    bank = db.get(QuestionBank, bank_id)
    if not bank:
        raise HTTPException(404, "题库不存在")
    return bank


def get_question(db: Session, question_id: str) -> Question:
    question = db.scalar(select(Question).where(Question.id == question_id).options(selectinload(Question.choices)))
    if not question:
        raise HTTPException(404, "题目不存在")
    return question


def create_question(db: Session, bank_id: str, payload: dict, sort_order: int = 0) -> Question:
    errors = validate_question(payload)
    if errors:
        raise ValueError("；".join(errors))
    fingerprint = question_fingerprint(payload)
    question = Question(
        bank_id=bank_id,
        type=payload["type"], prompt=payload["prompt"],
        case_material=payload.get("case_material", ""), explanation=payload.get("explanation", ""),
        source=payload.get("source", ""), sort_order=payload.get("sort_order", sort_order),
        answer_spec=payload["answer_spec"], fingerprint=fingerprint,
    )
    db.add(question)
    db.flush()
    for index, item in enumerate(payload.get("choices", [])):
        db.add(Choice(
            question_id=question.id, label=item.get("label", chr(65 + index)),
            content=item.get("content", ""), is_correct=item.get("is_correct", False),
            display_order=item.get("display_order", index),
        ))
    db.flush()
    db.refresh(question)
    return get_question(db, question.id)


@app.get(f"{API_PREFIX}/health")
def health():
    return {"status": "ok", "version": app.version}


@app.get(f"{API_PREFIX}/banks")
def list_banks(include_archived: bool = False, db: Session = Depends(get_db)):
    statement = select(QuestionBank).order_by(QuestionBank.updated_at.desc())
    if not include_archived:
        statement = statement.where(QuestionBank.archived.is_(False))
    banks = db.scalars(statement).all()
    counts = dict(db.execute(select(Question.bank_id, func.count()).group_by(Question.bank_id)).all())
    last = dict(db.execute(select(QuizSession.bank_id, func.max(QuizSession.updated_at)).group_by(QuizSession.bank_id)).all())
    return [bank_dict(bank, counts.get(bank.id, 0), last.get(bank.id)) for bank in banks]


@app.post(f"{API_PREFIX}/banks", status_code=201)
def add_bank(payload: dict, db: Session = Depends(get_db)):
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(422, "题库名称不能为空")
    user = local_user(db)
    bank = QuestionBank(
        workspace_id=user.workspace_id, name=name, description=payload.get("description", ""),
        tags=payload.get("tags", []), challenge_size=payload.get("challenge_size", 20),
    )
    db.add(bank)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "题库名称已存在")
    return bank_dict(bank)


@app.patch(f"{API_PREFIX}/banks/{{bank_id}}")
def update_bank(bank_id: str, payload: dict, db: Session = Depends(get_db)):
    bank = get_bank(db, bank_id)
    for field in ("name", "description", "tags", "challenge_size", "archived"):
        if field in payload:
            setattr(bank, field, payload[field])
    bank.version += 1
    db.commit()
    return bank_dict(bank, db.scalar(select(func.count()).where(Question.bank_id == bank.id)) or 0)


@app.delete(f"{API_PREFIX}/banks/{{bank_id}}", status_code=204)
def delete_bank(bank_id: str, db: Session = Depends(get_db)):
    db.delete(get_bank(db, bank_id))
    db.commit()


@app.post(f"{API_PREFIX}/banks/{{bank_id}}/merge")
def merge_bank(bank_id: str, payload: dict, db: Session = Depends(get_db)):
    target = get_bank(db, bank_id)
    source = get_bank(db, payload.get("source_bank_id", ""))
    copied = skipped = 0
    for question in db.scalars(select(Question).where(Question.bank_id == source.id).options(selectinload(Question.choices))).all():
        data = question_dict(question)
        exists = db.scalar(select(Question.id).where(and_(Question.bank_id == target.id, Question.fingerprint == question.fingerprint)))
        if exists:
            skipped += 1
            continue
        create_question(db, target.id, data)
        copied += 1
    db.commit()
    return {"copied": copied, "skipped": skipped}


@app.get(f"{API_PREFIX}/banks/{{bank_id}}/questions")
def list_questions(
    bank_id: str, page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=200),
    search: str = "", question_type: str = "", include_answer: bool = True,
    db: Session = Depends(get_db),
):
    get_bank(db, bank_id)
    filters = [Question.bank_id == bank_id]
    if search:
        filters.append(or_(Question.prompt.contains(search), Question.explanation.contains(search), Question.source.contains(search)))
    if question_type:
        filters.append(Question.type == question_type)
    total = db.scalar(select(func.count()).select_from(Question).where(*filters)) or 0
    items = db.scalars(
        select(Question).where(*filters).options(selectinload(Question.choices))
        .order_by(Question.sort_order, Question.created_at).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {"items": [question_dict(q, include_answer) for q in items], "total": total, "page": page, "page_size": page_size}


@app.post(f"{API_PREFIX}/banks/{{bank_id}}/questions", status_code=201)
def add_question(bank_id: str, payload: dict, db: Session = Depends(get_db)):
    get_bank(db, bank_id)
    try:
        question = create_question(db, bank_id, payload)
        db.commit()
        return question_dict(question)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc))
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "同一题库中已存在相同题目")


@app.put(f"{API_PREFIX}/questions/{{question_id}}")
def update_question(question_id: str, payload: dict, db: Session = Depends(get_db)):
    question = get_question(db, question_id)
    errors = validate_question(payload)
    if errors:
        raise HTTPException(422, "；".join(errors))
    for field in ("type", "prompt", "case_material", "explanation", "source", "sort_order", "answer_spec"):
        if field in payload:
            setattr(question, field, payload[field])
    question.fingerprint = question_fingerprint(payload)
    question.version += 1
    question.choices.clear()
    for index, item in enumerate(payload.get("choices", [])):
        question.choices.append(Choice(
            label=item.get("label", chr(65 + index)), content=item.get("content", ""),
            is_correct=item.get("is_correct", False), display_order=index,
        ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "同一题库中已存在相同题目")
    return question_dict(get_question(db, question_id))


@app.delete(f"{API_PREFIX}/questions/{{question_id}}", status_code=204)
def delete_question(question_id: str, db: Session = Depends(get_db)):
    db.delete(get_question(db, question_id))
    db.commit()


@app.post(f"{API_PREFIX}/questions/batch")
def batch_questions(payload: dict, db: Session = Depends(get_db)):
    ids = payload.get("question_ids", [])
    action = payload.get("action")
    questions = db.scalars(select(Question).where(Question.id.in_(ids)).options(selectinload(Question.choices))).all()
    changed = 0
    if action == "delete":
        for q in questions:
            db.delete(q)
            changed += 1
    elif action in {"move", "copy"}:
        target_id = payload.get("target_bank_id")
        get_bank(db, target_id)
        for q in questions:
            exists = db.scalar(select(Question.id).where(and_(Question.bank_id == target_id, Question.fingerprint == q.fingerprint)))
            if exists:
                continue
            create_question(db, target_id, question_dict(q))
            if action == "move":
                db.delete(q)
            changed += 1
    else:
        raise HTTPException(422, "批量操作无效")
    db.commit()
    return {"changed": changed}


@app.post(f"{API_PREFIX}/imports/preview", status_code=201)
def preview_import(payload: dict, db: Session = Depends(get_db)):
    bank = get_bank(db, payload.get("bank_id", ""))
    try:
        rows = parse_source(payload.get("source_type", "text"), payload.get("content", ""), payload.get("filename", ""))
    except Exception as exc:
        raise HTTPException(422, f"无法解析导入内容：{exc}")
    if len(rows) > 3000:
        raise HTTPException(422, "单次最多导入 3000 题")
    existing = set(db.scalars(select(Question.fingerprint).where(Question.bank_id == bank.id)).all())
    seen: set[str] = set()
    errors, valid = [], 0
    for index, row in enumerate(rows, 1):
        row_errors = validate_question(row)
        fingerprint = question_fingerprint(row)
        duplicate = fingerprint in existing or fingerprint in seen
        if duplicate:
            row_errors.append("重复题目")
        seen.add(fingerprint)
        row["_row"] = index
        row["_errors"] = row_errors
        row["_excluded"] = bool(row_errors)
        if row_errors:
            errors.append({"row": index, "messages": row_errors})
        else:
            valid += 1
    job = ImportJob(
        bank_id=bank.id, source_type=payload.get("source_type", "text"), rows=rows,
        errors=errors, stats={"total": len(rows), "valid": valid, "invalid": len(rows) - valid},
    )
    db.add(job)
    db.commit()
    return {"id": job.id, "rows": rows, "errors": errors, "stats": job.stats, "status": job.status}


@app.get(f"{API_PREFIX}/imports/template/excel")
def excel_template():
    from openpyxl import Workbook
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "题目"
    sheet.append(["题型", "题干", "材料", "A", "B", "C", "D", "答案", "解析", "答案无序"])
    sheet.append(["单选题", "示例题干", "", "选项一", "选项二", "", "", "A", "示例解析", ""])
    sheet.append(["填空题", "多个空的答案用分号分隔", "", "", "", "", "", "答案一;答案二", "", False])
    stream = io.BytesIO()
    workbook.save(stream)
    stream.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="QuizVault-import-template.xlsx"'}
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)


@app.patch(f"{API_PREFIX}/imports/{{job_id}}")
def edit_import(job_id: str, payload: dict, db: Session = Depends(get_db)):
    job = db.get(ImportJob, job_id)
    if not job or job.status != "preview":
        raise HTTPException(404, "导入预览不存在或已提交")
    rows = payload.get("rows", job.rows)
    errors = []
    for index, row in enumerate(rows, 1):
        row["_errors"] = [] if row.get("_excluded") else validate_question(row)
        if row["_errors"]:
            errors.append({"row": index, "messages": row["_errors"]})
    job.rows = rows
    job.errors = errors
    job.stats = {"total": len(rows), "valid": sum(not r.get("_excluded") and not r.get("_errors") for r in rows), "invalid": len(errors), "excluded": sum(bool(r.get("_excluded")) for r in rows)}
    db.commit()
    return {"id": job.id, "rows": job.rows, "errors": job.errors, "stats": job.stats}


@app.post(f"{API_PREFIX}/imports/{{job_id}}/commit")
def commit_import(job_id: str, db: Session = Depends(get_db)):
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(404, "导入任务不存在")
    if job.status == "committed":
        return {"id": job.id, "status": job.status, **job.stats}
    active = [row for row in job.rows if not row.get("_excluded")]
    invalid = [(row.get("_row"), validate_question(row)) for row in active if validate_question(row)]
    if invalid:
        raise HTTPException(422, {"message": "仍有未修正的题目", "rows": invalid})
    try:
        for index, row in enumerate(active):
            create_question(db, job.bank_id, row, index)
        job.status = "committed"
        job.committed_at = now()
        job.stats = {**job.stats, "committed": len(active)}
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(409, f"导入已回滚：{exc}")
    return {"id": job.id, "status": job.status, **job.stats}


@app.get(f"{API_PREFIX}/imports/{{job_id}}/errors")
def import_errors(job_id: str, db: Session = Depends(get_db)):
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(404, "导入任务不存在")
    return {"job_id": job.id, "source_type": job.source_type, "errors": job.errors, "stats": job.stats}


@app.get(f"{API_PREFIX}/migration/legacy/preview")
def legacy_preview(path: str = "", db: Session = Depends(get_db)):
    root = Path(path) if path else legacy_banks_dir()
    if not root.exists() or not root.is_dir():
        raise HTTPException(404, "旧版 banks 目录不存在")
    banks = []
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        try:
            questions = load_legacy_bank(folder)
            errors = sum(bool(validate_question(q)) for q in questions)
            banks.append({"name": folder.name, "path": str(folder), "questions": len(questions), "errors": errors})
        except Exception as exc:
            banks.append({"name": folder.name, "path": str(folder), "questions": 0, "errors": 1, "message": str(exc)})
    return {"root": str(root), "banks": banks, "total_questions": sum(x["questions"] for x in banks), "read_only": True}


@app.post(f"{API_PREFIX}/migration/legacy/commit")
def legacy_commit(payload: dict, db: Session = Depends(get_db)):
    root = Path(payload.get("path") or legacy_banks_dir())
    if not root.exists():
        raise HTTPException(404, "旧版目录不存在")
    create_backup()
    user = local_user(db)
    result = {"banks": 0, "questions": 0, "collections": 0, "sessions": 0, "skipped": 0, "invalid_questions": 0, "unmatched_states": 0}
    try:
        for folder in sorted(p for p in root.iterdir() if p.is_dir()):
            bank = db.scalar(select(QuestionBank).where(and_(QuestionBank.workspace_id == user.workspace_id, QuestionBank.name == folder.name)))
            if not bank:
                bank = QuestionBank(workspace_id=user.workspace_id, name=folder.name, description="从旧版 QuizVault 迁移")
                db.add(bank)
                db.flush()
                result["banks"] += 1
            id_map: dict[tuple, str] = {}
            ordered_question_ids: list[str] = []
            legacy_items = load_legacy_bank(folder)
            for index, item in enumerate(legacy_items):
                if validate_question(item):
                    result["invalid_questions"] += 1
                    continue
                legacy_key = f"{folder.resolve()}|{item.get('source')}|{index}|{item['type']}"
                mapping = db.get(LegacyMapping, legacy_key)
                if mapping:
                    result["skipped"] += 1
                    id_map[(item.get("_legacy_id"), item["type"])] = mapping.question_id
                    ordered_question_ids.append(mapping.question_id)
                    continue
                existing = db.scalar(select(Question).where(and_(Question.bank_id == bank.id, Question.fingerprint == question_fingerprint(item))))
                if existing:
                    question = existing
                    result["skipped"] += 1
                else:
                    question = create_question(db, bank.id, item, index)
                    result["questions"] += 1
                db.add(LegacyMapping(legacy_key=legacy_key, question_id=question.id))
                id_map[(item.get("_legacy_id"), item["type"])] = question.id
                ordered_question_ids.append(question.id)
            migrate_legacy_states(db, user.id, bank.id, folder, id_map, ordered_question_ids, result)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(422, f"迁移已回滚：{exc}")
    return result


def migrate_legacy_states(db: Session, user_id: str, bank_id: str, folder: Path, id_map: dict, ordered_question_ids: list[str], result: dict):
    state_files = {
        "wrong_questions.json": "wrong", "flagged.json": "flagged", "collections.json": "collection",
    }
    for filename, kind in state_files.items():
        file = folder / filename
        if not file.exists():
            continue
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except Exception:
            result["unmatched_states"] += 1
            continue
        if kind == "wrong":
            entries = data.get("questions", data) if isinstance(data, dict) else data
            for entry in entries if isinstance(entries, list) else []:
                question_id = id_map.get((entry.get("id"), entry.get("type")))
                if not question_id:
                    result["unmatched_states"] += 1
                    continue
                state = db.scalar(select(StudyState).where(and_(StudyState.user_id == user_id, StudyState.question_id == question_id))) or StudyState(user_id=user_id, question_id=question_id, wrong_count=0, favorite=False, note="", flagged=False, mastery="new")
                state.wrong_count = max(state.wrong_count or 0, int(entry.get("wrong_count", 1)))
                db.add(state)
        elif kind == "flagged":
            entries = data.get("flagged", data) if isinstance(data, dict) else data
            for entry in entries if isinstance(entries, list) else []:
                question_id = id_map.get((entry.get("id"), entry.get("type")))
                if question_id:
                    state = db.scalar(select(StudyState).where(and_(StudyState.user_id == user_id, StudyState.question_id == question_id))) or StudyState(user_id=user_id, question_id=question_id, wrong_count=0, favorite=False, note="", flagged=False, mastery="new")
                    state.flagged = True
                    db.add(state)
        elif kind == "collection":
            groups = data.get("collections", {}) if isinstance(data, dict) else {}
            for name, value in groups.items():
                entries = value.get("questions", []) if isinstance(value, dict) else value
                collection = db.scalar(select(Collection).where(and_(Collection.user_id == user_id, Collection.name == name)))
                if not collection:
                    collection = Collection(user_id=user_id, name=name)
                    db.add(collection)
                    db.flush()
                    result["collections"] += 1
                for entry in entries if isinstance(entries, list) else []:
                    question_id = id_map.get((entry.get("id"), entry.get("type")))
                    if not question_id:
                        result["unmatched_states"] += 1
                        continue
                    if not db.get(CollectionQuestion, (collection.id, question_id)):
                        db.add(CollectionQuestion(collection_id=collection.id, question_id=question_id))
                    state = db.scalar(select(StudyState).where(and_(StudyState.user_id == user_id, StudyState.question_id == question_id))) or StudyState(user_id=user_id, question_id=question_id, wrong_count=0, favorite=False, note="", flagged=False, mastery="new")
                    state.favorite = True
                    db.add(state)

    progress_file = folder / "quiz_progress.json"
    if not progress_file.exists() or not ordered_question_ids:
        return
    try:
        progress = json.loads(progress_file.read_text(encoding="utf-8"))
        source_key = str(progress_file.resolve())
        existing = db.scalars(select(QuizSession).where(and_(QuizSession.user_id == user_id, QuizSession.bank_id == bank_id, QuizSession.status == "active"))).all()
        if any(session.config.get("legacy_progress_source") == source_key for session in existing):
            return
        order = progress.get("question_order")
        if isinstance(order, list):
            question_order = [ordered_question_ids[index] for index in order if isinstance(index, int) and 0 <= index < len(ordered_question_ids)]
        else:
            question_order = list(ordered_question_ids)
        expected_total = int(progress.get("total_questions", len(question_order)))
        question_order = question_order[:expected_total]
        if not question_order:
            return
        config = {
            "scope": "all",
            "order": "random" if isinstance(order, list) else "sequential",
            "types": [] if progress.get("question_type") == "all" else [progress.get("question_type")],
            "legacy_mode": progress.get("mode"),
            "legacy_progress_source": source_key,
        }
        session = QuizSession(
            user_id=user_id, bank_id=bank_id, config=config, question_order=question_order,
            current_index=min(int(progress.get("current_idx", 0)), len(question_order) - 1), status="active",
        )
        db.add(session)
        db.flush()
        result["sessions"] += 1
        for index, answer in enumerate(progress.get("answers", [])):
            if index >= len(question_order) or not isinstance(answer, dict):
                break
            question = get_question(db, question_order[index])
            user_answer = str(answer.get("user_answer", "")).upper()
            db.add(QuizAnswer(
                session_id=session.id, question_id=question.id,
                answer={"selected": list(user_answer)}, question_snapshot=question_dict(question),
                is_correct=answer.get("is_correct"),
            ))
    except Exception:
        result["unmatched_states"] += 1


@app.post(f"{API_PREFIX}/quiz-sessions", status_code=201)
def create_quiz_session(payload: dict, db: Session = Depends(get_db)):
    bank_id = payload.get("bank_id", "")
    get_bank(db, bank_id)
    user = local_user(db)
    config = payload.get("config", {})
    filters = [Question.bank_id == bank_id]
    types = config.get("types") or []
    if types:
        filters.append(Question.type.in_(types))
    scope = config.get("scope", "all")
    if scope in {"wrong", "favorite", "unanswered"}:
        subquery = select(StudyState.question_id).where(StudyState.user_id == user.id)
        if scope == "wrong": subquery = subquery.where(StudyState.wrong_count > 0)
        if scope == "favorite": subquery = subquery.where(StudyState.favorite.is_(True))
        if scope == "unanswered": filters.append(~Question.id.in_(select(StudyState.question_id).where(and_(StudyState.user_id == user.id, StudyState.last_answered_at.is_not(None)))))
        else: filters.append(Question.id.in_(subquery))
    ids = list(db.scalars(select(Question.id).where(*filters).order_by(Question.sort_order)).all())
    if config.get("order") == "random":
        random.shuffle(ids)
    limit = int(config.get("limit") or 0)
    if limit > 0:
        ids = ids[:limit]
    if not ids:
        raise HTTPException(422, "当前范围没有可练习题目")
    if config.get("shuffle_options"):
        option_orders = {}
        choice_rows = db.execute(select(Choice.question_id, Choice.label).where(Choice.question_id.in_(ids)).order_by(Choice.display_order)).all()
        for question_id, label in choice_rows:
            option_orders.setdefault(question_id, []).append(label)
        for labels in option_orders.values():
            random.shuffle(labels)
        config["_option_orders"] = option_orders
    session = QuizSession(user_id=user.id, bank_id=bank_id, config=config, question_order=ids)
    db.add(session)
    db.commit()
    return session_dict(session)


@app.get(f"{API_PREFIX}/quiz-sessions/active")
def active_sessions(db: Session = Depends(get_db)):
    user = local_user(db)
    sessions = db.scalars(select(QuizSession).where(and_(QuizSession.user_id == user.id, QuizSession.status == "active")).order_by(QuizSession.updated_at.desc())).all()
    return [session_dict(s) for s in sessions]


@app.get(f"{API_PREFIX}/quiz-sessions/{{session_id}}")
def get_quiz_session(session_id: str, db: Session = Depends(get_db)):
    session = db.get(QuizSession, session_id)
    if not session:
        raise HTTPException(404, "刷题会话不存在")
    answers = db.scalars(select(QuizAnswer).where(QuizAnswer.session_id == session.id).order_by(QuizAnswer.answered_at)).all()
    questions = db.scalars(select(Question).where(Question.id.in_(session.question_order)).options(selectinload(Question.choices))).all()
    by_id = {q.id: q for q in questions}
    question_items = []
    option_orders = session.config.get("_option_orders", {})
    for qid in session.question_order:
        if qid not in by_id:
            continue
        item = question_dict(by_id[qid], include_answer=False)
        order = option_orders.get(qid, [])
        if order:
            rank = {label: index for index, label in enumerate(order)}
            item["choices"].sort(key=lambda choice: rank.get(choice["label"], 999))
        question_items.append(item)
    state_rows = db.scalars(select(StudyState).where(and_(StudyState.user_id == session.user_id, StudyState.question_id.in_(session.question_order)))).all()
    states = {state.question_id: state_dict(state) for state in state_rows}
    return {**session_dict(session, answers), "questions": question_items, "study_states": states}


@app.post(f"{API_PREFIX}/quiz-sessions/{{session_id}}/answers")
def submit_answer(session_id: str, payload: dict, db: Session = Depends(get_db)):
    session = db.get(QuizSession, session_id)
    if not session or session.status != "active":
        raise HTTPException(404, "活动会话不存在")
    question = get_question(db, payload.get("question_id", ""))
    if question.id not in session.question_order:
        raise HTTPException(422, "题目不属于该会话")
    user = local_user(db)
    answer = payload.get("answer", {})
    result = grade_answer(question_dict(question), answer, bool(session.config.get("compare_essay")))
    existing = db.scalar(select(QuizAnswer).where(and_(QuizAnswer.session_id == session.id, QuizAnswer.question_id == question.id)))
    snapshot = question_dict(question)
    if existing:
        existing.answer, existing.is_correct, existing.question_snapshot = answer, result, snapshot
        record = existing
    else:
        record = QuizAnswer(session_id=session.id, question_id=question.id, answer=answer, question_snapshot=snapshot, is_correct=result)
        db.add(record)
    state = db.scalar(select(StudyState).where(and_(StudyState.user_id == user.id, StudyState.question_id == question.id)))
    if not state:
        state = StudyState(user_id=user.id, question_id=question.id, wrong_count=0, favorite=False, note="", flagged=False, mastery="new")
        db.add(state)
    state.last_answered_at = now()
    if result is False:
        state.wrong_count += 1
        state.mastery = "learning"
    elif result is True:
        state.wrong_count = max(0, state.wrong_count - 1)
        state.mastery = "mastered" if state.wrong_count == 0 else "learning"
    index = session.question_order.index(question.id)
    session.current_index = max(session.current_index, index + 1)
    if session.current_index >= len(session.question_order):
        session.status, session.completed_at = "completed", now()
    db.commit()
    return {"is_correct": result, "correct_answer": question.answer_spec, "explanation": question.explanation, "session_status": session.status, "current_index": session.current_index}


@app.patch(f"{API_PREFIX}/quiz-sessions/{{session_id}}")
def update_session(session_id: str, payload: dict, db: Session = Depends(get_db)):
    session = db.get(QuizSession, session_id)
    if not session:
        raise HTTPException(404, "会话不存在")
    if "current_index" in payload:
        session.current_index = max(0, min(int(payload["current_index"]), len(session.question_order)))
    if payload.get("status") in {"active", "abandoned", "completed"}:
        session.status = payload["status"]
    db.commit()
    return session_dict(session)


@app.get(f"{API_PREFIX}/study-states")
def list_states(kind: str = "all", bank_id: str = "", page: int = 1, page_size: int = 50, db: Session = Depends(get_db)):
    user = local_user(db)
    filters = [StudyState.user_id == user.id]
    if kind == "wrong": filters.append(StudyState.wrong_count > 0)
    if kind == "favorite": filters.append(StudyState.favorite.is_(True))
    if kind == "note": filters.append(StudyState.note != "")
    if kind == "flagged": filters.append(StudyState.flagged.is_(True))
    statement = select(StudyState, Question).join(Question, Question.id == StudyState.question_id).where(*filters)
    if bank_id:
        statement = statement.where(Question.bank_id == bank_id)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.execute(statement.order_by(StudyState.last_answered_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [state_dict(state, question) for state, question in rows], "total": total}


@app.patch(f"{API_PREFIX}/study-states/{{question_id}}")
def update_state(question_id: str, payload: dict, db: Session = Depends(get_db)):
    get_question(db, question_id)
    user = local_user(db)
    state = db.scalar(select(StudyState).where(and_(StudyState.user_id == user.id, StudyState.question_id == question_id)))
    if not state:
        state = StudyState(user_id=user.id, question_id=question_id, wrong_count=0, favorite=False, note="", flagged=False, mastery="new")
        db.add(state)
    for field in ("favorite", "note", "flagged", "mastery", "wrong_count"):
        if field in payload:
            setattr(state, field, payload[field])
    db.commit()
    return state_dict(state)


@app.get(f"{API_PREFIX}/collections")
def list_collections(db: Session = Depends(get_db)):
    user = local_user(db)
    rows = db.execute(select(Collection, func.count(CollectionQuestion.question_id)).outerjoin(CollectionQuestion).where(Collection.user_id == user.id).group_by(Collection.id)).all()
    return [{"id": c.id, "name": c.name, "question_count": count, "created_at": c.created_at} for c, count in rows]


@app.get(f"{API_PREFIX}/collections/{{collection_id}}/questions")
def collection_questions(collection_id: str, db: Session = Depends(get_db)):
    collection = db.get(Collection, collection_id)
    if not collection:
        raise HTTPException(404, "收藏夹不存在")
    questions = db.scalars(select(Question).join(CollectionQuestion, CollectionQuestion.question_id == Question.id).where(CollectionQuestion.collection_id == collection_id).options(selectinload(Question.choices)).order_by(CollectionQuestion.added_at.desc())).all()
    return {"id": collection.id, "name": collection.name, "items": [question_dict(q) for q in questions]}


@app.patch(f"{API_PREFIX}/collections/{{collection_id}}")
def update_collection(collection_id: str, payload: dict, db: Session = Depends(get_db)):
    collection = db.get(Collection, collection_id)
    if not collection:
        raise HTTPException(404, "收藏夹不存在")
    if "name" in payload:
        collection.name = str(payload["name"]).strip()
    db.commit()
    return {"id": collection.id, "name": collection.name}


@app.delete(f"{API_PREFIX}/collections/{{collection_id}}", status_code=204)
def delete_collection(collection_id: str, db: Session = Depends(get_db)):
    collection = db.get(Collection, collection_id)
    if collection:
        db.delete(collection)
        db.commit()


@app.post(f"{API_PREFIX}/collections", status_code=201)
def add_collection(payload: dict, db: Session = Depends(get_db)):
    user = local_user(db)
    collection = Collection(user_id=user.id, name=str(payload.get("name", "")).strip())
    if not collection.name:
        raise HTTPException(422, "收藏夹名称不能为空")
    db.add(collection)
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "收藏夹名称已存在")
    return {"id": collection.id, "name": collection.name, "question_count": 0}


@app.post(f"{API_PREFIX}/collections/{{collection_id}}/questions")
def add_collection_question(collection_id: str, payload: dict, db: Session = Depends(get_db)):
    if not db.get(Collection, collection_id): raise HTTPException(404, "收藏夹不存在")
    get_question(db, payload.get("question_id", ""))
    item = CollectionQuestion(collection_id=collection_id, question_id=payload["question_id"])
    db.add(item)
    try: db.commit()
    except IntegrityError: db.rollback()
    return {"ok": True}


@app.delete(f"{API_PREFIX}/collections/{{collection_id}}/questions/{{question_id}}", status_code=204)
def remove_collection_question(collection_id: str, question_id: str, db: Session = Depends(get_db)):
    item = db.get(CollectionQuestion, (collection_id, question_id))
    if item: db.delete(item); db.commit()


@app.get(f"{API_PREFIX}/stats")
def stats(db: Session = Depends(get_db)):
    user = local_user(db)
    total_answers = db.scalar(select(func.count()).select_from(QuizAnswer).join(QuizSession).where(QuizSession.user_id == user.id)) or 0
    correct = db.scalar(select(func.count()).select_from(QuizAnswer).join(QuizSession).where(and_(QuizSession.user_id == user.id, QuizAnswer.is_correct.is_(True)))) or 0
    return {
        "banks": db.scalar(select(func.count()).select_from(QuestionBank).where(QuestionBank.archived.is_(False))) or 0,
        "questions": db.scalar(select(func.count()).select_from(Question)) or 0,
        "answers": total_answers,
        "correct": correct,
        "accuracy": round(correct / total_answers * 100, 1) if total_answers else 0,
        "wrong": db.scalar(select(func.count()).select_from(StudyState).where(and_(StudyState.user_id == user.id, StudyState.wrong_count > 0))) or 0,
        "favorites": db.scalar(select(func.count()).select_from(StudyState).where(and_(StudyState.user_id == user.id, StudyState.favorite.is_(True)))) or 0,
    }


@app.get(f"{API_PREFIX}/quiz-answers")
def answer_history(bank_id: str = "", page: int = 1, page_size: int = 50, db: Session = Depends(get_db)):
    user = local_user(db)
    filters = [QuizSession.user_id == user.id]
    if bank_id:
        filters.append(QuizSession.bank_id == bank_id)
    statement = select(QuizAnswer, Question, QuestionBank).join(QuizSession, QuizSession.id == QuizAnswer.session_id).join(Question, Question.id == QuizAnswer.question_id).join(QuestionBank, QuestionBank.id == QuizSession.bank_id).where(*filters)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.execute(statement.order_by(QuizAnswer.answered_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"total": total, "items": [{"id": answer.id, "answer": answer.answer, "is_correct": answer.is_correct, "answered_at": answer.answered_at, "question": question_dict(question), "bank_name": bank.name} for answer, question, bank in rows]}


def create_backup() -> Path:
    return create_database_backup(database_path(), data_dir() / "backups")


@app.post(f"{API_PREFIX}/backups")
def backup():
    path = create_backup()
    return backup_info(path)


@app.get(f"{API_PREFIX}/backups")
def list_backups():
    return [backup_info(path) for path in sorted((data_dir() / "backups").glob("*.db"), reverse=True)]


@app.get(f"{API_PREFIX}/backups/{{filename}}")
def download_backup(filename: str):
    safe = Path(filename).name
    path = data_dir() / "backups" / safe
    if not path.exists(): raise HTTPException(404, "备份不存在")
    validation = validate_database(path)
    if not validation.valid:
        raise HTTPException(422, validation.error or "备份无效")
    return FileResponse(path, filename=safe, media_type="application/x-sqlite3")


@app.post(f"{API_PREFIX}/backups/restore")
def restore_backup(payload: dict):
    encoded = payload.get("content", "")
    if not encoded:
        raise HTTPException(422, "备份内容为空")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception:
        raise HTTPException(422, "备份编码无效")
    if len(raw) > MAX_BACKUP_SIZE:
        raise HTTPException(413, "备份文件过大")
    descriptor, temp_name = tempfile.mkstemp(prefix="restore-upload-", suffix=".db", dir=data_dir())
    os.close(descriptor)
    temp_path = Path(temp_name)
    try:
        temp_path.write_bytes(raw)
        restore_database(temp_path, database_path(), data_dir() / "backups", engine.dispose)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    finally:
        temp_path.unlink(missing_ok=True)
    return {"restored": True}


web_dist = frontend_dist_dir()
if web_dist.exists():
    app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
