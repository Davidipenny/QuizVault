from __future__ import annotations

import hashlib
import re
from typing import Any


QUESTION_TYPES = {"single", "multi", "any", "truefalse", "fill", "essay"}


def normalize_text(value: str) -> str:
    value = str(value or "").replace("\u3000", " ").replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.strip() for line in value.strip().split("\n"))


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", normalize_text(value)).strip()


def question_fingerprint(question: dict[str, Any]) -> str:
    choices = question.get("choices") or []
    choice_text = "|".join(compact_text(c.get("content", "")) for c in choices)
    raw = f"{question.get('type', '')}|{compact_text(question.get('prompt', ''))}|{choice_text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_question(question: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    qtype = question.get("type")
    prompt = compact_text(question.get("prompt", ""))
    spec = question.get("answer_spec") or {}
    choices = question.get("choices") or []
    if qtype not in QUESTION_TYPES:
        errors.append("题型无效")
    if not prompt:
        errors.append("题干不能为空")
    labels = [str(c.get("label", "")).upper() for c in choices]
    if len(labels) != len(set(labels)):
        errors.append("选项标签不能重复")
    if qtype in {"single", "multi", "any"}:
        if len(choices) < 2:
            errors.append("选择题至少需要两个选项")
        correct = [str(x).upper() for x in spec.get("correct", [])]
        if any(x not in labels for x in correct):
            errors.append("答案包含不存在的选项")
        if qtype == "single" and len(correct) != 1:
            errors.append("单选题必须且只能有一个正确选项")
        if qtype == "multi" and len(correct) < 2:
            errors.append("多选题至少需要两个正确选项")
        if qtype == "any" and not correct:
            errors.append("任意选题至少需要一个正确选项")
    elif qtype == "truefalse" and not isinstance(spec.get("value"), bool):
        errors.append("判断题答案必须为布尔值")
    elif qtype == "fill":
        blanks = spec.get("blanks") or []
        if not blanks or any(not blank for blank in blanks):
            errors.append("填空题每个空至少需要一个可接受答案")
    elif qtype == "essay" and not compact_text(spec.get("reference", "")):
        errors.append("问答题需要参考答案")
    return errors


def grade_answer(question: dict[str, Any], answer: dict[str, Any], compare_essay: bool = False) -> bool | None:
    qtype = question["type"]
    spec = question.get("answer_spec") or {}
    if qtype in {"single", "multi", "any"}:
        expected = {str(x).upper() for x in spec.get("correct", [])}
        actual = {str(x).upper() for x in answer.get("selected", [])}
        return actual == expected
    if qtype == "truefalse":
        return answer.get("value") is spec.get("value")
    if qtype == "fill":
        expected_blanks = spec.get("blanks", [])
        actual_values = [normalize_text(x) for x in answer.get("values", [])]
        if len(actual_values) != len(expected_blanks):
            return False
        if spec.get("unordered"):
            remaining = list(actual_values)
            for accepted in expected_blanks:
                match = next((v for v in remaining if v in {normalize_text(x) for x in accepted}), None)
                if match is None:
                    return False
                remaining.remove(match)
            return True
        return all(actual in {normalize_text(x) for x in accepted} for actual, accepted in zip(actual_values, expected_blanks))
    if qtype == "essay":
        if not compare_essay:
            return answer.get("self_assessment")
        return normalize_text(answer.get("text", "")) == normalize_text(spec.get("reference", ""))
    raise ValueError(f"Unsupported question type: {qtype}")

