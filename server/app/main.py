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
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .config import API_PREFIX, APP_NAME, data_dir, database_path, frontend_dist_dir, legacy_banks_dir
from .backups import MAX_BACKUP_SIZE, backup_info, create_backup as create_database_backup, restore_database, validate_database
from .database import engine, get_db, run_migrations
from .domain import grade_answer, question_fingerprint, validate_question
from .importers import normalize_type, parse_source, scan_legacy_bank
from .models import (
    Choice, Collection, CollectionQuestion, ImportErrorRecord, ImportJob, LegacyMapping, Question,
    QuestionBank, QuizAnswer, QuizSession, StudyState, User, Workspace, now,
)
from .serializers import bank_dict, question_dict, session_dict, state_dict
from .schemas import (
    AnswerSubmit, BankCreate, BankMerge, BankUpdate, BatchQuestions, CollectionCreate,
    CollectionQuestionAdd, CollectionUpdate, ImportEdit, ImportPreview, LegacyCommit,
    QuestionRequest, QuizSessionCreate, QuizSessionUpdate, RestoreRequest, StudyStateUpdate,
)


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
    run_migrations()
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
def add_bank(payload: BankCreate, db: Session = Depends(get_db)):
    payload = payload.model_dump()
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
def update_bank(bank_id: str, payload: BankUpdate, db: Session = Depends(get_db)):
    payload = payload.model_dump(exclude_unset=True)
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
def merge_bank(bank_id: str, payload: BankMerge, db: Session = Depends(get_db)):
    payload = payload.model_dump()
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
def add_question(bank_id: str, payload: QuestionRequest, db: Session = Depends(get_db)):
    payload = payload.model_dump()
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
def update_question(question_id: str, payload: QuestionRequest, db: Session = Depends(get_db)):
    payload = payload.model_dump()
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
def batch_questions(payload: BatchQuestions, db: Session = Depends(get_db)):
    payload = payload.model_dump()
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
def preview_import(payload: ImportPreview, db: Session = Depends(get_db)):
    payload = payload.model_dump()
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
    db.flush()
    for error in errors:
        db.add(ImportErrorRecord(job_id=job.id, row_number=error["row"], messages=error["messages"]))
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
def edit_import(job_id: str, payload: ImportEdit, db: Session = Depends(get_db)):
    payload = payload.model_dump()
    job = db.get(ImportJob, job_id)
    if not job or job.status != "preview":
        raise HTTPException(404, "导入预览不存在或已提交")
    rows = payload.get("rows", job.rows)
    errors = []
    existing = set(db.scalars(select(Question.fingerprint).where(Question.bank_id == job.bank_id)).all())
    seen: set[str] = set()
    for index, row in enumerate(rows, 1):
        row_errors = [] if row.get("_excluded") else validate_question(row)
        fingerprint = question_fingerprint(row)
        if not row.get("_excluded") and (fingerprint in existing or fingerprint in seen):
            row_errors.append("重复题目")
        row["_fingerprint"] = fingerprint
        row["_row"] = index
        row["_errors"] = row_errors
        seen.add(fingerprint)
        if row["_errors"]:
            errors.append({"row": index, "messages": row["_errors"]})
    job.rows = rows
    job.errors = errors
    job.stats = {"total": len(rows), "valid": sum(not r.get("_excluded") and not r.get("_errors") for r in rows), "invalid": len(errors), "excluded": sum(bool(r.get("_excluded")) for r in rows)}
    for record in db.scalars(select(ImportErrorRecord).where(ImportErrorRecord.job_id == job.id)).all():
        db.delete(record)
    for error in errors:
        db.add(ImportErrorRecord(job_id=job.id, row_number=error["row"], messages=error["messages"]))
    db.commit()
    return {"id": job.id, "rows": job.rows, "errors": job.errors, "stats": job.stats}


