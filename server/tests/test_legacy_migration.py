import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app, auto_import_legacy_banks
from app.legacy_markdown import parse_markdown
from app.models import Collection, LegacyMapping, Question, QuestionBank, QuizAnswer, QuizSession, StudyState


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


def test_fixed_legacy_fixture_covers_real_file_variants():
    fixture = Path(__file__).parent / "fixtures" / "legacy_complete"

    with TestClient(app) as client:
        preview = client.get("/api/v1/migration/legacy/preview", params={"path": str(fixture)})

    assert preview.status_code == 200
    report = preview.json()
    assert {bank["name"] for bank in report["banks"]} == {"示例旧题库", "旧式状态题库"}
    sample = next(bank for bank in report["banks"] if bank["name"] == "示例旧题库")
    assert sample["deleted"] == 1
    assert any(issue["file"] == "broken.json" for issue in sample["issues"])
    assert report["summary"]["migratable"] >= 4


def test_startup_bank_import_is_automatic_and_idempotent(tmp_path, monkeypatch):
    root = tmp_path / "banks"
    folder = root / "自动识别题库"
    folder.mkdir(parents=True)
    folder.joinpath("questions.md").write_text(
        "## 单选题\n\n**1. 自动导入题（　）**\nA. 甲\nB. 乙\n\n**答案：A**\n\n"
        "---\n\n**1. 重复题号仍需导入（　）**\nA. 丙\nB. 丁\n\n**答案：B**",
        encoding="utf-8",
    )
    monkeypatch.setenv("QUIZVAULT_LEGACY_BANKS", str(root))

    first = auto_import_legacy_banks()
    repeated = auto_import_legacy_banks()

    assert first and first["banks"] == 1 and first["questions"] == 2
    assert repeated and repeated["banks"] == 0 and repeated["questions"] == 0
    with SessionLocal() as db:
        bank = db.scalar(select(QuestionBank).where(QuestionBank.name == folder.name))
        assert bank.description == "由本地 banks 自动导入"
        assert len(db.scalars(select(Question).where(Question.bank_id == bank.id)).all()) == 2
        assert len(db.scalars(select(LegacyMapping).where(LegacyMapping.question_id.in_(select(Question.id).where(Question.bank_id == bank.id)))).all()) == 2


def test_markdown_embedded_choice_section_header_applies_to_next_question():
    questions = parse_markdown(
        "## 多选题\n\n**1. 多选题（　）**\nA. 甲\nB. 乙\nC. 丙\nD. 丁第十章一、单项选择题\n\n**答案：AB**\n\n"
        "---\n\n**2. 标题缺失的单选题（　）**\nA. 丙\nB. 丁\n\n**答案：A**"
    )

    assert [question["type"] for question in questions] == ["multi", "single"]
