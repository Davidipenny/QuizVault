#!/usr/bin/env python3
"""把 SQLite 数据库中的题库导出为可自动导入的 banks/ 旧版 JSON 题库。

用法：
    python scripts/export_banks.py [输出目录，默认项目根 banks/]

从当前数据目录（QUIZVAULT_DATA_DIR 或 %APPDATA%/QuizVault）读取全部题库，
按 banks/<题库名>/questions.json 写出。导出内容与数据库指纹一致，
再次自动导入不会产生重复题目。
"""

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.config import database_path  # noqa: E402


def legacy_answer(qtype: str, spec: dict) -> str:
    if qtype in {"single", "multi", "any"}:
        return "".join(spec.get("correct", []))
    if qtype == "truefalse":
        return "正确" if spec.get("value") else "错误"
    if qtype == "fill":
        return "|".join("／".join(blank) for blank in spec.get("blanks", []))
    return str(spec.get("reference", ""))


def main() -> None:
    out_root = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "banks"
    db = sqlite3.connect(database_path())
    db.row_factory = sqlite3.Row
    total = 0
    for bank in db.execute("select id, name from question_banks order by name"):
        bank_dir = out_root / bank["name"]
        bank_dir.mkdir(parents=True, exist_ok=True)
        questions = []
        for row in db.execute(
            "select id, type, prompt, case_material, explanation, answer_spec"
            " from questions where bank_id=? order by sort_order, created_at",
            (bank["id"],),
        ):
            spec = json.loads(row["answer_spec"])
            options = {
                choice["label"]: choice["content"]
                for choice in db.execute(
                    "select label, content from choices where question_id=?"
                    " order by display_order",
                    (row["id"],),
                )
            }
            item = {
                "id": len(questions) + 1,
                "type": row["type"],
                "question": row["prompt"],
                "options": options,
                "answer_spec": spec,
                "answer": legacy_answer(row["type"], spec),
                "explanation": row["explanation"] or "",
            }
            if row["case_material"]:
                item["case_material"] = row["case_material"]
            questions.append(item)
        (bank_dir / "questions.json").write_text(
            json.dumps({"questions": questions}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"{bank['name']}: {len(questions)} 题 -> {bank_dir / 'questions.json'}")
        total += len(questions)
    print(f"共导出 {total} 题")


if __name__ == "__main__":
    main()
