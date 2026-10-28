import base64
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.main as main_module
from app.database import SessionLocal
from app.main import app, auto_import_legacy_banks
from app.models import Question, QuestionBank, QuizAnswer


def single_question(prompt):
    return {
        "type": "single", "prompt": prompt, "answer_spec": {"correct": ["A"]},
        "choices": [{"label": "A", "content": "甲"}, {"label": "B", "content": "乙"}],
    }


def test_update_bank_rename_conflict_returns_409():
    with TestClient(app) as client:
        first = client.post("/api/v1/banks", json={"name": "重命名冲突甲"}).json()
        client.post("/api/v1/banks", json={"name": "重命名冲突乙"})
        conflict = client.patch(f"/api/v1/banks/{first['id']}", json={"name": "重命名冲突乙"})
        assert conflict.status_code == 409
        assert conflict.json()["detail"] == "题库名称已存在"
        valid = client.patch(f"/api/v1/banks/{first['id']}", json={"name": "重命名成功"})
        assert valid.status_code == 200


def test_startup_import_reuses_bank_after_user_rename(tmp_path, monkeypatch):
    root = tmp_path / "banks"
    folder = root / "改名回归题库"
    folder.mkdir(parents=True)
    folder.joinpath("questions.md").write_text(
        "## 单选题\n\n**1. 改名后仍应复用（　）**\nA. 甲\nB. 乙\n\n**答案：A**",
        encoding="utf-8",
    )
    monkeypatch.setenv("QUIZVAULT_LEGACY_BANKS", str(root))

    with TestClient(app):
        first = auto_import_legacy_banks()
        assert first and first["banks"] == 1 and first["questions"] == 1
        with SessionLocal() as db:
            bank = db.scalar(select(QuestionBank).where(QuestionBank.name == folder.name))
            bank.name = "用户改过的名字"
            db.commit()

        repeated = auto_import_legacy_banks()
        assert repeated and repeated["banks"] == 0 and repeated["questions"] == 0
        with SessionLocal() as db:
            assert db.scalar(select(QuestionBank).where(QuestionBank.name == folder.name)) is None
            renamed = db.scalar(select(QuestionBank).where(QuestionBank.name == "用户改过的名字"))
            assert renamed is not None
            assert db.scalar(select(func.count()).select_from(Question).where(Question.bank_id == renamed.id)) == 1


def test_concurrent_answer_submission_stays_idempotent():
    with TestClient(app) as client:
        bank = client.post("/api/v1/banks", json={"name": "并发答题题库"}).json()
        question = client.post(f"/api/v1/banks/{bank['id']}/questions", json=single_question("并发提交同一题")).json()
        session = client.post("/api/v1/quiz-sessions", json={"bank_id": bank["id"], "config": {}}).json()
        endpoint = f"/api/v1/quiz-sessions/{session['id']}/answers"

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(
                lambda _: client.post(endpoint, json={"question_id": question["id"], "answer": {"selected": ["A"]}}),
                range(2),
            ))

        assert all(response.status_code == 200 for response in responses)
        with SessionLocal() as db:
            answers = db.scalars(select(QuizAnswer).where(QuizAnswer.session_id == session["id"])).all()
            assert len(answers) == 1


def test_restore_rejects_invalid_payloads_without_touching_database():
    with TestClient(app) as client:
        assert client.post("/api/v1/backups/restore", json={"content": " "}).status_code == 422
        assert client.post("/api/v1/backups/restore", json={"content": "!!!not-base64!!!"}).status_code == 422
        not_sqlite = base64.b64encode("这不是一个 SQLite 数据库".encode()).decode()
        rejected = client.post("/api/v1/backups/restore", json={"content": not_sqlite})
        assert rejected.status_code == 422
        assert client.get("/api/v1/banks").status_code == 200


def test_restore_rejects_oversized_payload(monkeypatch):
    monkeypatch.setattr(main_module, "MAX_BACKUP_SIZE", 8)
    with TestClient(app) as client:
        oversized = base64.b64encode(b"0123456789abcdef").decode()
        response = client.post("/api/v1/backups/restore", json={"content": oversized})
        assert response.status_code == 413


