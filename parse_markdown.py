#!/usr/bin/env python3
"""Markdown 题库解析器命令行入口。"""

from server.app.legacy_markdown import parse_markdown


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            content = f.read()
        questions = parse_markdown(content)
        print(f"解析到 {len(questions)} 道题目")
        for q in questions[:3]:
            print(f"\n题目 {q['id']}: {q['question']}")
            print(f"题型: {q['type']}")
            print(f"答案: {q['answer']}")
