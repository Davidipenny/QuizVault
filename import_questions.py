#!/usr/bin/env python3
"""题库导入工具 — 验证模块"""

import argparse
import hashlib
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Tuple

from parse_markdown import parse_markdown

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

QUESTIONS_FILE = 'questions.yaml'
QUESTIONS_FILE_JSON = 'questions.json'

REQUIRED_FIELDS = ['id', 'type', 'question', 'options', 'answer']
VALID_TYPES = ['single', 'multi', 'truefalse']


def validate_question(q: Dict) -> List[str]:
    """
    验证单个题目

    Args:
        q: 题目字典

    Returns:
        错误列表，空列表表示通过
    """
    errors = []

    # 必填字段检查
    for field in REQUIRED_FIELDS:
        if field not in q:
            errors.append(f"缺少必填字段: {field}")

    if errors:  # 缺少基本字段，无法继续验证
        return errors

    # 类型检查
    if q['type'] not in VALID_TYPES:
        errors.append(f"type 无效: {q['type']}，必须是 {VALID_TYPES}")

    # 选项检查
    if not isinstance(q['options'], dict):
        errors.append("options 必须是字典格式")
    elif q['type'] == 'truefalse':
        if len(q['options']) != 2:
            errors.append(f"判断题必须有 2 个选项，当前为 {len(q['options'])} 个")
    elif q['type'] in ('single', 'multi'):
        if len(q['options']) < 3 or len(q['options']) > 4:
            errors.append(f"{q['type']}题必须有 3-4 个选项，当前为 {len(q['options'])} 个")

    # 答案检查
    answer = q['answer'].upper()
    valid_letters = ''.join(sorted(q['options'].keys()))  # 动态获取有效字母
    if q['type'] == 'truefalse':
        if answer not in ('A', 'B'):
            errors.append(f"answer 无效: 判断题答案必须是 A 或 B，当前为 \"{q['answer']}\"")
    elif q['type'] == 'single':
        if len(answer) != 1 or answer not in valid_letters:
            errors.append(f"answer 无效: 单选答案必须是 {valid_letters} 中的一个字母，当前为 \"{q['answer']}\"")
    elif q['type'] == 'multi':
        if len(answer) < 2 or len(answer) > len(valid_letters):
            errors.append(f"answer 无效: 多选答案必须是 2-{len(valid_letters)} 个字母，当前为 {len(answer)} 个")
        elif len(answer) != len(set(answer)):
            errors.append(f"answer 无效: 多选答案有重复字母: {q['answer']}")
        elif not all(c in valid_letters for c in answer):
            errors.append(f"answer 无效: 多选答案包含无效字母: {q['answer']}")

    return errors


def compute_hash(text: str, q_type: str = '') -> str:
    """
    计算题目文本的内容哈希

    Args:
        text: 题目文本
        q_type: 题目类型（'single' 或 'multi'），用于区分同题目不同题型

    Returns:
        哈希值的前 8 位
    """
    normalized = re.sub(r'^[\s\W]+|[\s\W]+$', '', text)
    if q_type:
        normalized = f"{q_type}:{normalized}"
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()[:8]


def convert_options_dict_to_list(options: Dict[str, str]) -> List[str]:
    """将 dict 格式选项转为 list 格式"""
    result = []
    for letter in sorted(options.keys()):
        result.append(f"{letter}. {options[letter]}")
    return result


def convert_options_list_to_dict(options: List[str]) -> Dict[str, str]:
    """将 list 格式选项转为 dict 格式"""
    result = {}
    for opt in options:
        match = re.match(r'^([A-D])\.\s*(.+)', opt)
        if match:
            result[match.group(1)] = match.group(2).strip()
    return result


def load_questions() -> Dict:
    """
    加载题库数据

    Returns:
        包含 meta 和 questions 的字典
    """
    # 优先尝试 YAML
    if HAS_YAML and os.path.exists(QUESTIONS_FILE):
        with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    # fallback 到 JSON
    if os.path.exists(QUESTIONS_FILE_JSON):
        with open(QUESTIONS_FILE_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)

    # 返回空题库
    return {
        'meta': {
            'version': 1,
            'updated': datetime.now().strftime('%Y-%m-%d'),
            'source_files': [],
            'total': 0,
            'single_count': 0,
            'multi_count': 0,
            'truefalse_count': 0
        },
        'questions': []
    }