@app.post(f"{API_PREFIX}/imports/{{job_id}}/commit")
def commit_import(job_id: str, db: Session = Depends(get_db)):
    if db.bind and db.bind.dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
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
def import_errors(job_id: str, download: bool = False, db: Session = Depends(get_db)):
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(404, "导入任务不存在")
    records = db.scalars(select(ImportErrorRecord).where(ImportErrorRecord.job_id == job.id).order_by(ImportErrorRecord.row_number)).all()
    errors = [{"row": record.row_number, "messages": record.messages} for record in records]
    result = {"job_id": job.id, "source_type": job.source_type, "errors": errors, "stats": job.stats}
    if download:
        content = json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8")
        return Response(content=content, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="import-errors-{job.id}.json"'})
    return result


@app.get(f"{API_PREFIX}/migration/legacy/preview")
def legacy_preview(path: str = "", db: Session = Depends(get_db)):
    root = Path(path) if path else legacy_banks_dir()
    if not root.exists() or not root.is_dir():
        raise HTTPException(404, "旧版 banks 目录不存在")
    banks = []
    summary = {"migratable": 0, "invalid": 0, "duplicate": 0, "already_migrated": 0, "unmatched": 0}
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        try:
            scan = scan_legacy_bank(folder)
            candidates = _legacy_candidates(scan["questions"])
            stats = {"migratable": 0, "invalid": 0, "duplicate": scan["duplicates"], "already_migrated": 0, "unmatched": 0}
            user = local_user(db)
            bank = db.scalar(select(QuestionBank).where(and_(QuestionBank.workspace_id == user.workspace_id, QuestionBank.name == folder.name)))
            existing_fingerprints = set(db.scalars(select(Question.fingerprint).where(Question.bank_id == bank.id)).all()) if bank else set()
            for item in scan["questions"]:
                if validate_question(item):
                    stats["invalid"] += 1
                elif db.get(LegacyMapping, _legacy_key(folder, item)):
                    stats["already_migrated"] += 1
                elif question_fingerprint(item) in existing_fingerprints:
                    stats["duplicate"] += 1
                else:
                    stats["migratable"] += 1
            state_report = _analyze_legacy_states(folder, candidates)
            stats["unmatched"] = state_report["unmatched"]
            issues = [*scan["issues"], *state_report["issues"]]
            for key in summary:
                summary[key] += stats[key]
            banks.append({
                "name": folder.name, "path": str(folder), "questions": len(scan["questions"]),
                "errors": stats["invalid"] + len(issues), "stats": stats, "issues": issues,
                "deleted": scan["deleted"],
            })
        except Exception as exc:
            banks.append({"name": folder.name, "path": str(folder), "questions": 0, "errors": 1, "message": str(exc)})
    return {"root": str(root), "banks": banks, "total_questions": sum(x["questions"] for x in banks), "summary": summary, "read_only": True}


def _legacy_key(folder: Path, item: dict) -> str:
    directory = os.path.normcase(str(folder.resolve()))
    source = str(item.get("_legacy_source") or item.get("source") or "")
    return f"{directory}|{source}|{item.get('_legacy_id')}|{item['type']}"


def _legacy_candidates(items: list[dict]) -> dict[tuple, list[dict]]:
    candidates: dict[tuple, list[dict]] = {}
    for item in items:
        candidates.setdefault((item.get("_legacy_id"), normalize_type(item.get("type"))), []).append(item)
    return candidates


def _resolve_legacy_entry(entry: dict, candidates: dict[tuple, list[dict]]) -> dict | None:
    matches = candidates.get((entry.get("id"), normalize_type(entry.get("type"))), [])
    if len(matches) == 1:
        return matches[0]
    prompt = str(entry.get("question") or entry.get("prompt") or "").strip()
    if prompt:
        normalized = " ".join(prompt.split())
        narrowed = [item for item in matches if " ".join(str(item.get("prompt", "")).split()) == normalized]
        if len(narrowed) == 1:
            return narrowed[0]
    return None


def _read_legacy_json(folder: Path, filename: str, issues: list[dict]):
    path = folder / filename
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        issues.append({"file": filename, "message": f"状态文件无效：{exc}"})
        return None


def _wrong_entries(data) -> list[dict]:
    if isinstance(data, list):
        return [entry for entry in data if isinstance(entry, dict)]
    if not isinstance(data, dict):
        return []
    if isinstance(data.get("wrong_books"), dict):
        return [entry for book in data["wrong_books"].values() if isinstance(book, list) for entry in book if isinstance(entry, dict)]
    for key in ("wrong_questions", "questions"):
        if isinstance(data.get(key), list):
            return [entry for entry in data[key] if isinstance(entry, dict)]
    return []


def _analyze_legacy_states(folder: Path, candidates: dict[tuple, list[dict]]) -> dict:
    issues: list[dict] = []
    unmatched = matched = 0
    sources: list[tuple[str, list[dict]]] = []
    wrong_data = _read_legacy_json(folder, "wrong_questions.json", issues)
    sources.append(("wrong_questions.json", _wrong_entries(wrong_data)))
    flagged = _read_legacy_json(folder, "flagged.json", issues)
    flagged_entries = flagged.get("flagged", flagged) if isinstance(flagged, dict) else flagged
    sources.append(("flagged.json", flagged_entries if isinstance(flagged_entries, list) else []))
    collections = _read_legacy_json(folder, "collections.json", issues)
    groups = collections.get("collections", {}) if isinstance(collections, dict) else {}
    for name, value in groups.items():
        entries = value.get("questions", []) if isinstance(value, dict) else value
        sources.append((f"collections.json:{name}", entries if isinstance(entries, list) else []))
    progress = _read_legacy_json(folder, "quiz_progress.json", issues)
    if isinstance(progress, dict):
        sources.append(("quiz_progress.json:wrong_questions", progress.get("wrong_questions", [])))
    for source, entries in sources:
        for entry in entries:
            if not isinstance(entry, dict) or not _resolve_legacy_entry(entry, candidates):
                unmatched += 1
                issues.append({"file": source, "message": "无法匹配题目", "entry": entry})
            else:
                matched += 1
    return {"matched": matched, "unmatched": unmatched, "issues": issues}


@app.post(f"{API_PREFIX}/migration/legacy/commit")
def legacy_commit(payload: LegacyCommit, db: Session = Depends(get_db)):
    payload = payload.model_dump()
    root = Path(payload.get("path") or legacy_banks_dir())
    if not root.exists():
        raise HTTPException(404, "旧版目录不存在")
    create_backup()
    user = local_user(db)
    result = {"banks": 0, "questions": 0, "collections": 0, "sessions": 0, "skipped": 0, "invalid_questions": 0, "unmatched_states": 0, "issues": []}
    try:
        for folder in sorted(p for p in root.iterdir() if p.is_dir()):
            bank = db.scalar(select(QuestionBank).where(and_(QuestionBank.workspace_id == user.workspace_id, QuestionBank.name == folder.name)))
            if not bank:
                bank = QuestionBank(workspace_id=user.workspace_id, name=folder.name, description="从旧版 QuizVault 迁移")
                db.add(bank)
                db.flush()
                result["banks"] += 1
            scan = scan_legacy_bank(folder)
            result["issues"].extend({"bank": folder.name, **issue} for issue in scan["issues"])
            legacy_items = scan["questions"]
            source_order: list[str | None] = []
            for index, item in enumerate(legacy_items):
                if validate_question(item):
                    result["invalid_questions"] += 1
                    source_order.append(None)
                    continue
                legacy_key = _legacy_key(folder, item)
                mapping = db.get(LegacyMapping, legacy_key)
                if mapping:
                    result["skipped"] += 1
                    item["_target_id"] = mapping.question_id
                    source_order.append(mapping.question_id)
                    continue
                existing = db.scalar(select(Question).where(and_(Question.bank_id == bank.id, Question.fingerprint == question_fingerprint(item))))
                if existing:
                    question = existing
                    result["skipped"] += 1
                else:
                    question = create_question(db, bank.id, item, index)
                    result["questions"] += 1
                db.add(LegacyMapping(legacy_key=legacy_key, question_id=question.id))
                item["_target_id"] = question.id
                source_order.append(question.id)
            migrate_legacy_states(db, user.id, bank.id, folder, _legacy_candidates(legacy_items), source_order, result)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(422, f"迁移已回滚：{exc}")
    return result


def migrate_legacy_states(db: Session, user_id: str, bank_id: str, folder: Path, candidates: dict, source_order: list[str | None], result: dict):
    issues: list[dict] = []
    state_cache = {
        state.question_id: state
        for state in db.scalars(select(StudyState).where(StudyState.user_id == user_id)).all()
    }

    def resolve(entry):
        item = _resolve_legacy_entry(entry, candidates) if isinstance(entry, dict) else None
        if not item or not item.get("_target_id"):
            result["unmatched_states"] += 1
            result["issues"].append({"bank": folder.name, "message": "无法匹配状态题目", "entry": entry})
            return None
        return item["_target_id"]

    def state_for(question_id):
        state = state_cache.get(question_id)
        if not state:
            state = StudyState(user_id=user_id, question_id=question_id, wrong_count=0, favorite=False, note="", flagged=False, mastery="new")
            state_cache[question_id] = state
            db.add(state)
        return state

    wrong_data = _read_legacy_json(folder, "wrong_questions.json", issues)
    for entry in _wrong_entries(wrong_data):
        question_id = resolve(entry)
        if question_id:
            state = state_for(question_id)
            state.wrong_count = max(state.wrong_count or 0, max(0, int(entry.get("wrong_count", 1))))
            state.mastery = "learning" if state.wrong_count else state.mastery

    flagged_data = _read_legacy_json(folder, "flagged.json", issues)
    flagged_entries = flagged_data.get("flagged", flagged_data) if isinstance(flagged_data, dict) else flagged_data
    for entry in flagged_entries if isinstance(flagged_entries, list) else []:
        question_id = resolve(entry)
        if question_id:
            state_for(question_id).flagged = True

    collection_data = _read_legacy_json(folder, "collections.json", issues)
    groups = collection_data.get("collections", {}) if isinstance(collection_data, dict) else {}
    for name, value in groups.items():
        entries = value.get("questions", []) if isinstance(value, dict) else value
        collection = db.scalar(select(Collection).where(and_(Collection.user_id == user_id, Collection.name == str(name))))
        if not collection:
            collection = Collection(user_id=user_id, name=str(name))
            db.add(collection)
            db.flush()
            result["collections"] += 1
        for entry in entries if isinstance(entries, list) else []:
            question_id = resolve(entry)
            if not question_id:
                continue
            if not db.get(CollectionQuestion, (collection.id, question_id)):
                db.add(CollectionQuestion(collection_id=collection.id, question_id=question_id))
            state_for(question_id).favorite = True

    result["issues"].extend({"bank": folder.name, **issue} for issue in issues)
    progress_file = folder / "quiz_progress.json"
    if not progress_file.exists() or not any(source_order):
        return
    try:
        progress = json.loads(progress_file.read_text(encoding="utf-8"))
        source_key = os.path.normcase(str(progress_file.resolve()))
        existing = db.scalars(select(QuizSession).where(and_(QuizSession.user_id == user_id, QuizSession.bank_id == bank_id))).all()
        if any(session.config.get("legacy_progress_source") == source_key for session in existing):
            return
        order = progress.get("question_order")
        if isinstance(order, list):
            raw_order = [source_order[index] if isinstance(index, int) and 0 <= index < len(source_order) else None for index in order]
        else:
            raw_order = list(source_order)
        expected_total = int(progress.get("total_questions", len(raw_order)))
        raw_order = raw_order[:expected_total]
        question_order = [question_id for question_id in raw_order if question_id]
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
            current_index=min(sum(bool(question_id) for question_id in raw_order[:max(0, int(progress.get("current_idx", 0)))]), len(question_order) - 1), status="active",
        )
        db.add(session)
        db.flush()
        result["sessions"] += 1
        for index, answer in enumerate(progress.get("answers", [])):
            if index >= len(raw_order) or not isinstance(answer, dict):
                break
            question_id = raw_order[index]
            if not question_id:
                continue
            question = get_question(db, question_id)
            user_answer = str(answer.get("user_answer", "")).upper()
            db.add(QuizAnswer(
                session_id=session.id, question_id=question.id,
                answer={"selected": list(user_answer)}, question_snapshot=question_dict(question),
                is_correct=answer.get("is_correct"),
            ))
    except Exception as exc:
        result["unmatched_states"] += 1
        result["issues"].append({"bank": folder.name, "file": "quiz_progress.json", "message": str(exc)})


