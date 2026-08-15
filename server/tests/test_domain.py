import pytest

from app.domain import grade_answer, normalize_text, question_fingerprint, validate_question


def question(qtype, answer_spec, choices=None):
    return {
        "type": qtype,
        "prompt": "测试题干",
        "answer_spec": answer_spec,
        "choices": choices or [],
    }


@pytest.mark.parametrize(("item", "answer", "expected"), [
    (question("single", {"correct": ["B"]}, [{"label": "A", "content": "甲"}, {"label": "B", "content": "乙"}]), {"selected": ["B"]}, True),
    (question("multi", {"correct": ["A", "C"]}, [{"label": "A", "content": "甲"}, {"label": "B", "content": "乙"}, {"label": "C", "content": "丙"}]), {"selected": ["C", "A"]}, True),
    (question("any", {"correct": ["A"]}, [{"label": "A", "content": "甲"}, {"label": "B", "content": "乙"}]), {"selected": ["A", "B"]}, False),
    (question("truefalse", {"value": False}), {"value": False}, True),
    (question("fill", {"blanks": [["北京", "北京市"], ["中国"]]}), {"values": [" 北京　", "中国"]}, True),
    (question("fill", {"blanks": [["甲"], ["乙"]], "unordered": True}), {"values": ["乙", "甲"]}, True),
    (question("essay", {"reference": "第一行\n第二行"}), {"text": " 第一行\r\n第二行 ", "self_assessment": False}, True),
    (question("essay", {"reference": "参考"}), {"text": "不同", "self_assessment": False}, False),
])
def test_grading(item, answer, expected):
    compare = item["type"] == "essay" and item["answer_spec"]["reference"] != "参考"
    assert grade_answer(item, answer, compare_essay=compare) is expected


def test_essay_defaults_to_self_assessment():
    item = question("essay", {"reference": "参考"})
    assert grade_answer(item, {"text": "任意", "self_assessment": None}) is None


def test_validation_and_fingerprint_normalization():
    bad = question("single", {"correct": ["A", "B"]}, [{"label": "A", "content": "甲"}, {"label": "B", "content": "乙"}])
    assert "单选题必须且只能有一个正确选项" in validate_question(bad)
    a = {**bad, "answer_spec": {"correct": ["A"]}, "prompt": "  测试题干　"}
    b = {**a, "prompt": "测试题干"}
    assert question_fingerprint(a) == question_fingerprint(b)
    assert normalize_text(" a　\r\nb ") == "a\nb"