def save_questions(data: Dict) -> None:
    """
    保存题库数据

    Args:
        data: 包含 meta 和 questions 的字典
    """
    # 更新 meta
    data['meta']['updated'] = datetime.now().strftime('%Y-%m-%d')
    data['meta']['total'] = len(data['questions'])
    data['meta']['single_count'] = sum(1 for q in data['questions'] if q['type'] == 'single')
    data['meta']['multi_count'] = sum(1 for q in data['questions'] if q['type'] == 'multi')
    data['meta']['truefalse_count'] = sum(1 for q in data['questions'] if q['type'] == 'truefalse')

    if HAS_YAML:
        with open(QUESTIONS_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"✓ 已保存到 {QUESTIONS_FILE}")
    else:
        with open(QUESTIONS_FILE_JSON, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ 已保存到 {QUESTIONS_FILE_JSON}（PyYAML 未安装，使用 JSON 格式）")


def import_from_markdown(filepath: str, force: bool = False) -> Tuple[int, int, int]:
    """
    从 Markdown 文件导入题目

    Args:
        filepath: Markdown 文件路径
        force: 是否强制覆盖已有题目

    Returns:
        (成功数, 跳过数, 失败数)
    """
    if not os.path.exists(filepath):
        print(f"✗ 文件不存在: {filepath}")
        return 0, 0, 0

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    questions = parse_markdown(content)
    if not questions:
        print(f"⚠ 未解析到题目: {filepath}")
        return 0, 0, 0

    data = load_questions()

    # 构建已有题目的哈希集合（用于去重）
    existing_hashes = set()
    for q in data['questions']:
        if 'content_hash' in q:
            existing_hashes.add(q['content_hash'])

    source_name = os.path.basename(filepath)
    success = 0
    skipped = 0
    failed = 0

    for q in questions:
        # 设置来源
        q['source'] = source_name

        # 验证
        errors = validate_question(q)
        if errors:
            print(f"  ✗ 题号 {q.get('id', '?')}: {'; '.join(errors)}")
            failed += 1
            continue

        # 计算哈希
        q['content_hash'] = compute_hash(q['question'], q['type'])

        # 去重检查
        if not force and q['content_hash'] in existing_hashes:
            skipped += 1
            continue

        # 转换选项格式为 list（YAML 存储格式）
        q_save = q.copy()
        if isinstance(q_save['options'], dict):
            q_save['options'] = convert_options_dict_to_list(q_save['options'])

        # 添加标记字段
        q_save['flagged'] = False
        q_save['flag_reason'] = None

        data['questions'].append(q_save)
        existing_hashes.add(q['content_hash'])
        success += 1

    # 更新 source_files
    if source_name not in data['meta']['source_files']:
        data['meta']['source_files'].append(source_name)

    save_questions(data)

    return success, skipped, failed


def import_from_directory(dirpath: str, force: bool = False) -> Tuple[int, int, int]:
    """
    从目录下所有 .md 文件导入题目

    Args:
        dirpath: 目录路径
        force: 是否强制覆盖

    Returns:
        (成功数, 跳过数, 失败数)
    """
    if not os.path.isdir(dirpath):
        print(f"✗ 目录不存在: {dirpath}")
        return 0, 0, 0

    total_success = 0
    total_skipped = 0
    total_failed = 0

    md_files = sorted([f for f in os.listdir(dirpath) if f.endswith('.md')])
    if not md_files:
        print(f"⚠ 目录中没有 .md 文件: {dirpath}")
        return 0, 0, 0

    for md_file in md_files:
        filepath = os.path.join(dirpath, md_file)
        print(f"\n导入: {md_file}")
        success, skipped, failed = import_from_markdown(filepath, force)
        total_success += success
        total_skipped += skipped
        total_failed += failed

    return total_success, total_skipped, total_failed


def cmd_import(args):
    """导入命令"""
    if args.dir:
        success, skipped, failed = import_from_directory(args.dir, args.force)
    else:
        success, skipped, failed = import_from_markdown(args.file, args.force)

    print(f"\n{'='*40}")
    print(f"✓ 导入完成：{success} 题成功，{skipped} 题跳过（重复），{failed} 题失败")


def cmd_validate(args):
    """校验命令"""
    with open(args.file, 'r', encoding='utf-8') as f:
        content = f.read()

    questions = parse_markdown(content)
    total = len(questions)
    passed = 0
    failed = 0

    for q in questions:
        errors = validate_question(q)
        if errors:
            print(f"  ✗ 题号 {q.get('id', '?')}: {'; '.join(errors)}")
            failed += 1
        else:
            passed += 1

    print(f"\n校验结果：{total} 题中 {passed} 题通过，{failed} 题有问题")


def cmd_stats(args):
    """统计命令"""
    data = load_questions()
    meta = data['meta']
    questions = data['questions']

    print(f"题库统计")
    print(f"{'='*40}")
    print(f"总题数: {meta.get('total', len(questions))}")
    print(f"判断题: {meta.get('truefalse_count', 0)}")
    print(f"单选题: {meta.get('single_count', 0)}")
    print(f"多选题: {meta.get('multi_count', 0)}")
    print(f"标记待处理: {sum(1 for q in questions if q.get('flagged'))}")
    print(f"来源文件: {', '.join(meta.get('source_files', []))}")
    print(f"最后更新: {meta.get('updated', '未知')}")


def cmd_flagged(args):
    """列出标记题目"""
    data = load_questions()
    flagged = [q for q in data['questions'] if q.get('flagged')]

    if not flagged:
        print("没有标记的题目")
        return

    print(f"标记待处理的题目 ({len(flagged)} 道):")
    print(f"{'='*40}")
    for q in flagged:
        reason = q.get('flag_reason', '无')
        print(f"  [{q['type']}] ID {q['id']}: {q['question'][:50]}...")
        print(f"    标记原因: {reason}")


def cmd_unflag(args):
    """取消标记"""
    data = load_questions()
    found = False

    for q in data['questions']:
        if q.get('id') == args.id and q.get('flagged'):
            if args.type and q.get('type') != args.type:
                continue
            q['flagged'] = False
            q['flag_reason'] = None
            found = True
            break

    if found:
        save_questions(data)
        print(f"✓ 已取消标记: 题号 {args.id}")
    else:
        print(f"✗ 未找到标记的题目: 题号 {args.id}")


def cmd_export(args):
    """导出为 Markdown"""
    data = load_questions()
    questions = data['questions']

    lines = []
    current_type = None

    for q in sorted(questions, key=lambda x: (x['type'], x.get('id', 0))):
        if q['type'] != current_type:
            current_type = q['type']
            type_name = '判断题' if current_type == 'truefalse' else ('单选题' if current_type == 'single' else '多选题')
            lines.append(f"\n## {type_name}\n")

        lines.append(f"**{q.get('id', '?')}. {q['question']}**")

        # 处理选项格式
        if isinstance(q['options'], list):
            for opt in q['options']:
                lines.append(opt)
        elif isinstance(q['options'], dict):
            for letter in sorted(q['options'].keys()):
                lines.append(f"{letter}. {q['options'][letter]}")

        lines.append(f"\n**答案：{q['answer']}**\n")

        if q.get('explanation'):
            lines.append(f"**解析：** {q['explanation']}\n")

        lines.append("---")

    output = '\n'.join(lines)
    output_file = args.output or '导出题库.md'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)

    print(f"✓ 已导出到 {output_file}，共 {len(questions)} 道题目")