@app.post(f"{API_PREFIX}/quiz-sessions", status_code=201)
def create_quiz_session(payload: QuizSessionCreate, db: Session = Depends(get_db)):
    payload = payload.model_dump()
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
    study_mode = bool(session.config.get("study_mode"))
    for qid in session.question_order:
        if qid not in by_id:
            continue
        item = question_dict(by_id[qid], include_answer=study_mode)
        order = option_orders.get(qid, [])
        if order:
            rank = {label: index for index, label in enumerate(order)}
            item["choices"].sort(key=lambda choice: rank.get(choice["label"], 999))
        question_items.append(item)
    state_rows = db.scalars(select(StudyState).where(and_(StudyState.user_id == session.user_id, StudyState.question_id.in_(session.question_order)))).all()
    states = {state.question_id: state_dict(state) for state in state_rows}
    return {**session_dict(session, answers), "questions": question_items, "study_states": states}


@app.post(f"{API_PREFIX}/quiz-sessions/{{session_id}}/answers")
def submit_answer(session_id: str, payload: AnswerSubmit, db: Session = Depends(get_db)):
    payload = payload.model_dump()
    session = db.get(QuizSession, session_id)
    if not session:
        raise HTTPException(404, "活动会话不存在")
    question = get_question(db, payload.get("question_id", ""))
    if question.id not in session.question_order:
        raise HTTPException(422, "题目不属于该会话")
    user = local_user(db)
    answer = payload.get("answer", {})
    result = grade_answer(question_dict(question), answer, bool(session.config.get("compare_essay")))
    existing = db.scalar(select(QuizAnswer).where(and_(QuizAnswer.session_id == session.id, QuizAnswer.question_id == question.id)))
    if session.status != "active" and not existing:
        raise HTTPException(404, "活动会话不存在")
    previous_wrong = int(bool(existing and existing.is_correct is False))
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
    state.wrong_count = max(0, state.wrong_count + int(result is False) - previous_wrong)
    if result is False:
        state.mastery = "learning"
    elif result is True:
        state.mastery = "mastered" if state.wrong_count == 0 else "learning"
    index = session.question_order.index(question.id)
    session.current_index = max(session.current_index, index + 1)
    if session.current_index >= len(session.question_order):
        session.status, session.completed_at = "completed", now()
    db.commit()
    return {"is_correct": result, "correct_answer": question.answer_spec, "explanation": question.explanation, "session_status": session.status, "current_index": session.current_index}


