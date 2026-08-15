from __future__ import annotations

import re
from typing import Any


def parse_markdown(text: str) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    current_question: dict[str, Any] | None = None
    current_type = "single"

    for raw_block in text.split("---"):
        block = raw_block.strip()
        if not block:
            continue

        header_match = re.search(r"^#+\s*(.+)", block, re.MULTILINE)
        if header_match:
            header_text = header_match.group(1).strip().lower()
            if "单选" in header_text or "single" in header_text:
                current_type = "single"
            elif "多选" in header_text or "multiple" in header_text:
                current_type = "multi"
            elif "判断" in header_text or "truefalse" in header_text:
                current_type = "truefalse"
            if not re.search(r"\*\*\d+\.", block):
                continue

        if block.startswith(">"):
            continue
        if "<!-- single -->" in block:
            current_type = "single"
        elif "<!-- multi -->" in block:
            current_type = "multi"
        elif "<!-- truefalse -->" in block:
            current_type = "truefalse"

        question_match = re.search(r"\*\*(\d+)\.\s*(.+?（\s*）.*?)\*\*", block)
        if question_match:
            if current_question:
                questions.append(current_question)
            current_question = {
                "id": int(question_match.group(1)),
                "type": current_type,
                "question": question_match.group(2).strip(),
                "options": {},
                "answer": "",
                "explanation": "",
            }
            options = re.findall(r"([A-D])\.\s*(.+?)(?=\n[A-D]\.|\n\*\*答案|$)", block, re.DOTALL)
            for label, content in options:
                current_question["options"][label] = content.strip()

        answer_match = re.search(r"\*\*答案：([A-D]+)\*\*", block)
        if answer_match and current_question:
            current_question["answer"] = answer_match.group(1)
            if len(current_question["answer"]) > 1 and current_question["type"] == "single":
                current_question["type"] = "multi"

        explanation_match = re.search(r"\*\*解析：\*\*\s*(.+?)(?=\n---|\n##|$)", block, re.DOTALL)
        if explanation_match and current_question:
            current_question["explanation"] = explanation_match.group(1).strip()

    if current_question:
        questions.append(current_question)
    return questions