def main():
    parser = argparse.ArgumentParser(description='题库导入工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # import 命令
    import_parser = subparsers.add_parser('import', help='导入题目')
    import_parser.add_argument('file', nargs='?', help='Markdown 文件路径')
    import_parser.add_argument('--dir', help='导入目录下所有 .md 文件')
    import_parser.add_argument('--force', action='store_true', help='强制覆盖已有题目')

    # validate 命令
    validate_parser = subparsers.add_parser('validate', help='校验题目格式')
    validate_parser.add_argument('file', help='Markdown 文件路径')

    # stats 命令
    subparsers.add_parser('stats', help='显示题库统计')

    # flagged 命令
    subparsers.add_parser('flagged', help='列出标记题目')

    # unflag 命令
    unflag_parser = subparsers.add_parser('unflag', help='取消标记')
    unflag_parser.add_argument('--id', type=int, required=True, help='题目 ID')
    unflag_parser.add_argument('--type', choices=['single', 'multi', 'truefalse'], help='题目类型')

    # export 命令
    export_parser = subparsers.add_parser('export', help='导出为 Markdown')
    export_parser.add_argument('--output', help='输出文件名')

    args = parser.parse_args()

    if args.command == 'import':
        if not args.file and not args.dir:
            import_parser.error("请指定文件路径或 --dir 目录")
        cmd_import(args)
    elif args.command == 'validate':
        cmd_validate(args)
    elif args.command == 'stats':
        cmd_stats(args)
    elif args.command == 'flagged':
        cmd_flagged(args)
    elif args.command == 'unflag':
        cmd_unflag(args)
    elif args.command == 'export':
        cmd_export(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
