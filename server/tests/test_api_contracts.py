from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import app
import pytest


def single_question(prompt="幂等题"):
    return {
        "type": "single", "prompt": prompt, "answer_spec": {"correct": ["A"]},
        "choices": [
            {"label": "A", "content": "正确"},
            {"label": "B", "content": "错误"},
        ],
    }


def test_request_models_reject_unknown_fields_and_invalid_ranges():
    with TestClient(app) as client:
        assert client.post("/api/v1/banks", json={"name": "严格模型", "unknown": True}).status_code == 422
        assert client.post("/api/v1/banks", json={"name": " ", "challenge_size": -1}).status_code == 422
        assert client.post("/api/v1/quiz-sessions", json={"bank_id": "missing", "config": {"order": "invalid"}}).status_code == 422


@pytest.mark.parametrize("question", [
    {"type": "single", "prompt": "单选", "choices": [{"label": "A", "content": "甲"}, {"label": "B", "content": "乙"}], "answer_spec": {"correct": []}},
    {"type": "multi", "prompt": "多选", "choices": [{"label": "A", "content": "甲"}, {"label": "B", "content": "乙"}], "answer_spec": {"correct": ["A"]}},
    {"type": "any", "prompt": "任意", "choices": [{"label": "A", "content": "甲"}, {"label": "B", "content": "乙"}], "answer_spec": {"correct": []}},
    {"type": "truefalse", "prompt": "判断", "answer_spec": {"value": "not-bool"}},
    {"type": "fill", "prompt": "填空", "answer_spec": {"blanks": []}},
    {"type": "essay", "prompt": "问答", "answer_spec": {"reference": " "}},
])
def test_all_question_types_reject_invalid_answer_specs(question):
    with TestClient(app) as client:
        banks = client.get("/api/v1/banks").json()
        bank = banks[0] if banks else client.post("/api/v1/banks", json={"name": "异常题型题库"}).json()
        assert client.post(f"/api/v1/banks/{bank['id']}/questions", json=question).status_code == 422


def test_repeated_answer_submission_adjusts_wrong_count_by_result_delta():
    with TestClient(app) as client:
        bank = client.post("/api/v1/banks", json={"name": "答案幂等题库"}).json()
        question = client.post(f"/api/v1/banks/{bank['id']}/questions", json=single_question()).json()
        session = client.post("/api/v1/quiz-sessions", json={"bank_id": bank["id"], "config": {}}).json()
        endpoint = f"/api/v1/quiz-sessions/{session['id']}/answers"

        for _ in range(2):
            response = client.post(endpoint, json={"question_id": question["id"], "answer": {"selected": ["B"]}})
            assert response.status_code == 200
        wrong = client.get("/api/v1/study-states", params={"kind": "wrong", "bank_id": bank["id"]}).json()
        assert wrong["items"][0]["wrong_count"] == 1

        for _ in range(2):
            response = client.post(endpoint, json={"question_id": question["id"], "answer": {"selected": ["A"]}})
            assert response.status_code == 200
        assert client.get("/api/v1/study-states", params={"kind": "wrong", "bank_id": bank["id"]}).json()["total"] == 0


def test_concurrent_import_commit_returns_one_committed_result():
    with TestClient(app) as client:
        bank = client.post("/api/v1/banks", json={"name": "并发导入题库"}).json()
        preview = client.post("/api/v1/imports/preview", json={
            "bank_id": bank["id"], "source_type": "ai_json",
            "content": '[{"type":"truefalse","prompt":"并发一","answer":true},{"type":"truefalse","prompt":"并发二","answer":false}]',
        }).json()
        endpoint = f"/api/v1/imports/{preview['id']}/commit"
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: client.post(endpoint), range(2)))

        assert all(response.status_code == 200 for response in responses)
        assert all(response.json()["committed"] == 2 for response in responses)
        questions = client.get(f"/api/v1/banks/{bank['id']}/questions").json()
        assert questions["total"] == 2


def test_import_edit_recomputes_duplicates_and_downloads_json_errors():
    with TestClient(app) as client:
        bank = client.post("/api/v1/banks", json={"name": "导入错误题库"}).json()
        preview = client.post("/api/v1/imports/preview", json={
            "bank_id": bank["id"], "source_type": "ai_json",
            "content": '[{"type":"truefalse","prompt":"原题","answer":true}]',
        }).json()
        rows = [preview["rows"][0], {**preview["rows"][0], "_row": 2}]
        edited = client.patch(f"/api/v1/imports/{preview['id']}", json={"rows": rows}).json()
        assert edited["stats"]["invalid"] == 1
        downloaded = client.get(f"/api/v1/imports/{preview['id']}/errors", params={"download": True})
        assert downloaded.status_code == 200
        assert downloaded.headers["content-type"].startswith("application/json")
        assert "attachment" in downloaded.headers["content-disposition"]