@app.patch(f"{API_PREFIX}/quiz-sessions/{{session_id}}")
def update_session(session_id: str, payload: QuizSessionUpdate, db: Session = Depends(get_db)):
    payload = payload.model_dump(exclude_unset=True)
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
def list_states(kind: Literal["all", "wrong", "favorite", "note", "flagged", "unanswered"] = "all", bank_id: str = "", page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    user = local_user(db)
    if kind == "unanswered":
        join_condition = and_(StudyState.question_id == Question.id, StudyState.user_id == user.id)
        statement = select(Question, StudyState).outerjoin(StudyState, join_condition).where(StudyState.last_answered_at.is_(None))
        if bank_id:
            statement = statement.where(Question.bank_id == bank_id)
        total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        rows = db.execute(statement.order_by(Question.sort_order, Question.created_at).offset((page - 1) * page_size).limit(page_size)).all()
        return {
            "items": [{
                "id": state.id if state else None,
                "question_id": question.id,
                "wrong_count": state.wrong_count if state else 0,
                "favorite": state.favorite if state else False,
                "note": state.note if state else "",
                "flagged": state.flagged if state else False,
                "last_answered_at": None,
                "mastery": state.mastery if state else "new",
                "question": question_dict(question),
            } for question, state in rows],
            "total": total,
        }
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
def update_state(question_id: str, payload: StudyStateUpdate, db: Session = Depends(get_db)):
    payload = payload.model_dump(exclude_unset=True)
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
def update_collection(collection_id: str, payload: CollectionUpdate, db: Session = Depends(get_db)):
    payload = payload.model_dump()
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
def add_collection(payload: CollectionCreate, db: Session = Depends(get_db)):
    payload = payload.model_dump()
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
def add_collection_question(collection_id: str, payload: CollectionQuestionAdd, db: Session = Depends(get_db)):
    payload = payload.model_dump()
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
def answer_history(bank_id: str = "", page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
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
def restore_backup(payload: RestoreRequest):
    payload = payload.model_dump()
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
        run_migrations()
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    finally:
        temp_path.unlink(missing_ok=True)
    return {"restored": True}


web_dist = frontend_dist_dir()
if web_dist.exists():
    app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