def test_backup_restore_round_trip_over_http():
    with TestClient(app) as client:
        client.post("/api/v1/banks", json={"name": "恢复往返题库"})
        created = client.post("/api/v1/backups").json()
        content = client.get(f"/api/v1/backups/{Path(created['filename']).name}")
        assert content.status_code == 200

        encoded = base64.b64encode(content.content).decode()
        restored = client.post("/api/v1/backups/restore", json={"content": encoded})
        assert restored.status_code == 200
        names = [bank["name"] for bank in client.get("/api/v1/banks").json()]
        assert "恢复往返题库" in names


def test_merge_bank_copies_and_skips_duplicates():
    with TestClient(app) as client:
        target = client.post("/api/v1/banks", json={"name": "合并目标题库"}).json()
        source = client.post("/api/v1/banks", json={"name": "合并来源题库"}).json()
        client.post(f"/api/v1/banks/{target['id']}/questions", json=single_question("合并重复题"))
        client.post(f"/api/v1/banks/{source['id']}/questions", json=single_question("合并重复题"))
        client.post(f"/api/v1/banks/{source['id']}/questions", json=single_question("合并新题"))

        result = client.post(f"/api/v1/banks/{target['id']}/merge", json={"source_bank_id": source["id"]}).json()

        assert result == {"copied": 1, "skipped": 1}
        assert client.get(f"/api/v1/banks/{target['id']}/questions").json()["total"] == 2


def test_batch_questions_copy_move_delete_and_missing_target():
    with TestClient(app) as client:
        first = client.post("/api/v1/banks", json={"name": "批量题库甲"}).json()
        second = client.post("/api/v1/banks", json={"name": "批量题库乙"}).json()
        third = client.post("/api/v1/banks", json={"name": "批量题库丙"}).json()
        kept = client.post(f"/api/v1/banks/{first['id']}/questions", json=single_question("批量保留题")).json()
        moved = client.post(f"/api/v1/banks/{second['id']}/questions", json=single_question("批量移动题")).json()

        def batch(action, target_bank_id=None, ids=None):
            payload = {"action": action, "question_ids": ids or []}
            if target_bank_id is not None:
                payload["target_bank_id"] = target_bank_id
            return client.post("/api/v1/questions/batch", json=payload)

        copied = batch("copy", first["id"], [moved["id"]]).json()
        assert copied["changed"] == 1
        assert client.get(f"/api/v1/banks/{first['id']}/questions").json()["total"] == 2

        assert batch("move", None, [moved["id"]]).status_code == 422
        moved_result = batch("move", third["id"], [moved["id"]]).json()
        assert moved_result["changed"] == 1
        assert client.get(f"/api/v1/banks/{second['id']}/questions").json()["total"] == 0
        assert client.get(f"/api/v1/banks/{third['id']}/questions").json()["total"] == 1

        deleted = batch("delete", None, [kept["id"]]).json()
        assert deleted["changed"] == 1
        assert client.get(f"/api/v1/banks/{first['id']}/questions").json()["total"] == 1


def test_update_question_rejects_duplicate_and_delete_removes():
    with TestClient(app) as client:
        bank = client.post("/api/v1/banks", json={"name": "编辑删除题库"}).json()
        question = client.post(f"/api/v1/banks/{bank['id']}/questions", json=single_question("编辑前题干")).json()
        duplicate = client.post(f"/api/v1/banks/{bank['id']}/questions", json=single_question("重复指纹题")).json()

        edited = client.put(f"/api/v1/questions/{question['id']}", json=single_question("编辑后题干"))
        assert edited.status_code == 200
        assert edited.json()["version"] == question["version"] + 1

        conflict = client.put(f"/api/v1/questions/{question['id']}", json=single_question("重复指纹题"))
        assert conflict.status_code == 409

        assert client.delete(f"/api/v1/questions/{duplicate['id']}").status_code == 204
        assert client.get(f"/api/v1/banks/{bank['id']}/questions").json()["total"] == 1
