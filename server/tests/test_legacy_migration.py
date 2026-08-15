import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import Collection, QuestionBank, QuizAnswer, QuizSession, StudyState


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_legacy_preview_and_commit_preserve_all_supported_state_formats():
    root = Path(tempfile.mkdtemp(prefix="quizvault-legacy-complete-"))
    folder = root / "完整旧题库"
    folder.mkdir()
    folder.joinpath("questions.md").write_text(
        "## 单选题\n\n**1. 第一题（　）**\nA. 甲\nB. 乙\n\n**答案：A**\n\n---\n\n"
        "## 多选题\n\n**2. 无效题（　）**\nA. 甲\nB. 乙\n\n**答案：A**",
        encoding="utf-8",
    )
    write_json(folder / "more.json", {"questions": [
        {"id": 3, "type": "truefalse", "question": "第三题", "options": {"A": "正确", "B": "错误"}, "answer": "A"},
        {"id": 30, "type": "truefalse", "question": "第三题", "options": {"A": "重复", "B": "重复"}, "answer": "A"},
        {"id": 4, "type": "single", "question": "待删除", "options": {"A": "甲", "B": "乙"}, "answer": "A"},
        {"id": 9, "type": "single", "question": "第一题", "options": {"A": "重复", "B": "重复"}, "answer": "A"},
    ]})
    write_json(folder / "deleted.json", {"deleted": [{"id": 4, "type": "single"}]})
    write_json(folder / "wrong_questions.json", {"wrong_books": {
        "一": [{"id": 1, "type": "single", "wrong_count": 2}],
        "二": [{"id": 1, "type": "single", "wrong_count": 7}, {"id": 404, "type": "single"}],
    }})
    write_json(folder / "collections.json", {"collections": {
        "旧列表": [{"id": 1, "type": "single"}],
        "新结构": {"created": "2026-01-01", "questions": [{"id": 3, "type": "truefalse"}]},
    }})
    write_json(folder / "flagged.json", {"flagged": [{"id": 1, "type": "single"}]})
    write_json(folder / "quiz_progress.json", {
        "bank_name": folder.name, "mode": "random", "question_type": "all",
        "total_questions": 3, "current_idx": 2, "correct_count": 1,
        "question_order": [3, 2, 0],
        "answers": [
            {"user_answer": "A", "is_correct": True},
            {"user_answer": "A", "is_correct": True},
            {"user_answer": "A", "is_correct": False},
        ],
    })

    with TestClient(app) as client:
        preview = client.get("/api/v1/migration/legacy/preview", params={"path": str(root)})
        assert preview.status_code == 200
        report = preview.json()["banks"][0]
        assert report["deleted"] == 1
        assert report["stats"]["invalid"] == 1
        assert report["stats"]["duplicate"] == 1
        assert report["stats"]["unmatched"] == 1

        result = client.post("/api/v1/migration/legacy/commit", json={"path": str(root)}).json()
        assert result["questions"] == 3
        assert result["unmatched_states"] == 1
        repeated = client.post("/api/v1/migration/legacy/commit", json={"path": str(root)}).json()
        assert repeated["questions"] == 0
        assert repeated["sessions"] == 0

    with SessionLocal() as db:
        bank = db.scalar(select(QuestionBank).where(QuestionBank.name == folder.name))
        session = db.scalar(select(QuizSession).where(QuizSession.bank_id == bank.id))
        states = db.scalars(select(StudyState).where(StudyState.question_id.in_(session.question_order))).all()
        assert len(session.question_order) == 2
        assert len(db.scalars(select(QuizAnswer).where(QuizAnswer.session_id == session.id)).all()) == 2
        assert max(state.wrong_count for state in states) == 7
        assert any(state.flagged for state in states)
        assert len(db.scalars(select(Collection).where(Collection.name.in_(["旧列表", "新结构"]))).all()) == 2
