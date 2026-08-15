import os
import tempfile
import json
from pathlib import Path

os.environ["QUIZVAULT_DATA_DIR"] = tempfile.mkdtemp(prefix="quizvault-test-")

from fastapi.testclient import TestClient

from app.main import app


def sample_question():
    return {
        "type": "single",
        "prompt": "SQLite 属于哪类数据库？",
        "case_material": "",
        "explanation": "SQLite 是嵌入式关系型数据库。",
        "source": "test",
        "choices": [
            {"label": "A", "content": "关系型", "is_correct": True},
            {"label": "B", "content": "图数据库", "is_correct": False},
        ],
        "answer_spec": {"correct": ["A"]},
    }


def test_end_to_end_local_flow():
    with TestClient(app) as client:
        bank = client.post("/api/v1/banks", json={"name": "测试题库", "tags": ["测试"]}).json()
        created = client.post(f"/api/v1/banks/{bank['id']}/questions", json=sample_question())
        assert created.status_code == 201
        question = created.json()

        duplicate = client.post(f"/api/v1/banks/{bank['id']}/questions", json=sample_question())
        assert duplicate.status_code == 409

        preview = client.post("/api/v1/imports/preview", json={
            "bank_id": bank["id"], "source_type": "ai_json",
            "content": '[{"type":"truefalse","prompt":"SQLite 可离线使用","answer":true}]',
        })
        assert preview.status_code == 201
        job = preview.json()
        assert job["stats"]["valid"] == 1
        committed = client.post(f"/api/v1/imports/{job['id']}/commit")
        assert committed.json()["committed"] == 1

        quiz = client.post("/api/v1/quiz-sessions", json={"bank_id": bank["id"], "config": {"types": ["single"], "order": "sequential"}}).json()
        session = client.get(f"/api/v1/quiz-sessions/{quiz['id']}").json()
        assert len(session["questions"]) == 1
        answer = client.post(f"/api/v1/quiz-sessions/{quiz['id']}/answers", json={"question_id": question["id"], "answer": {"selected": ["B"]}}).json()
        assert answer["is_correct"] is False
        states = client.get("/api/v1/study-states?kind=wrong").json()
        assert states["total"] == 1

        collection = client.post("/api/v1/collections", json={"name": "重点"}).json()
        assert client.post(f"/api/v1/collections/{collection['id']}/questions", json={"question_id": question["id"]}).status_code == 200
        saved = client.get(f"/api/v1/collections/{collection['id']}/questions").json()
        assert saved["items"][0]["id"] == question["id"]
        history = client.get("/api/v1/quiz-answers").json()
        assert history["total"] == 1
        assert history["items"][0]["is_correct"] is False
        template = client.get("/api/v1/imports/template/excel")
        assert template.status_code == 200
        assert template.content.startswith(b"PK")

        legacy_root = Path(tempfile.mkdtemp(prefix="quizvault-legacy-"))
        legacy_bank = legacy_root / "旧题库"
        legacy_bank.mkdir()
        legacy_bank.joinpath("questions.md").write_text(
            "## 单选题\n\n**1. 迁移题目（　）**\nA. 甲\nB. 乙\n\n**答案：A**\n\n**解析：** 迁移解析\n\n---\n\n## 多选题\n\n**2. 无效多选（　）**\nA. 甲\nB. 乙\n\n**答案：A**",
            encoding="utf-8",
        )
        legacy_bank.joinpath("collections.json").write_text(json.dumps({
            "collections": {"旧收藏": {"created": "2026-01-01", "questions": [{"id": 1, "type": "single"}]}}
        }, ensure_ascii=False), encoding="utf-8")
        legacy_bank.joinpath("quiz_progress.json").write_text(json.dumps({
            "bank_name": "旧题库", "mode": "normal", "question_type": "single",
            "total_questions": 1, "current_idx": 0, "correct_count": 0,
            "question_order": [0], "answers": [],
        }, ensure_ascii=False), encoding="utf-8")
        migrated = client.post("/api/v1/migration/legacy/commit", json={"path": str(legacy_root)}).json()
        assert migrated["questions"] == 1
        assert migrated["invalid_questions"] == 1
        assert migrated["collections"] == 1
        assert migrated["sessions"] == 1
        repeated = client.post("/api/v1/migration/legacy/commit", json={"path": str(legacy_root)}).json()
        assert repeated["questions"] == 0
        assert repeated["sessions"] == 0

        backup = client.post("/api/v1/backups").json()
        assert backup["filename"].endswith(".db")
