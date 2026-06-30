#!/usr/bin/env python3
"""Markdown 题库解析器 - 开发工具"""

import re
from typing import List, Dict


def parse_markdown(text: str) -> List[Dict]:
    """
    解析 Markdown 格式的题库

    Args:
        text: Markdown 文本字符串

    Returns:
        题目列表，每个题目是一个字典
    """
    questions = []
    current_question = None
    current_type = 'single'  # 默认题型

    # 分割成块
    blocks = text.split('---')

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # 检测章节标题，更新当前默认类型
        header_match = re.search(r'^#+\s*(.+)', block, re.MULTILINE)
        if header_match:
            header_text = header_match.group(1).strip().lower()
            if '单选' in header_text or 'single' in header_text:
                current_type = 'single'
            elif '多选' in header_text or 'multiple' in header_text:
                current_type = 'multi'
            # 跳过纯标题块（没有题目的块）
            if not re.search(r'\*\*\d+\.', block):
                continue

        # 跳过纯说明块
        if block.startswith('>'):
            continue

        # 检测单题类型覆盖注释
        if '<!-- single -->' in block:
            current_type = 'single'
        elif '<!-- multi -->' in block:
            current_type = 'multi'

        # 匹配题号和题干
        # 允许（　）后有文本，如 "（　）中首先确立的。"
        question_match = re.search(r'\*\*(\d+)\.\s*(.+?（\s*）.*?)\*\*', block)
        if question_match:
            if current_question:
                questions.append(current_question)

            q_id = int(question_match.group(1))
            q_text = question_match.group(2).strip()

            current_question = {
                'id': q_id,
                'type': current_type,  # 使用当前默认类型
                'question': q_text,
                'options': {},
                'answer': '',
                'explanation': ''
            }

            # 解析选项
            options = re.findall(r'([A-D])\.\s*(.+?)(?=\n[A-D]\.|\n\*\*答案|$)', block, re.DOTALL)
            for opt_letter, opt_text in options:
                current_question['options'][opt_letter] = opt_text.strip()

        # 匹配答案
        answer_match = re.search(r'\*\*答案：([A-D]+)\*\*', block)
        if answer_match and current_question:
            current_question['answer'] = answer_match.group(1)

        # 匹配解析
        explanation_match = re.search(r'\*\*解析：\*\*\s*(.+?)(?=\n---|\n##|$)', block, re.DOTALL)
        if explanation_match and current_question:
            current_question['explanation'] = explanation_match.group(1).strip()

    # 添加最后一题
    if current_question:
        questions.append(current_question)

    return questions


if __name__ == '__main__':
    # 测试用
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            content = f.read()
        questions = parse_markdown(content)
        print(f"解析到 {len(questions)} 道题目")
        for q in questions[:3]:
            print(f"\n题目 {q['id']}: {q['question']}")
            print(f"题型: {q['type']}")
            print(f"答案: {q['answer']}")
