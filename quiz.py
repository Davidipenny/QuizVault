#!/usr/bin/env python3
"""
QuizVault 选择题刷题系统

功能：
- 支持顺序/随机两种刷题模式
- 单选题和多选题分别练习
- 彩色终端输出
- 错题本功能，跨会话持久化

使用方法：
    python quiz.py

依赖：
    Python 3.6+，无外部依赖
"""

import json
import os
import random
import re
import sys
import unicodedata
from datetime import datetime
from typing import Optional

# 从外部文件加载题库（部分功能仍需要）
try:
    from import_questions import load_questions, save_questions
except ImportError:
    # fallback: 如果 import_questions.py 不在同目录
    load_questions = None
    save_questions = None

# 题库文件夹扫描（可被测试 mock）
try:
    from bank_manager import scan_banks_folder as _scan_banks_folder
except ImportError:
    _scan_banks_folder = None

# 统一基础目录：打包后从 exe 位置找，开发时从脚本位置找
if getattr(sys, 'frozen', False):
    # 打包后：exe 所在目录
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 开发时：脚本所在目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WRONG_QUESTIONS_FILE = os.path.join(BASE_DIR, 'wrong_questions.json')
DELETED_QUESTIONS_FILE = os.path.join(BASE_DIR, 'deleted_questions.json')
COLLECTIONS_FILE = os.path.join(BASE_DIR, 'collections.json')
BANKS_FOLDER = os.path.join(BASE_DIR, 'banks')


def load_collections() -> dict:
    """加载收藏夹数据"""
    if not os.path.exists(COLLECTIONS_FILE):
        return {'collections': {}}
    try:
        with open(COLLECTIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'collections' not in data:
            return {'collections': {}}
        return data
    except (json.JSONDecodeError, IOError):
        return {'collections': {}}


def save_collections(data: dict) -> None:
    """保存收藏夹数据"""
    with open(COLLECTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def create_collection(name: str) -> bool:
    """创建新收藏夹，已存在返回 False"""
    data = load_collections()
    if name in data['collections']:
        return False
    data['collections'][name] = {
        'created': datetime.now().strftime('%Y-%m-%d'),
        'questions': []
    }
    save_collections(data)
    return True


def delete_collection(name: str) -> bool:
    """删除收藏夹，不存在返回 False"""
    data = load_collections()
    if name not in data['collections']:
        return False
    del data['collections'][name]
    save_collections(data)
    return True


def rename_collection(old_name: str, new_name: str) -> bool:
    """重命名收藏夹，old不存在或new已存在返回 False"""
    data = load_collections()
    if old_name not in data['collections']:
        return False
    if new_name in data['collections']:
        return False
    data['collections'][new_name] = data['collections'].pop(old_name)
    save_collections(data)
    return True


def add_to_collection(name: str, question_id: int, question_type: str) -> bool:
    """将题目加入收藏夹，已存在返回 False"""
    data = load_collections()
    if name not in data['collections']:
        return False
    questions = data['collections'][name]['questions']
    for q in questions:
        if q['id'] == question_id and q['type'] == question_type:
            return False
    questions.append({
        'id': question_id,
        'type': question_type,
        'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    save_collections(data)
    return True


def remove_from_collection(name: str, question_id: int, question_type: str) -> bool:
    """从收藏夹移除题目，不存在返回 False"""
    data = load_collections()
    if name not in data['collections']:
        return False
    questions = data['collections'][name]['questions']
    for i, q in enumerate(questions):
        if q['id'] == question_id and q['type'] == question_type:
            questions.pop(i)
            save_collections(data)
            return True
    return False


def find_collections_for_question(question_id: int, question_type: str) -> list:
    """返回包含该题的收藏夹名称列表"""
    data = load_collections()
    result = []
    for name, info in data['collections'].items():
        for q in info['questions']:
            if q['id'] == question_id and q['type'] == question_type:
                result.append(name)
                break
    return result


def prompt_collect_question(question: dict) -> None:
    """答题后收藏提示"""
    qid = question['id']
    qtype = question['type']
    existing = find_collections_for_question(qid, qtype)
    collections_data = load_collections()
    all_names = list(collections_data.get('collections', {}).keys())

    if existing:
        names_str = '、'.join(f'"{n}"' for n in existing)
        print_colored(f"  已在收藏夹 {names_str} 中", Colors.YELLOW)
        user_input = input("  也加入其他收藏夹？输入名称（或 Enter 跳过）：").strip()
        if not user_input:
            return
    else:
        if not all_names:
            user_input = input("  收藏此题？输入收藏夹名称（或 Enter 跳过）：").strip()
        else:
            names_str = '、'.join(f'"{n}"' for n in all_names)
            user_input = input(f"  收藏此题？输入收藏夹名称（已有：{names_str}，或 Enter 跳过）：").strip()
        if not user_input:
            return

    # Add to collection (create if needed)
    data = load_collections()
    if user_input not in data['collections']:
        create_collection(user_input)
        print_colored(f'  ✓ 已创建并加入"{user_input}"', Colors.GREEN)
    else:
        print_colored(f'  ✓ 已加入"{user_input}"', Colors.GREEN)
    add_to_collection(user_input, qid, qtype)


def _prompt_bank_collect(question: dict, bank_path: str, bank_name: str) -> None:
    """题库模式下的收藏提示（使用题库文件夹内的收藏夹）"""
    from bank_manager import load_bank_collections, save_bank_collection

    # 第一步：y/n 确认是否收藏
    confirm = input("  收藏此题？(y/n)：").strip().lower()
    if confirm != 'y':
        return

    qid = question['id']
    qtype = question['type']
    collections_data = load_bank_collections(bank_path)
    collections = collections_data.get('collections', {})

    # 检查题目已在哪些收藏夹中
    existing = []
    for name, items in collections.items():
        for q in items:
            if q['id'] == qid and q['type'] == qtype:
                existing.append(name)
                break

    if existing:
        names_str = '、'.join(f'"{n}"' for n in existing)
        print_colored(f"  已在收藏夹 {names_str} 中", Colors.YELLOW)

    # 第二步：显示收藏夹列表，带编号选择
    all_names = list(collections.keys())

    print_colored("\n  收藏夹列表：", Colors.BOLD)
    for i, name in enumerate(all_names, 1):
        count = len(collections[name])
        print_colored(f"    {i}. {name}（{count}题）", Colors.END)
    print_colored("    n. 新建收藏夹", Colors.END)

    user_input = input("\n  选择收藏夹（输入编号或 n 新建）：").strip()

    if not user_input:
        return

    if user_input.lower() == 'n':
        new_name = input("  新建收藏夹名称：").strip()
        if not new_name:
            return
        save_bank_collection(bank_path, new_name, question)
        print_colored(f'  ✓ 已创建并加入"{new_name}"', Colors.GREEN)
    else:
        try:
            idx = int(user_input) - 1
            if 0 <= idx < len(all_names):
                chosen_name = all_names[idx]
                save_bank_collection(bank_path, chosen_name, question)
                print_colored(f'  ✓ 已加入"{chosen_name}"', Colors.GREEN)
            else:
                print_colored("  无效选择", Colors.RED)
        except ValueError:
            # 用户输入了自定义名称而非编号
            save_bank_collection(bank_path, user_input, question)
            print_colored(f'  ✓ 已加入"{user_input}"', Colors.GREEN)


# 题库数据
QUESTION_BANK = []


def load_question_bank() -> list:
    """
    从 banks/ 文件夹加载题库（兼容旧代码调用）

    Returns:
        题目列表
    """
    if _scan_banks_folder is not None:
        banks = _scan_banks_folder(BANKS_FOLDER)
        if banks:
            return banks[0]['questions']
    return []


def check_answer(question: dict, user_answer: str) -> bool:
    """
    判断用户答案是否正确

    Args:
        question: 题目字典
        user_answer: 用户输入的答案

    Returns:
        答案是否正确
    """
    correct_answer = question['answer'].upper()
    user_answer = user_answer.upper().strip()

    if question['type'] == 'single':
        # 单选题：直接比较
        return user_answer == correct_answer
    else:
        # 多选题：排序后比较
        return sorted(user_answer) == sorted(correct_answer)


def load_wrong_questions() -> list:
    """
    加载错题列表

    Returns:
        错题列表，如果文件不存在返回空列表
    """
    if not os.path.exists(WRONG_QUESTIONS_FILE):
        return []

    try:
        with open(WRONG_QUESTIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('wrong_questions', [])
    except (json.JSONDecodeError, IOError) as e:
        print(f"⚠ 警告：无法读取错题本文件: {e}")
        return []


def save_wrong_question(question: dict) -> None:
    """
    保存错题到错题本

    Args:
        question: 答错的题目字典
    """
    wrong_questions = load_wrong_questions()

    # 检查题目是否已存在（用 id + type 做联合去重，避免单选/多选 ID 碰撞）
    existing_keys = [(q['id'], q['type']) for q in wrong_questions]

    if (question['id'], question['type']) in existing_keys:
        # 更新已有题目的答错次数
        for q in wrong_questions:
            if q['id'] == question['id'] and q['type'] == question['type']:
                q['wrong_count'] = q.get('wrong_count', 1) + 1
                q['last_wrong'] = datetime.now().strftime('%Y-%m-%d')
                break
    else:
        # 添加新题目
        wrong_entry = {
            'id': question['id'],
            'type': question['type'],
            'question': question['question'],
            'options': question['options'],
            'answer': question['answer'],
            'explanation': question['explanation'],
            'wrong_count': 1,
            'last_wrong': datetime.now().strftime('%Y-%m-%d')
        }
        wrong_questions.append(wrong_entry)

    # 保存到文件
    try:
        data = {
            'wrong_questions': wrong_questions,
            'last_updated': datetime.now().isoformat()
        }
        with open(WRONG_QUESTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"⚠ 警告：无法保存错题本文件: {e}")


def remove_wrong_question(question_id: int, question_type: str) -> None:
    """
    从错题本中移除题目

    Args:
        question_id: 题目 ID
        question_type: 题目类型 ('single' 或 'multi')
    """
    wrong_questions = load_wrong_questions()
    wrong_questions = [q for q in wrong_questions if not (q['id'] == question_id and q['type'] == question_type)]

    try:
        data = {
            'wrong_questions': wrong_questions,
            'last_updated': datetime.now().isoformat()
        }
        with open(WRONG_QUESTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"⚠ 警告：无法保存错题本文件: {e}")


def save_deleted_questions(questions: list) -> None:
    """
    将删除的题目备份到 deleted_questions.json

    Args:
        questions: 要备份的题目列表
    """
    # 加载现有数据
    existing = {'deleted': []}
    if os.path.exists(DELETED_QUESTIONS_FILE):
        try:
            with open(DELETED_QUESTIONS_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing = {'deleted': []}

    # 追加新删除的题目
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for q in questions:
        entry = {
            'deleted_at': timestamp,
            'question': {
                'id': q.get('id'),
                'type': q.get('type'),
                'question': q.get('question'),
                'options': q.get('options'),
                'answer': q.get('answer'),
                'explanation': q.get('explanation'),
                'source': q.get('source'),
                'content_hash': q.get('content_hash')
            }
        }
        existing['deleted'].append(entry)

    # 保存
    try:
        with open(DELETED_QUESTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print_colored(f"⚠ 警告：无法保存备份文件: {e}", Colors.YELLOW)


def flag_question(question: dict, reason: str = '') -> None:
    """
    标记题目为待修改

    Args:
        question: 题目字典
        reason: 标记原因
    """
    if load_questions is None:
        print_colored("⚠ 标记功能需要 import_questions.py", Colors.YELLOW)
        return

    data = load_questions()
    for q in data['questions']:
        if q.get('id') == question.get('id') and q.get('type') == question.get('type'):
            q['flagged'] = True
            q['flag_reason'] = reason or None
            break

    from import_questions import save_questions
    save_questions(data)
    print_colored("✓ 已标记题目", Colors.GREEN)


# 颜色代码
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_colored(text: str, color: str) -> None:
    """
    彩色输出文本

    Args:
        text: 要输出的文本
        color: 颜色代码
    """
    print(f"{color}{text}{Colors.END}")


def _display_width(s: str) -> int:
    """Return the terminal display width of a string, counting CJK characters as 2 columns."""
    return sum(2 if unicodedata.east_asian_width(c) in ('F', 'W') else 1 for c in s)


def _truncate_to_width(text: str, max_width: int) -> str:
    """Truncate text to fit within max_width display columns, appending '...' if truncated."""
    result = ''
    width = 0
    for ch in text:
        w = 2 if unicodedata.east_asian_width(ch) in ('F', 'W') else 1
        if width + w > max_width:
            result += '...'
            break
        result += ch
        width += w
    return result


def _pad_to_width(s: str, width: int) -> str:
    """Pad a string with trailing spaces to reach the target display width."""
    dw = _display_width(s)
    if dw >= width:
        return s
    return s + ' ' * (width - dw)


def _wrap_text(text: str, max_width: int) -> list:
    """
    将文本按显示宽度自动换行

    Args:
        text: 要换行的文本
        max_width: 每行最大显示宽度

    Returns:
        换行后的文本列表
    """
    lines = []
    current_line = ''
    current_width = 0

    for ch in text:
        w = 2 if unicodedata.east_asian_width(ch) in ('F', 'W') else 1
        if current_width + w > max_width:
            lines.append(current_line)
            current_line = ch
            current_width = w
        else:
            current_line += ch
            current_width += w

    if current_line:
        lines.append(current_line)

    return lines if lines else ['']


def _center_to_width(s: str, width: int) -> str:
    """Center a string within the target display width using spaces."""
    dw = _display_width(s)
    if dw >= width:
        return s
    total_pad = width - dw
    left_pad = total_pad // 2
    right_pad = total_pad - left_pad
    return ' ' * left_pad + s + ' ' * right_pad


def _format_question_list_line(i: int, q: dict) -> str:
    """Format a single question line for list display within a 60-column box.

    Handles source truncation to prevent line overflow when source filenames
    contain CJK characters.
    """
    type_label = "单选" if q['type'] == 'single' else "多选"
    source = q.get('source', '')
    if source:
        prefix_width = _display_width(f"  {i}. [{type_label}] ")
        label_width = _display_width("  来源：")
        qtext = _truncate_to_width(q['question'], 32)
        qtext_width = _display_width(qtext)
        remaining = 60 - prefix_width - qtext_width - label_width
        source = _truncate_to_width(source, max(remaining, 4))
        line = f"  {i}. [{type_label}] {qtext}  来源：{source}"
    else:
        qtext = _truncate_to_width(q['question'], 46)
        line = f"  {i}. [{type_label}] {qtext}"
    return line


def display_question(question: dict, current: int, total: int) -> None:
    """
    显示题目

    Args:
        question: 题目字典
        current: 当前题号
        total: 总题数
    """
    # 清屏
    os.system('cls' if os.name == 'nt' else 'clear')

    # 来源（如果有）
    source = question.get('source')
    if source:
        print_colored(f"来源：{source}", Colors.END)
        print()

    # 题目类型
    type_name = '单选题' if question['type'] == 'single' else '多选题'

    # 计算内容最大宽度（用于自动换行）
    content_width = 58  # 内容区域宽度（60 - 2 边框）

    # 计算实际需要的宽度
    max_content_width = _display_width(question['question'])
    for letter in ['A', 'B', 'C', 'D']:
        if letter in question['options']:
            text = f"{letter}. {question['options'][letter]}"
            max_content_width = max(max_content_width, _display_width(text))

    # 使用实际宽度，但不超过终端宽度
    box_width = min(max(max_content_width + 2, 60), 100)
    content_width = box_width - 2

    # 进度条
    print_colored(f"┌{'─' * box_width}┐", Colors.BLUE)
    progress_prefix = f" [{current}/{total}] "
    print_colored("│" + _pad_to_width(progress_prefix + type_name, box_width) + "│", Colors.BLUE)
    print_colored(f"├{'─' * box_width}┤", Colors.BLUE)

    # 题干（自动换行）
    question_lines = _wrap_text(question['question'], content_width - 1)
    for line in question_lines:
        print_colored("│" + _pad_to_width(" " + line, box_width) + "│", Colors.BOLD)
    print_colored("│" + " " * box_width + "│", Colors.BLUE)

    # 选项（自动换行）
    for letter in ['A', 'B', 'C', 'D']:
        if letter in question['options']:
            text = f"{letter}. {question['options'][letter]}"
            opt_lines = _wrap_text(text, content_width - 1)
            for line in opt_lines:
                print_colored("│" + _pad_to_width(" " + line, box_width) + "│", Colors.END)

    print_colored(f"└{'─' * box_width}┘", Colors.BLUE)
    print()


def display_feedback(correct: bool, question: dict) -> None:
    """
    显示答题反馈

    Args:
        correct: 答案是否正确
        question: 题目字典
    """
    if correct:
        print_colored("✓ 正确！", Colors.GREEN)
    else:
        print_colored(f"✗ 错误！正确答案是：{question['answer']}", Colors.RED)
        if question.get('explanation'):
            # 截断过长的解析（使用显示宽度而非字符数，CJK 字符占 2 列）
            explanation = question['explanation']
            if _display_width(explanation) > 100:
                truncated = ''
                width = 0
                for ch in explanation:
                    w = 2 if unicodedata.east_asian_width(ch) in ('F', 'W') else 1
                    if width + w > 97:
                        break
                    truncated += ch
                    width += w
                explanation = truncated + '...'
            print_colored(f"解析：{explanation}", Colors.YELLOW)


def display_stats(total: int, correct: int, wrong_count: int, bank_name: str = '') -> None:
    """
    显示结算面板

    Args:
        total: 总题数
        correct: 正确数
        wrong_count: 错误数
        bank_name: 题库名称（为空时显示默认路径）
    """
    accuracy = (correct / total * 100) if total > 0 else 0

    print()
    print_colored(f"╔{'═' * 60}╗", Colors.BLUE)
    print_colored("║" + _center_to_width("刷题结束", 60) + "║", Colors.BLUE)
    print_colored(f"╠{'═' * 60}╣", Colors.BLUE)
    print_colored("║" + _pad_to_width(f"  总题数：{total}", 60) + "║", Colors.END)
    print_colored("║" + _pad_to_width(f"  正确数：{correct}", 60) + "║", Colors.GREEN)
    print_colored("║" + _pad_to_width(f"  错误数：{wrong_count}", 60) + "║", Colors.RED)
    print_colored("║" + _pad_to_width(f"  正确率：{accuracy:.1f}%", 60) + "║", Colors.YELLOW)
    print_colored("║" + " " * 60 + "║", Colors.BLUE)
    if bank_name:
        msg = f"  错题已保存到 {bank_name}/wrong_questions.json"
    else:
        msg = "  错题已保存到 wrong_questions.json"
    print_colored("║" + _pad_to_width(msg, 60) + "║", Colors.END)
    print_colored(f"╚{'═' * 60}╝", Colors.BLUE)
    print()


def parse_selection_input(user_input: str, valid_range: tuple) -> set:
    """
    解析用户输入的选择范围

    Args:
        user_input: 用户输入（如 '3', '3-7', '3,7,12', '3-7,12,15-18'）
        valid_range: 有效题号范围 (min, max)

    Returns:
        选中的题号集合
    """
    selected = set()
    min_id, max_id = valid_range

    if not user_input.strip():
        return selected

    parts = user_input.split(',')
    for part in parts:
        part = part.strip()
        if '-' in part:
            # 范围格式
            try:
                start, end = part.split('-', 1)
                start = int(start.strip())
                end = int(end.strip())
                # 支持反向范围
                if start > end:
                    start, end = end, start
                for num in range(start, end + 1):
                    if min_id <= num <= max_id:
                        selected.add(num)
            except ValueError:
                continue
        else:
            # 单个数字
            try:
                num = int(part)
                if min_id <= num <= max_id:
                    selected.add(num)
            except ValueError:
                continue

    return selected


def validate_answer(user_input: str, question_type: str) -> bool:
    """
    验证用户输入是否有效

    Args:
        user_input: 用户输入
        question_type: 题目类型 ('single' 或 'multi')

    Returns:
        输入是否有效
    """
    user_input = user_input.upper().strip()

    if not user_input:
        return False

    if user_input in ['Q', 'QUIT', 'F']:
        return True

    if question_type == 'single':
        return user_input in ['A', 'B', 'C', 'D']
    else:
        # 多选题：至少需要两个选项，检查是否是 A-D 的组合，字母不重复
        if len(user_input) < 2:
            return False
        if not all(c in 'ABCD' for c in user_input):
            return False
        return len(user_input) == len(set(user_input))


def run_quiz(questions: list, mode: str = 'sequential', allow_collect: bool = True, bank_path: str = '', bank_name: str = '', resume_data: Optional[dict] = None) -> tuple:
    """
    运行刷题

    Args:
        questions: 题目列表
        mode: 模式 ('sequential' 或 'random')
        allow_collect: 是否允许收藏
        bank_path: 题库路径（用于保存错题和收藏到题库文件夹）
        bank_name: 题库名称
        resume_data: 恢复数据（可选），用于继续上次未完成的刷题

    Returns:
        (总题数, 正确数, 答错的题目列表)
    """
    # 恢复模式
    if resume_data:
        _shuffle_indices = resume_data.get('question_order') if resume_data.get('question_order') else None
        if resume_data.get('question_order'):
            # 随机模式：按保存的顺序恢复题目
            order = resume_data['question_order']
            ordered_questions = []
            for idx in order:
                if idx < len(questions):
                    ordered_questions.append(questions[idx])
            questions = ordered_questions
        # 跳到上次位置
        start_idx = resume_data.get('current_idx', 0)
        correct_count = resume_data.get('correct_count', 0)
        # 恢复错题列表
        wrong_questions = []
        if resume_data.get('wrong_questions') and bank_path:
            all_questions = questions
            for wr in resume_data['wrong_questions']:
                for q in all_questions:
                    if q['id'] == wr['id'] and q['type'] == wr['type']:
                        wrong_questions.append(q)
                        break
    else:
        _shuffle_indices = None
        if mode == 'random':
            questions = questions.copy()
            # Capture shuffle order for progress saving
            _shuffle_indices = list(range(len(questions)))
            random.shuffle(_shuffle_indices)
            questions = [questions[i] for i in _shuffle_indices]

        start_idx = 0
        correct_count = 0
        wrong_questions = []

    total = len(questions)

    def _save_current_progress():
        """保存当前刷题进度"""
        if not bank_path or i >= total:
            return
        from bank_manager import save_quiz_progress
        from datetime import datetime
        question_type = 'single' if all(q['type'] == 'single' for q in questions) else 'multi' if all(q['type'] == 'multi' for q in questions) else 'all'
        progress = {
            'bank_name': bank_name,
            'mode': mode,
            'question_type': question_type,
            'total_questions': total,
            'current_idx': i - 1,
            'correct_count': correct_count,
            'wrong_questions': [{'id': q['id'], 'type': q['type']} for q in wrong_questions],
            'question_order': _shuffle_indices if mode == 'random' else None,
            'saved_at': datetime.now().isoformat()
        }
        save_quiz_progress(bank_path, progress)

    for i, question in enumerate(questions[start_idx:], start_idx + 1):
        display_question(question, i, total)

        if question['type'] == 'single':
            prompt = "请输入答案 (A/B/C/D，F标记，Q退出): "
        else:
            prompt = "请输入答案 (如 AB、BCD，F标记，Q退出): "

        while True:
            try:
                user_input = input(prompt).strip()
            except EOFError:
                _save_current_progress()
                return total, correct_count, wrong_questions

            if user_input.upper() in ['Q', 'QUIT']:
                # 保存进度
                if bank_path and i < total:
                    _save_current_progress()
                    print_colored("\n已退出本次刷题，进度已保存", Colors.YELLOW)
                else:
                    print_colored("\n已退出本次刷题", Colors.YELLOW)
                return total, correct_count, wrong_questions

            if user_input.upper() == 'F':
                reason = input("标记原因（可选，直接回车跳过）: ").strip()
                if bank_path:
                    from bank_manager import add_to_bank_flagged
                    if add_to_bank_flagged(bank_path, question['id'], question['type'], reason):
                        print_colored("✓ 已标记题目", Colors.GREEN)
                    else:
                        print_colored("⚠ 题目已被标记", Colors.YELLOW)
                else:
                    flag_question(question, reason)
                continue

            if not validate_answer(user_input, question['type']):
                print_colored("⚠ 无效输入，请重新输入", Colors.YELLOW)
                continue

            break

        is_correct = check_answer(question, user_input)
        display_feedback(is_correct, question)

        if is_correct:
            correct_count += 1
            if bank_path:
                from bank_manager import remove_bank_wrong_question
                remove_bank_wrong_question(bank_path, question['id'], question['type'])
            else:
                remove_wrong_question(question['id'], question['type'])
        else:
            wrong_questions.append(question)
            if bank_path:
                from bank_manager import save_bank_wrong_question
                default_book = f"{bank_name}错题" if bank_name else "默认错题"
                save_bank_wrong_question(bank_path, default_book, question)
            else:
                save_wrong_question(question)

        # 收藏提示
        if allow_collect:
            if bank_path:
                _prompt_bank_collect(question, bank_path, bank_name)
            else:
                prompt_collect_question(question)

        # 等待用户按键继续
        try:
            input("\n按 Enter 继续...")
        except EOFError:
            _save_current_progress()
            break

    return total, correct_count, wrong_questions


def batch_delete_questions() -> None:
    """批量删题功能"""
    if load_questions is None or save_questions is None:
        print_colored("⚠ 批量删题功能需要 import_questions.py", Colors.YELLOW)
        input("按 Enter 继续...")
        return

    data = load_questions()
    questions = data.get('questions', [])

    if not questions:
        print_colored("\n题库为空，没有可删除的题目", Colors.GREEN)
        input("按 Enter 继续...")
        return

    # 已选中的题号集合
    selected_ids = set()
    page_size = 20
    current_page = 0
    total_pages = (len(questions) + page_size - 1) // page_size

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')

        # 计算当前页的题目
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, len(questions))
        page_questions = questions[start_idx:end_idx]

        # 显示标题
        print_colored(f"╔{'═' * 62}╗", Colors.BLUE)
        title = f"批量删题 — 第 {current_page + 1}/{total_pages} 页"
        print_colored("║" + _center_to_width(title, 62) + "║", Colors.BOLD)
        print_colored(f"╠{'═' * 62}╣", Colors.BLUE)

        # 显示题目列表
        for i, q in enumerate(page_questions):
            global_idx = start_idx + i + 1  # 1-based 题号
            marker = '●' if global_idx in selected_ids else '○'
            type_tag = '[单选]' if q['type'] == 'single' else '[多选]'

            # 截断题干到46显示宽度
            truncated = _truncate_to_width(q['question'], 46)

            source = q.get('source', '')
            line = f"  {marker} {global_idx:>3}. {truncated}  {type_tag} {source}"
            print_colored("║" + _pad_to_width(line, 62) + "║", Colors.END)

        # 显示状态栏
        print_colored(f"╠{'═' * 62}╣", Colors.BLUE)
        status = f"  已选：{len(selected_ids)} 题"
        print_colored("║" + _pad_to_width(status, 62) + "║", Colors.YELLOW)
        help_text = "  输入题号切换 | n-下页 | p-上页 | done-确认 | q-取消"
        print_colored("║" + _pad_to_width(help_text, 62) + "║", Colors.END)
        print_colored(f"╚{'═' * 62}╝", Colors.BLUE)

        # 获取用户输入
        user_input = input("\n请输入: ").strip().lower()

        if user_input == 'q' or user_input == 'quit':
            return
        elif user_input == 'n' or user_input == 'next':
            if current_page < total_pages - 1:
                current_page += 1
        elif user_input == 'p' or user_input == 'prev':
            if current_page > 0:
                current_page -= 1
        elif user_input == 'all':
            for i in range(len(page_questions)):
                selected_ids.add(start_idx + i + 1)
        elif user_input == 'none':
            for i in range(len(page_questions)):
                selected_ids.discard(start_idx + i + 1)
        elif user_input == 'done' or user_input == 'd':
            if not selected_ids:
                print_colored("\n未选择任何题目", Colors.YELLOW)
                input("按 Enter 继续...")
                continue

            # 确认删除
            os.system('cls' if os.name == 'nt' else 'clear')
            print_colored(f"╔{'═' * 62}╗", Colors.BLUE)
            print_colored("║" + _center_to_width("确认删除", 62) + "║", Colors.BOLD)
            print_colored(f"╠{'═' * 62}╣", Colors.BLUE)

            to_delete = []
            for i, q in enumerate(questions):
                if i + 1 in selected_ids:
                    to_delete.append(q)
                    type_tag = '[单选]' if q['type'] == 'single' else '[多选]'
                    line = f"  {type_tag} {q['id']}. {_truncate_to_width(q['question'], 46)}"
                    print_colored("║" + _pad_to_width(line, 62) + "║", Colors.END)

            print_colored(f"╠{'═' * 62}╣", Colors.BLUE)
            print_colored("║" + _pad_to_width(f"  即将删除 {len(to_delete)} 道题目", 62) + "║", Colors.YELLOW)
            print_colored("║" + _pad_to_width("  删除后备份到 deleted_questions.json", 62) + "║", Colors.END)
            print_colored(f"╚{'═' * 62}╝", Colors.BLUE)

            confirm = input("\n确认删除？(y/n): ").strip().lower()
            if confirm == 'y':
                # 备份
                save_deleted_questions(to_delete)

                # 从题库中删除
                data['questions'] = [q for i, q in enumerate(questions) if i + 1 not in selected_ids]
                save_questions(data)

                print_colored(f"\n✓ 已删除 {len(to_delete)} 道题目，备份已保存到 deleted_questions.json", Colors.GREEN)
                input("按 Enter 返回主菜单...")
                return
            else:
                print_colored("\n已取消删除", Colors.YELLOW)
                input("按 Enter 继续...")
        else:
            # 尝试解析为题号选择
            valid_range = (start_idx + 1, end_idx)
            new_selection = parse_selection_input(user_input, valid_range)
            if new_selection:
                # 切换选中状态
                for num in new_selection:
                    if num in selected_ids:
                        selected_ids.discard(num)
                    else:
                        selected_ids.add(num)
            else:
                print_colored("请输入题号或操作命令", Colors.YELLOW)
                input("按 Enter 继续...")


def review_bank_wrong_questions(bank_path: str, bank_name: str) -> None:
    """题库错题回顾（从题库文件夹的错题本加载）"""
    from bank_manager import load_bank_wrong_questions
    data = load_bank_wrong_questions(bank_path)
    wrong_books = data.get('wrong_books', {})

    if not wrong_books:
        print_colored("\n✓ 暂无错题", Colors.GREEN)
        input("\n按 Enter 返回主菜单...")
        return

    print()
    print_colored(f"╔{'═' * 60}╗", Colors.BLUE)
    print_colored("║" + _center_to_width("错题本列表", 60) + "║", Colors.BOLD)
    print_colored(f"╠{'═' * 60}╣", Colors.BLUE)

    names = list(wrong_books.keys())
    for i, name in enumerate(names, 1):
        count = len(wrong_books[name])
        line = f"  {i}. {name}（{count} 题）"
        print_colored("║" + _pad_to_width(line, 60) + "║", Colors.END)

    print_colored(f"╠{'═' * 60}╣", Colors.BLUE)
    print_colored("║" + _pad_to_width("  输入编号选择错题本 | n 新建错题本 | q 返回", 60) + "║", Colors.END)
    print_colored(f"╚{'═' * 60}╝", Colors.BLUE)

    choice = input("请选择：").strip().lower()
    if choice == 'q':
        return

    if choice == 'n':
        new_name = input("  新建错题本名称：").strip()
        if not new_name:
            return
        # 创建空错题本并保存
        wrong_books[new_name] = []
        data['wrong_books'] = wrong_books
        filepath = os.path.join(bank_path, 'wrong_questions.json')
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print_colored(f'  ✓ 已创建空错题本"{new_name}"', Colors.GREEN)
        except IOError as e:
            print_colored(f"  无法保存：{e}", Colors.RED)
        input("\n按 Enter 返回主菜单...")
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(names):
            book_name = names[idx]
            wrong_questions = wrong_books[book_name]
            if not wrong_questions:
                print_colored("\n✓ 该错题本为空", Colors.GREEN)
                input("\n按 Enter 返回主菜单...")
                return

            print()
            print_colored(f"╔{'═' * 60}╗", Colors.BLUE)
            print_colored("║" + _center_to_width(f"错题本：{book_name}（{len(wrong_questions)} 题）", 60) + "║", Colors.BOLD)
            print_colored(f"╠{'═' * 60}╣", Colors.BLUE)

            for i, q in enumerate(wrong_questions, 1):
                line = _format_question_list_line(i, q)
                print_colored("║" + _pad_to_width(line, 60) + "║", Colors.END)

            print_colored(f"╠{'═' * 60}╣", Colors.BLUE)
            print_colored("║" + _pad_to_width("  操作：", 60) + "║", Colors.END)
            print_colored("║" + _pad_to_width("    s - 开始刷题", 60) + "║", Colors.END)
            print_colored("║" + _pad_to_width("    q - 返回", 60) + "║", Colors.END)
            print_colored(f"╚{'═' * 60}╝", Colors.BLUE)

            sub_choice = input("请选择：").strip().lower()
            if sub_choice == 'q':
                return
            if sub_choice != 's':
                print_colored("  请输入 s 或 q", Colors.RED)
                input("\n按 Enter 返回主菜单...")
                return

            total, correct, wrong = run_quiz(wrong_questions, 'sequential', bank_path=bank_path, bank_name=bank_name)
            display_stats(total, correct, len(wrong))
        else:
            print_colored("无效选择", Colors.RED)
            input("\n按 Enter 返回主菜单...")
    except ValueError:
        print_colored("请输入编号或 n", Colors.RED)
        input("\n按 Enter 返回主菜单...")


def _find_question(qid: int, qtype: str) -> dict:
    """从 QUESTION_BANK 中查找题目"""
    for q in QUESTION_BANK:
        if q['id'] == qid and q['type'] == qtype:
            return q
    return None


def _run_collection_quiz(name: str, sequential: bool = True) -> None:
    """在收藏夹内刷题"""
    data = load_collections()
    if name not in data['collections']:
        return

    qrefs = data['collections'][name]['questions']
    if not qrefs:
        print_colored("\n  收藏夹中暂无题目", Colors.YELLOW)
        input("按 Enter 继续...")
        return

    # Build full question list from references
    questions = []
    for qref in qrefs:
        q = _find_question(qref['id'], qref['type'])
        if q:
            questions.append(q)

    if not questions:
        print_colored("\n  收藏夹中题目已全部从题库删除", Colors.YELLOW)
        input("按 Enter 继续...")
        return

    if not sequential:
        random.shuffle(questions)
    total, correct, wrong = run_quiz(questions, mode='sequential', allow_collect=False)
    display_stats(total, correct, len(wrong))


def _export_collection_markdown(name: str) -> None:
    """导出收藏夹为 Markdown 文件"""
    data = load_collections()
    if name not in data['collections']:
        return

    qrefs = data['collections'][name]['questions']
    if not qrefs:
        print_colored("\n  收藏夹中暂无题目，无法导出", Colors.YELLOW)
        input("按 Enter 继续...")
        return

    # Group questions by type
    single_questions = []
    multi_questions = []
    for qref in qrefs:
        q = _find_question(qref['id'], qref['type'])
        if q:
            if q['type'] == 'single':
                single_questions.append(q)
            else:
                multi_questions.append(q)

    # Prompt for filename
    default_name = f"{name}.md"
    user_input = input(f"  导出到文件名（默认：{default_name}）：").strip()
    filename = user_input if user_input else default_name

    # Build markdown content
    lines = []

    def _format_question(q, num):
        """Format a single question as Markdown"""
        parts = []
        parts.append(f"**{num}. {q['question']}（　）**")
        if isinstance(q['options'], dict):
            for letter in sorted(q['options'].keys()):
                parts.append(f"{letter}. {q['options'][letter]}")
        else:
            for opt in q['options']:
                parts.append(opt)
        parts.append("")
        parts.append(f"**答案：{q['answer']}**")
        parts.append("")
        if q.get('explanation'):
            parts.append(f"**解析：** {q['explanation']}")
            parts.append("")
        parts.append("---")
        parts.append("")
        return parts

    if single_questions:
        lines.append("## 单选题")
        lines.append("")
        for i, q in enumerate(single_questions, 1):
            lines.extend(_format_question(q, i))

    if multi_questions:
        lines.append("## 多选题")
        lines.append("")
        for i, q in enumerate(multi_questions, 1):
            lines.extend(_format_question(q, i))

    content = '\n'.join(lines)

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

    print_colored(f"\n  ✓ 已导出到 {filename}（{len(single_questions) + len(multi_questions)} 题）", Colors.GREEN)
    input("按 Enter 继续...")


def collection_detail(name: str) -> None:
    """收藏夹详情界面"""
    while True:
        data = load_collections()
        if name not in data['collections']:
            print_colored(f'  收藏夹"{name}"不存在', Colors.RED)
            input("按 Enter 继续...")
            return

        questions = data['collections'][name]['questions']

        print()
        print_colored(f"╔{'═' * 60}╗", Colors.BLUE)
        print_colored("║" + _center_to_width(f"收藏夹：{name}（{len(questions)} 题）", 60) + "║", Colors.BOLD)
        print_colored(f"╠{'═' * 60}╣", Colors.BLUE)

        if not questions:
            print_colored("║" + _pad_to_width("  暂无题目", 60) + "║", Colors.YELLOW)
        else:
            for i, qref in enumerate(questions, 1):
                q = _find_question(qref['id'], qref['type'])
                if q:
                    line = _format_question_list_line(i, q)
                else:
                    line = f"  {i}. [已删除] ID={qref['id']}"
                print_colored("║" + _pad_to_width(line, 60) + "║", Colors.END)

        print_colored(f"╠{'═' * 60}╣", Colors.BLUE)
        print_colored("║" + _pad_to_width("  操作：", 60) + "║", Colors.END)
        if questions:
            print_colored("║" + _pad_to_width("    s - 开始刷题（顺序）", 60) + "║", Colors.END)
            print_colored("║" + _pad_to_width("    x - 开始刷题（随机）", 60) + "║", Colors.END)
            print_colored("║" + _pad_to_width("    输入题号 → 从收藏夹移除", 60) + "║", Colors.END)
        print_colored("║" + _pad_to_width("    r - 重命名收藏夹", 60) + "║", Colors.END)
        print_colored("║" + _pad_to_width("    d - 删除整个收藏夹", 60) + "║", Colors.END)
        if questions:
            print_colored("║" + _pad_to_width("    e - 导出为 Markdown", 60) + "║", Colors.END)
        print_colored("║" + _pad_to_width("    q - 返回", 60) + "║", Colors.END)
        print_colored(f"╚{'═' * 60}╝", Colors.BLUE)

        choice = input("请选择：").strip().lower()

        if choice == 'q':
            return
        elif choice == 's' and questions:
            _run_collection_quiz(name, sequential=True)
        elif choice == 'x' and questions:
            _run_collection_quiz(name, sequential=False)
        elif choice == 'r':
            new_name = input("新名称：").strip()
            if not new_name:
                print_colored("  名称不能为空", Colors.RED)
            elif rename_collection(name, new_name):
                print_colored(f'  ✓ 已重命名为"{new_name}"', Colors.GREEN)
                name = new_name  # Update local reference
            else:
                print_colored(f'  名称"{new_name}"已存在', Colors.RED)
            input("按 Enter 继续...")
        elif choice == 'd':
            confirm = input(f'确认删除收藏夹"{name}"？(y/n): ').strip().lower()
            if confirm == 'y':
                delete_collection(name)
                print_colored(f'  ✓ 已删除收藏夹"{name}"', Colors.GREEN)
                input("按 Enter 继续...")
                return
        elif choice == 'e' and questions:
            _export_collection_markdown(name)
        else:
            # Try as question number for removal
            try:
                idx = int(choice)
                if 1 <= idx <= len(questions):
                    qref = questions[idx - 1]
                    q = _find_question(qref['id'], qref['type'])
                    q_desc = q['question'][:30] if q else f"ID={qref['id']}"
                    confirm = input(f'确认移除第{idx}题「{q_desc}」？(y/n): ').strip().lower()
                    if confirm == 'y':
                        remove_from_collection(name, qref['id'], qref['type'])
                        print_colored("  ✓ 已移除", Colors.GREEN)
                        input("按 Enter 继续...")
                else:
                    print_colored(f"  无效题号", Colors.RED)
                    input("按 Enter 继续...")
            except ValueError:
                print_colored("  请输入有效操作", Colors.RED)
                input("按 Enter 继续...")


def collections_menu() -> None:
    """收藏夹管理主界面"""
    while True:
        data = load_collections()
        collections = data.get('collections', {})

        print()
        print_colored(f"╔{'═' * 60}╗", Colors.BLUE)
        print_colored("║" + _center_to_width("收藏夹管理", 60) + "║", Colors.BOLD)
        print_colored(f"╠{'═' * 60}╣", Colors.BLUE)

        if not collections:
            print_colored("║" + _pad_to_width("  暂无收藏夹，输入 n 新建", 60) + "║", Colors.YELLOW)
        else:
            for i, (name, info) in enumerate(collections.items(), 1):
                count = len(info.get('questions', []))
                line = f"  {i}. {name}（{count} 题）"
                print_colored("║" + _pad_to_width(line, 60) + "║", Colors.END)

        print_colored(f"╠{'═' * 60}╣", Colors.BLUE)
        print_colored("║" + _pad_to_width("  操作：", 60) + "║", Colors.END)
        if collections:
            print_colored("║" + _pad_to_width("    输入序号 → 查看/编辑该收藏夹", 60) + "║", Colors.END)
        print_colored("║" + _pad_to_width("    n - 新建收藏夹", 60) + "║", Colors.END)
        print_colored("║" + _pad_to_width("    q - 返回主菜单", 60) + "║", Colors.END)
        print_colored(f"╚{'═' * 60}╝", Colors.BLUE)

        choice = input("请选择：").strip().lower()

        if choice == 'q':
            break
        elif choice == 'n':
            name = input("新收藏夹名称：").strip()
            if not name:
                print_colored("  名称不能为空", Colors.RED)
                input("按 Enter 继续...")
                continue
            if create_collection(name):
                print_colored(f'  ✓ 已创建收藏夹"{name}"', Colors.GREEN)
            else:
                print_colored(f'  收藏夹"{name}"已存在', Colors.RED)
            input("按 Enter 继续...")
        else:
            # Try to interpret as collection index
            try:
                idx = int(choice)
                names = list(collections.keys())
                if 1 <= idx <= len(names):
                    collection_detail(names[idx - 1])
                else:
                    print_colored("  无效序号", Colors.RED)
                    input("按 Enter 继续...")
            except ValueError:
                print_colored("  请输入序号、n 或 q", Colors.RED)
                input("按 Enter 继续...")


def bank_collections_menu(bank_path: str, bank_name: str) -> None:
    """银行模式的收藏夹管理主界面"""
    from bank_manager import (load_bank_collections, create_bank_collection,
                              delete_bank_collection, rename_bank_collection)

    while True:
        data = load_bank_collections(bank_path)
        collections = data.get('collections', {})

        print()
        print_colored(f"╔{'═' * 60}╗", Colors.BLUE)
        print_colored("║" + _center_to_width(f"{bank_name} - 收藏夹管理", 60) + "║", Colors.BOLD)
        print_colored(f"╠{'═' * 60}╣", Colors.BLUE)

        if not collections:
            print_colored("║" + _pad_to_width("  暂无收藏夹，输入 n 新建", 60) + "║", Colors.YELLOW)
        else:
            for i, (name, info) in enumerate(collections.items(), 1):
                count = len(info.get('questions', []))
                line = f"  {i}. {name}（{count} 题）"
                print_colored("║" + _pad_to_width(line, 60) + "║", Colors.END)

        print_colored(f"╠{'═' * 60}╣", Colors.BLUE)
        print_colored("║" + _pad_to_width("  操作：", 60) + "║", Colors.END)
        if collections:
            print_colored("║" + _pad_to_width("    输入序号 → 查看/编辑该收藏夹", 60) + "║", Colors.END)
        print_colored("║" + _pad_to_width("    n - 新建收藏夹", 60) + "║", Colors.END)
        print_colored("║" + _pad_to_width("    q - 返回", 60) + "║", Colors.END)
        print_colored(f"╚{'═' * 60}╝", Colors.BLUE)

        choice = input("请选择：").strip().lower()

        if choice == 'q':
            break
        elif choice == 'n':
            name = input("新收藏夹名称：").strip()
            if not name:
                print_colored("  名称不能为空", Colors.RED)
                input("按 Enter 继续...")
                continue
            if create_bank_collection(bank_path, name):
                print_colored(f'  ✓ 已创建收藏夹"{name}"', Colors.GREEN)
            else:
                print_colored(f'  收藏夹"{name}"已存在', Colors.RED)
            input("按 Enter 继续...")
        else:
            # Try to interpret as collection index
            try:
                idx = int(choice)
                names = list(collections.keys())
                if 1 <= idx <= len(names):
                    bank_collection_detail(bank_path, bank_name, names[idx - 1])
                else:
                    print_colored("  无效序号", Colors.RED)
                    input("按 Enter 继续...")
            except ValueError:
                print_colored("  请输入序号、n 或 q", Colors.RED)
                input("按 Enter 继续...")


def bank_collection_detail(bank_path: str, bank_name: str, name: str) -> None:
    """银行模式的收藏夹详情界面"""
    from bank_manager import (load_bank_collections, delete_bank_collection,
                              rename_bank_collection, remove_from_bank_collection)

    while True:
        data = load_bank_collections(bank_path)
        if name not in data.get('collections', {}):
            print_colored(f'  收藏夹"{name}"不存在', Colors.RED)
            input("按 Enter 继续...")
            return

        questions = data['collections'][name].get('questions', [])

        print()
        print_colored(f"╔{'═' * 60}╗", Colors.BLUE)
        print_colored("║" + _center_to_width(f"收藏夹：{name}（{len(questions)} 题）", 60) + "║", Colors.BOLD)
        print_colored(f"╠{'═' * 60}╣", Colors.BLUE)

        if not questions:
            print_colored("║" + _pad_to_width("  暂无题目", 60) + "║", Colors.YELLOW)
        else:
            for i, qref in enumerate(questions, 1):
                q = _find_question(qref['id'], qref['type'])
                if q:
                    line = _format_question_list_line(i, q)
                else:
                    line = f"  {i}. [已删除] ID={qref['id']}"
                print_colored("║" + _pad_to_width(line, 60) + "║", Colors.END)

        print_colored(f"╠{'═' * 60}╣", Colors.BLUE)
        print_colored("║" + _pad_to_width("  操作：", 60) + "║", Colors.END)
        if questions:
            print_colored("║" + _pad_to_width("    s - 开始刷题（顺序）", 60) + "║", Colors.END)
            print_colored("║" + _pad_to_width("    x - 开始刷题（随机）", 60) + "║", Colors.END)
            print_colored("║" + _pad_to_width("    输入题号 → 从收藏夹移除", 60) + "║", Colors.END)
        print_colored("║" + _pad_to_width("    r - 重命名收藏夹", 60) + "║", Colors.END)
        print_colored("║" + _pad_to_width("    d - 删除整个收藏夹", 60) + "║", Colors.END)
        if questions:
            print_colored("║" + _pad_to_width("    e - 导出为 Markdown", 60) + "║", Colors.END)
        print_colored("║" + _pad_to_width("    q - 返回", 60) + "║", Colors.END)
        print_colored(f"╚{'═' * 60}╝", Colors.BLUE)

        choice = input("请选择：").strip().lower()

        if choice == 'q':
            return
        elif choice == 's' and questions:
            _run_collection_quiz(name, sequential=True)
        elif choice == 'x' and questions:
            _run_collection_quiz(name, sequential=False)
        elif choice == 'r':
            new_name = input("新名称：").strip()
            if not new_name:
                print_colored("  名称不能为空", Colors.RED)
            elif rename_bank_collection(bank_path, name, new_name):
                print_colored(f'  ✓ 已重命名为"{new_name}"', Colors.GREEN)
                name = new_name  # Update local reference
            else:
                print_colored(f'  名称"{new_name}"已存在', Colors.RED)
            input("按 Enter 继续...")
        elif choice == 'd':
            confirm = input(f'确认删除收藏夹"{name}"？(y/n): ').strip().lower()
            if confirm == 'y':
                delete_bank_collection(bank_path, name)
                print_colored(f'  ✓ 已删除收藏夹"{name}"', Colors.GREEN)
                input("按 Enter 继续...")
                return
        elif choice == 'e' and questions:
            _export_collection_markdown(name)
        else:
            # Try as question number for removal
            try:
                idx = int(choice)
                if 1 <= idx <= len(questions):
                    qref = questions[idx - 1]
                    q = _find_question(qref['id'], qref['type'])
                    q_desc = q['question'][:30] if q else f"ID={qref['id']}"
                    confirm = input(f'确认移除第{idx}题「{q_desc}」？(y/n): ').strip().lower()
                    if confirm == 'y':
                        remove_from_bank_collection(bank_path, name, qref['id'], qref['type'])
                        print_colored("  ✓ 已移除", Colors.GREEN)
                        input("按 Enter 继续...")
                else:
                    print_colored(f"  无效题号", Colors.RED)
                    input("按 Enter 继续...")
            except ValueError:
                print_colored("  请输入有效操作", Colors.RED)
                input("按 Enter 继续...")


def bank_batch_delete_questions(bank_path: str, bank_name: str, questions: list) -> None:
    """银行模式的批量删题功能"""
    from bank_manager import add_to_bank_deleted

    if not questions:
        print_colored("\n题库为空，没有可删除的题目", Colors.GREEN)
        input("按 Enter 继续...")
        return

    PAGE_SIZE = 15
    current_page = 0
    selected_ids = set()  # 使用题目的序号（1-based）
    total_pages = (len(questions) + PAGE_SIZE - 1) // PAGE_SIZE

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        start_idx = current_page * PAGE_SIZE
        end_idx = min(start_idx + PAGE_SIZE, len(questions))
        page_questions = questions[start_idx:end_idx]

        print_colored(f"╔{'═' * 62}╗", Colors.BLUE)
        title = f"{bank_name} - 批量删题（第 {current_page + 1}/{total_pages} 页）"
        print_colored("║" + _center_to_width(title, 62) + "║", Colors.BOLD)
        print_colored(f"╠{'═' * 62}╣", Colors.BLUE)

        for i, q in enumerate(page_questions):
            global_idx = start_idx + i + 1
            type_tag = '[单选]' if q['type'] == 'single' else '[多选]'
            mark = "●" if global_idx in selected_ids else "○"
            qtext = _truncate_to_width(q['question'], 46)
            line = f"  {mark} {global_idx:>3}. {type_tag} {qtext}"
            print_colored("║" + _pad_to_width(line, 62) + "║", Colors.END)

        print_colored(f"╠{'═' * 62}╣", Colors.BLUE)
        status = f"  已选：{len(selected_ids)} 题"
        print_colored("║" + _pad_to_width(status, 62) + "║", Colors.YELLOW)
        help_text = "  输入题号切换 | n-下页 | p-上页 | done-确认 | q-取消"
        print_colored("║" + _pad_to_width(help_text, 62) + "║", Colors.END)
        print_colored(f"╚{'═' * 62}╝", Colors.BLUE)

        # 获取用户输入
        user_input = input("\n请输入: ").strip().lower()

        if user_input == 'q' or user_input == 'quit':
            return
        elif user_input == 'n' or user_input == 'next':
            if current_page < total_pages - 1:
                current_page += 1
        elif user_input == 'p' or user_input == 'prev':
            if current_page > 0:
                current_page -= 1
        elif user_input == 'all':
            for i in range(len(page_questions)):
                selected_ids.add(start_idx + i + 1)
        elif user_input == 'none':
            for i in range(len(page_questions)):
                selected_ids.discard(start_idx + i + 1)
        elif user_input == 'done' or user_input == 'd':
            if not selected_ids:
                print_colored("\n未选择任何题目", Colors.YELLOW)
                input("按 Enter 继续...")
                continue

            # 确认删除
            os.system('cls' if os.name == 'nt' else 'clear')
            print_colored(f"╔{'═' * 62}╗", Colors.BLUE)
            print_colored("║" + _center_to_width("确认删除", 62) + "║", Colors.BOLD)
            print_colored(f"╠{'═' * 62}╣", Colors.BLUE)

            to_delete = []
            for i, q in enumerate(questions):
                if i + 1 in selected_ids:
                    to_delete.append(q)
                    type_tag = '[单选]' if q['type'] == 'single' else '[多选]'
                    line = f"  {type_tag} {q['id']}. {_truncate_to_width(q['question'], 46)}"
                    print_colored("║" + _pad_to_width(line, 62) + "║", Colors.END)

            print_colored(f"╠{'═' * 62}╣", Colors.BLUE)
            print_colored("║" + _pad_to_width(f"  即将删除 {len(to_delete)} 道题目", 62) + "║", Colors.YELLOW)
            print_colored("║" + _pad_to_width("  删除后可通过 deleted.json 恢复", 62) + "║", Colors.END)
            print_colored(f"╚{'═' * 62}╝", Colors.BLUE)

            confirm = input("\n确认删除？(y/n): ").strip().lower()
            if confirm == 'y':
                # 标记为已删除
                deleted_count = 0
                for q in to_delete:
                    if add_to_bank_deleted(bank_path, q['id'], q['type']):
                        deleted_count += 1

                print_colored(f"\n✓ 已删除 {deleted_count} 道题目", Colors.GREEN)
                input("按 Enter 返回主菜单...")
                return
            else:
                print_colored("\n已取消删除", Colors.YELLOW)
                input("按 Enter 继续...")
        else:
            # 尝试解析为题号选择
            valid_range = (start_idx + 1, end_idx)
            new_selection = parse_selection_input(user_input, valid_range)
            if new_selection:
                # 切换选中状态
                for num in new_selection:
                    if num in selected_ids:
                        selected_ids.discard(num)
                    else:
                        selected_ids.add(num)
            else:
                print_colored("请输入题号或操作命令", Colors.YELLOW)
                input("按 Enter 继续...")


def _edit_question_in_md(question: dict, bank_path: str) -> bool:
    """
    编辑 .md 文件中的题目

    Args:
        question: 题目字典（需包含 source 字段）
        bank_path: 题库文件夹路径

    Returns:
        是否编辑成功
    """
    source = question.get('source', '')
    if not source:
        print_colored("⚠ 无法确定题目来源文件", Colors.YELLOW)
        return False

    filepath = os.path.join(bank_path, source)
    if not os.path.exists(filepath):
        print_colored(f"⚠ 找不到源文件: {source}", Colors.YELLOW)
        return False

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except IOError as e:
        print_colored(f"⚠ 无法读取文件: {e}", Colors.YELLOW)
        return False

    # 找到题目所在的块（以 --- 分隔）
    blocks = content.split('---')
    target_block_idx = None
    q_id = question['id']
    q_type = question['type']
    current_type = 'single'

    for i, block in enumerate(blocks):
        # 检测章节标题
        header_match = re.search(r'^#+\s*(.+)', block, re.MULTILINE)
        if header_match:
            header_text = header_match.group(1).strip().lower()
            if '单选' in header_text or 'single' in header_text:
                current_type = 'single'
            elif '多选' in header_text or 'multiple' in header_text:
                current_type = 'multi'

        # 检测单题类型覆盖
        if '<!-- single -->' in block:
            current_type = 'single'
        elif '<!-- multi -->' in block:
            current_type = 'multi'

        # 匹配题号
        question_match = re.search(r'\*\*(\d+)\.\s*(.+?)（\s*）.*?\*\*', block)
        if question_match:
            block_id = int(question_match.group(1))
            block_type = current_type
            if block_id == q_id and block_type == q_type:
                target_block_idx = i
                break

    if target_block_idx is None:
        print_colored("⚠ 在源文件中找不到该题目", Colors.YELLOW)
        return False

    # 显示当前题目内容
    block = blocks[target_block_idx]
    print_colored("\n当前题目内容:", Colors.BOLD)
    print_colored(block.strip(), Colors.END)

    # 编辑题型
    type_name = '单选' if question['type'] == 'single' else '多选'
    print_colored("\n编辑（直接回车保持原值）:", Colors.BOLD)
    new_type = input(f"题型 [{type_name}] (1=单选 2=多选): ").strip()
    if new_type == '1' and question['type'] != 'single':
        # 从多选改为单选：添加 <!-- single --> 注释
        if '<!-- multi -->' in block:
            block = block.replace('<!-- multi -->', '<!-- single -->')
        elif '<!-- single -->' not in block:
            block = '<!-- single -->\n' + block
        print_colored("  题型已更新: 多选 → 单选", Colors.GREEN)
    elif new_type == '2' and question['type'] != 'multi':
        # 从单选改为多选：添加 <!-- multi --> 注释
        if '<!-- single -->' in block:
            block = block.replace('<!-- single -->', '<!-- multi -->')
        elif '<!-- multi -->' not in block:
            block = '<!-- multi -->\n' + block
        print_colored("  题型已更新: 单选 → 多选", Colors.GREEN)

    # 编辑答案
    new_answer = input(f"答案 [{question['answer']}]: ").strip().upper()
    if new_answer and new_answer != question['answer']:
        # 替换答案
        block = re.sub(
            r'\*\*答案：[A-D]+\*\*',
            f'**答案：{new_answer}**',
            block
        )
        print_colored(f"  答案已更新: {question['answer']} → {new_answer}", Colors.GREEN)

    # 编辑选项
    if isinstance(question['options'], dict):
        for letter in sorted(question['options'].keys()):
            old_opt = question['options'][letter]
            new_opt = input(f"选项{letter} [{old_opt[:30]}...]: ").strip()
            if new_opt and new_opt != old_opt:
                # 替换选项
                block = re.sub(
                    rf'({letter}\.\s*).*',
                    rf'\g<1>{new_opt}',
                    block,
                    count=1
                )
                print_colored(f"  选项{letter}已更新", Colors.GREEN)

    # 编辑解析
    old_exp = question.get('explanation', '')
    new_exp = input(f"解析 [{old_exp[:20]}...]: ").strip()
    if new_exp and new_exp != old_exp:
        # 替换解析
        if '**解析：**' in block:
            block = re.sub(
                r'\*\*解析：\*\*\s*.*',
                f'**解析：** {new_exp}',
                block,
                count=1
            )
        else:
            # 如果没有解析字段，在答案后添加
            block = re.sub(
                r'(\*\*答案：[A-D]+\*\*)',
                f'\\1\n\n**解析：** {new_exp}',
                block
            )
        print_colored("  解析已更新", Colors.GREEN)

    # 保存修改
    blocks[target_block_idx] = block
    new_content = '---'.join(blocks)

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print_colored("✓ 已保存到源文件", Colors.GREEN)
        return True
    except IOError as e:
        print_colored(f"⚠ 保存失败: {e}", Colors.YELLOW)
        return False


def bank_handle_flagged_questions(bank_path: str, bank_name: str) -> None:
    """银行模式的处理标记题目"""
    from bank_manager import load_bank_flagged, remove_from_bank_flagged, add_to_bank_deleted

    while True:
        data = load_bank_flagged(bank_path)
        flagged = data.get('flagged', [])

        if not flagged:
            print_colored("\n没有标记的题目", Colors.GREEN)
            input("按 Enter 继续...")
            return

        os.system('cls' if os.name == 'nt' else 'clear')
        print_colored(f"\n{bank_name} - 标记待处理的题目 ({len(flagged)} 道)", Colors.BOLD)
        print_colored("=" * 50, Colors.BLUE)

        for i, qref in enumerate(flagged, 1):
            # Look up full question from current bank questions
            q = _find_question(qref['id'], qref['type'])
            if q:
                type_label = "单选" if q['type'] == 'single' else "多选"
                reason = qref.get('reason', '无')
                print_colored(f"\n{i}. [{type_label}] {q['question'][:60]}", Colors.END)
                print_colored(f"   答案: {q['answer']}  |  标记原因: {reason}", Colors.YELLOW)
            else:
                print_colored(f"\n{i}. [已删除] ID={qref['id']}", Colors.END)

        print_colored("\n操作：E-编辑  D-删除  C-取消标记  S-跳过  Q-退出", Colors.BLUE)
        choice = input("请选择: ").strip().upper()

        if choice == 'Q':
            break
        elif choice in ['E', 'D', 'C']:
            idx = input("请输入题目序号: ").strip()
            try:
                idx = int(idx) - 1
                if 0 <= idx < len(flagged):
                    target = flagged[idx]
                    q = _find_question(target['id'], target['type'])

                    if choice == 'E':
                        if q:
                            if _edit_question_in_md(q, bank_path):
                                # 编辑成功后取消标记
                                remove_from_bank_flagged(bank_path, target['id'], target['type'])
                                print_colored("✓ 已取消标记", Colors.GREEN)
                        else:
                            print_colored("⚠ 题目已删除，无法编辑", Colors.YELLOW)

                    elif choice == 'D':
                        # 标记为已删除
                        add_to_bank_deleted(bank_path, target['id'], target['type'])
                        remove_from_bank_flagged(bank_path, target['id'], target['type'])
                        print_colored("✓ 已标记为删除", Colors.GREEN)

                    elif choice == 'C':
                        remove_from_bank_flagged(bank_path, target['id'], target['type'])
                        print_colored("✓ 已取消标记", Colors.GREEN)
                else:
                    print_colored("无效序号", Colors.YELLOW)
            except ValueError:
                print_colored("请输入数字", Colors.YELLOW)
        elif choice == 'S':
            pass  # 跳过
        else:
            print_colored("无效选择", Colors.YELLOW)

        input("\n按 Enter 继续...")


def handle_flagged_questions() -> None:
    """处理标记的题目"""
    if load_questions is None:
        print_colored("⚠ 功能需要 import_questions.py", Colors.YELLOW)
        return

    data = load_questions()
    flagged = [q for q in data['questions'] if q.get('flagged')]

    if not flagged:
        print_colored("\n没有标记的题目", Colors.GREEN)
        input("按 Enter 继续...")
        return

    while True:
        # 重新加载（可能有修改）
        data = load_questions()
        flagged = [q for q in data['questions'] if q.get('flagged')]

        if not flagged:
            print_colored("\n所有标记题目已处理完毕", Colors.GREEN)
            break

        os.system('cls' if os.name == 'nt' else 'clear')
        print_colored(f"\n标记待处理的题目 ({len(flagged)} 道)", Colors.BOLD)
        print_colored("=" * 50, Colors.BLUE)

        for i, q in enumerate(flagged, 1):
            reason = q.get('flag_reason', '无')
            print_colored(f"\n{i}. [{q['type']}] {q['question'][:60]}", Colors.END)
            print_colored(f"   答案: {q['answer']}  |  标记原因: {reason}", Colors.YELLOW)

        print_colored("\n操作：E-编辑  D-删除  S-跳过  C-取消标记  Q-退出", Colors.BLUE)
        choice = input("请选择: ").strip().upper()

        if choice == 'Q':
            break
        elif choice in ['E', 'D', 'S', 'C']:
            idx = input("请输入题目序号: ").strip()
            try:
                idx = int(idx) - 1
                if 0 <= idx < len(flagged):
                    target = flagged[idx]
                    if choice == 'E':
                        edit_question(target, data)
                    elif choice == 'D':
                        data['questions'] = [q for q in data['questions']
                                             if not (q.get('id') == target.get('id')
                                                     and q.get('type') == target.get('type'))]
                        save_questions(data)
                        print_colored("✓ 已删除", Colors.GREEN)
                    elif choice == 'S':
                        pass  # 跳过
                    elif choice == 'C':
                        for q in data['questions']:
                            if q.get('id') == target.get('id') and q.get('type') == target.get('type'):
                                q['flagged'] = False
                                q['flag_reason'] = None
                        save_questions(data)
                        print_colored("✓ 已取消标记", Colors.GREEN)
                else:
                    print_colored("无效序号", Colors.YELLOW)
            except ValueError:
                print_colored("请输入数字", Colors.YELLOW)
        else:
            print_colored("无效选择", Colors.YELLOW)

        input("\n按 Enter 继续...")


def edit_question(question: dict, data: dict) -> None:
    """
    编辑题目

    Args:
        question: 要编辑的题目
        data: 完整题库数据
    """
    from import_questions import save_questions

    print_colored("\n编辑题目（直接回车保持原值）:", Colors.BOLD)

    new_q = input(f"题干 [{question['question'][:30]}...]: ").strip()
    if new_q:
        question['question'] = new_q

    new_a = input(f"答案 [{question['answer']}]: ").strip()
    if new_a:
        question['answer'] = new_a.upper()

    if isinstance(question['options'], dict):
        for letter in sorted(question['options'].keys()):
            new_opt = input(f"选项{letter} [{question['options'][letter][:20]}...]: ").strip()
            if new_opt:
                question['options'][letter] = new_opt
    elif isinstance(question['options'], list):
        new_options = []
        for opt in question['options']:
            new_opt = input(f"选项 [{opt[:30]}...]: ").strip()
            new_options.append(new_opt if new_opt else opt)
        question['options'] = new_options

    new_exp = input(f"解析 [{(question.get('explanation') or '')[:20]}...]: ").strip()
    if new_exp:
        question['explanation'] = new_exp

    # 取消标记
    question['flagged'] = False
    question['flag_reason'] = None

    save_questions(data)
    print_colored("✓ 已保存", Colors.GREEN)


def display_bank_menu(banks: list) -> None:
    """显示题库选择菜单"""
    os.system('cls' if os.name == 'nt' else 'clear')

    print_colored(f"╔{'═' * 60}╗", Colors.BLUE)
    print_colored("║" + _center_to_width("选择题库", 60) + "║", Colors.BOLD)
    print_colored(f"╠{'═' * 60}╣", Colors.BLUE)

    if not banks:
        print_colored("║" + _pad_to_width("  暂无题库，请在 banks/ 文件夹中添加", 60) + "║", Colors.YELLOW)
    else:
        for i, bank in enumerate(banks, 1):
            q_count = len(bank['questions'])
            info = f"{i}. {bank['name']}（{q_count} 题）"
            print_colored("║" + _pad_to_width("  " + info, 60) + "║", Colors.END)

    print_colored(f"╠{'═' * 60}╣", Colors.BLUE)
    print_colored("║" + _pad_to_width("  0. 退出", 60) + "║", Colors.END)
    print_colored(f"╚{'═' * 60}╝", Colors.BLUE)
    print()


def display_menu(bank_name: str = '', questions: list = None) -> None:
    """显示主菜单"""
    os.system('cls' if os.name == 'nt' else 'clear')

    if questions is None:
        questions = QUESTION_BANK

    # 动态计算题数
    single_count = len(get_questions_by_type(questions, 'single'))
    multi_count = len(get_questions_by_type(questions, 'multi'))
    total_count = len(questions)

    # 计算标记题数（仅在非题库模式下，因为题库模式的 .md 题目不支持 flagged 字段）
    flagged_count = 0
    if not bank_name and load_questions is not None:
        try:
            data = load_questions()
            flagged_count = sum(1 for q in data.get('questions', []) if q.get('flagged'))
        except Exception:
            pass

    # 计算收藏夹数量（仅在非题库模式下）
    collection_count = 0
    if not bank_name:
        collections_data = load_collections()
        collection_count = len(collections_data.get('collections', {}))

    # The box has 62 display columns: ║ (1) + 60 inner + ║ (1)
    # So all inner content must pad/center to exactly 60 display-width columns.
    print_colored(f"╔{'═' * 60}╗", Colors.BLUE)
    title = f"{bank_name}选择题刷题系统" if bank_name else "选择题刷题系统"
    print_colored("║" + _center_to_width(title, 60) + "║", Colors.BOLD)
    print_colored(f"╠{'═' * 60}╣", Colors.BLUE)

    # 显示题库信息
    info = f"题库：{total_count} 道（单选 {single_count} / 多选 {multi_count}）"
    print_colored("║" + _pad_to_width("  " + info, 60) + "║", Colors.END)
    if flagged_count > 0:
        flag_info = f"标记待处理：{flagged_count} 道"
        print_colored("║" + _pad_to_width("  " + flag_info, 60) + "║", Colors.YELLOW)
    if collection_count > 0:
        coll_info = f"收藏夹：{collection_count} 个"
        print_colored("║" + _pad_to_width("  " + coll_info, 60) + "║", Colors.END)
    print_colored(f"╠{'═' * 60}╣", Colors.BLUE)

    menu_items = [
        f"1. 顺序刷题（单选题 {single_count}道）",
        f"2. 随机刷题（单选题 {single_count}道）",
        f"3. 顺序刷题（多选题 {multi_count}道）",
        f"4. 随机刷题（多选题 {multi_count}道）",
        f"5. 顺序刷题（全部 {total_count}道）",
        f"6. 随机刷题（全部 {total_count}道）",
        "7. 错题回顾",
    ]
    if bank_name:
        menu_items.extend([
            "8. 处理标记题目",
            "9. 批量删题",
            "10. 收藏夹管理",
        ])
    else:
        menu_items.extend([
            "8. 处理标记题目",
            "9. 批量删题",
            "10. 收藏夹管理",
        ])
    if bank_name:
        menu_items.append("11. 返回题库选择")
    menu_items.append("0. 退出")
    for item in menu_items:
        print_colored("║" + _pad_to_width("  " + item, 60) + "║", Colors.END)
    print_colored(f"╚{'═' * 60}╝", Colors.BLUE)
    print()


def get_questions_by_type(questions: list, q_type: str) -> list:
    """
    根据题型筛选题目

    Args:
        questions: 题目列表
        q_type: 题型 ('single' 或 'multi')

    Returns:
        筛选后的题目列表
    """
    return [q for q in questions if q['type'] == q_type]


def main() -> None:
    """主程序"""
    global QUESTION_BANK

    # 检查 banks/ 文件夹是否存在
    if not os.path.exists(BANKS_FOLDER):
        os.makedirs(BANKS_FOLDER, exist_ok=True)
        print()
        print("╔══════════════════════════════════════╗")
        print("║" + _pad_to_width("  提示", 36) + "║")
        print("╠══════════════════════════════════════╣")
        print("║" + _pad_to_width("  未找到 banks 文件夹", 36) + "║")
        print("║" + _pad_to_width("  已自动创建 banks/", 36) + "║")
        print("║" + _pad_to_width("", 36) + "║")
        print("║" + _pad_to_width("  请在 banks/ 下创建子文件夹并放入", 36) + "║")
        print("║" + _pad_to_width("  .md 或 .json 格式的题库文件", 36) + "║")
        print("║" + _pad_to_width("  然后重新启动程序", 36) + "║")
        print("╚══════════════════════════════════════╝")
        print()
        input("按 Enter 退出...")
        return

    # 扫描 banks/ 文件夹
    banks = _scan_banks_folder(BANKS_FOLDER) if _scan_banks_folder is not None else []

    # banks/ 为空时提示
    if not banks:
        print()
        print("╔══════════════════════════════════════╗")
        print("║" + _pad_to_width("  提示", 36) + "║")
        print("╠══════════════════════════════════════╣")
        print("║" + _pad_to_width("  banks/ 文件夹为空", 36) + "║")
        print("║" + _pad_to_width("", 36) + "║")
        print("║" + _pad_to_width("  请在 banks/ 下创建子文件夹并放入", 36) + "║")
        print("║" + _pad_to_width("  .md 或 .json 格式的题库文件", 36) + "║")
        print("║" + _pad_to_width("  然后重新启动程序", 36) + "║")
        print("╚══════════════════════════════════════╝")
        print()
        input("按 Enter 退出...")
        return

    if banks:
        # 两层菜单：先选题库，再选操作
        while True:
            display_bank_menu(banks)

            try:
                choice = input("请选择题库编号：").strip()
            except EOFError:
                break

            if choice == '0':
                print_colored("\n感谢使用，再见！", Colors.GREEN)
                break

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(banks):
                    _run_bank_menu(banks[idx])
                else:
                    print_colored("无效选择，请重新输入", Colors.RED)
                    input("按 Enter 继续...")
            except ValueError:
                print_colored("请输入数字", Colors.RED)
                input("按 Enter 继续...")
    else:
        # 无 banks 文件夹，使用内置题库（向后兼容）
        _run_builtin_menu()


def _run_builtin_menu() -> None:
    """使用内置 QUESTION_BANK 的单层菜单（无 banks 文件夹时的后备模式）"""
    global QUESTION_BANK

    loaded = load_question_bank()
    if loaded:
        QUESTION_BANK = loaded
    elif not QUESTION_BANK:
        print_colored("错误：题库为空，请先运行导入命令：", Colors.RED)
        print_colored("  python import_questions.py import <markdown文件>", Colors.YELLOW)
        return

    while True:
        display_menu()

        try:
            choice = input("请选择 [0-10]: ").strip()
        except EOFError:
            break

        if choice == '0':
            print_colored("\n感谢使用，再见！", Colors.GREEN)
            break

        elif choice == '1':
            questions = get_questions_by_type(QUESTION_BANK, 'single')
            total, correct, wrong = run_quiz(questions, 'sequential')
            display_stats(total, correct, len(wrong))

        elif choice == '2':
            questions = get_questions_by_type(QUESTION_BANK, 'single')
            total, correct, wrong = run_quiz(questions, 'random')
            display_stats(total, correct, len(wrong))

        elif choice == '3':
            questions = get_questions_by_type(QUESTION_BANK, 'multi')
            total, correct, wrong = run_quiz(questions, 'sequential')
            display_stats(total, correct, len(wrong))

        elif choice == '4':
            questions = get_questions_by_type(QUESTION_BANK, 'multi')
            total, correct, wrong = run_quiz(questions, 'random')
            display_stats(total, correct, len(wrong))

        elif choice == '5':
            total, correct, wrong = run_quiz(QUESTION_BANK, 'sequential')
            display_stats(total, correct, len(wrong))

        elif choice == '6':
            total, correct, wrong = run_quiz(QUESTION_BANK, 'random')
            display_stats(total, correct, len(wrong))

        elif choice == '7':
            wrong_questions = load_wrong_questions()
            if not wrong_questions:
                print_colored("\n✓ 错题本为空，没有需要复习的题目", Colors.GREEN)
                input("\n按 Enter 返回主菜单...")
                continue

            print_colored(f"\n共有 {len(wrong_questions)} 道错题", Colors.YELLOW)
            total, correct, wrong = run_quiz(wrong_questions, 'sequential')
            display_stats(total, correct, len(wrong))

        elif choice == '8':
            handle_flagged_questions()

        elif choice == '9':
            batch_delete_questions()

        elif choice == '10':
            collections_menu()

        else:
            print_colored("⚠ 无效选择，请重新输入", Colors.YELLOW)
            input("\n按 Enter 继续...")


def _check_resume_progress(bank_path: str, bank_name: str, mode: str, question_type: str) -> Optional[dict]:
    """
    检测是否有可恢复的进度

    Args:
        bank_path: 题库路径
        bank_name: 题库名称
        mode: 刷题模式 ('sequential' 或 'random')
        question_type: 题型 ('single', 'multi', 'all')

    Returns:
        恢复数据或 None
    """
    from bank_manager import load_quiz_progress, delete_quiz_progress

    progress = load_quiz_progress(bank_path)
    if not progress:
        return None

    # 检查模式是否匹配
    if progress.get('mode') != mode or progress.get('question_type') != question_type:
        return None

    # 显示提示
    current = progress.get('current_idx', 0)
    total = progress.get('total_questions', 0)
    correct = progress.get('correct_count', 0)

    print()
    print_colored("╔══════════════════════════════════════════════╗", Colors.YELLOW)
    print_colored("║" + _pad_to_width("  检测到上次未完成的刷题", 44) + "║", Colors.YELLOW)
    print_colored("║" + _pad_to_width(f"  做到第 {current}/{total} 题，已答对 {correct} 题", 44) + "║", Colors.YELLOW)
    print_colored("╠══════════════════════════════════════════════╣", Colors.YELLOW)
    print_colored("║" + _pad_to_width("  1. 继续上次", 44) + "║", Colors.END)
    print_colored("║" + _pad_to_width("  2. 重新开始", 44) + "║", Colors.END)
    print_colored("╚══════════════════════════════════════════════╝", Colors.YELLOW)
    print()

    while True:
        try:
            choice = input("请选择 [1/2]: ").strip()
        except EOFError:
            return None

        if choice == '1':
            return progress
        elif choice == '2':
            delete_quiz_progress(bank_path)
            return None
        else:
            print_colored("请输入 1 或 2", Colors.YELLOW)


def _run_bank_menu(bank: dict) -> None:
    """运行单个题库的菜单"""
    global QUESTION_BANK

    questions = bank['questions']
    bank_name = bank['name']
    bank_path = bank['path']
    # 设置全局题库，使 _find_question 等函数能正常工作
    QUESTION_BANK = questions

    while True:
        display_menu(bank_name, questions)

        try:
            choice = input("请选择 [0-11]: ").strip()
        except EOFError:
            return

        if choice == '0':
            print_colored("\n感谢使用，再见！", Colors.GREEN)
            exit()

        elif choice == '11':
            # 返回题库选择
            return

        elif choice == '1':
            qs = get_questions_by_type(questions, 'single')
            resume_data = _check_resume_progress(bank_path, bank_name, 'sequential', 'single')
            if resume_data:
                from bank_manager import delete_quiz_progress
                delete_quiz_progress(bank_path)
            total, correct, wrong = run_quiz(qs, 'sequential', bank_path=bank_path, bank_name=bank_name, resume_data=resume_data)
            display_stats(total, correct, len(wrong), bank_name)

        elif choice == '2':
            qs = get_questions_by_type(questions, 'single')
            resume_data = _check_resume_progress(bank_path, bank_name, 'random', 'single')
            if resume_data:
                from bank_manager import delete_quiz_progress
                delete_quiz_progress(bank_path)
            total, correct, wrong = run_quiz(qs, 'random', bank_path=bank_path, bank_name=bank_name, resume_data=resume_data)
            display_stats(total, correct, len(wrong), bank_name)

        elif choice == '3':
            qs = get_questions_by_type(questions, 'multi')
            resume_data = _check_resume_progress(bank_path, bank_name, 'sequential', 'multi')
            if resume_data:
                from bank_manager import delete_quiz_progress
                delete_quiz_progress(bank_path)
            total, correct, wrong = run_quiz(qs, 'sequential', bank_path=bank_path, bank_name=bank_name, resume_data=resume_data)
            display_stats(total, correct, len(wrong), bank_name)

        elif choice == '4':
            qs = get_questions_by_type(questions, 'multi')
            resume_data = _check_resume_progress(bank_path, bank_name, 'random', 'multi')
            if resume_data:
                from bank_manager import delete_quiz_progress
                delete_quiz_progress(bank_path)
            total, correct, wrong = run_quiz(qs, 'random', bank_path=bank_path, bank_name=bank_name, resume_data=resume_data)
            display_stats(total, correct, len(wrong), bank_name)

        elif choice == '5':
            resume_data = _check_resume_progress(bank_path, bank_name, 'sequential', 'all')
            if resume_data:
                from bank_manager import delete_quiz_progress
                delete_quiz_progress(bank_path)
            total, correct, wrong = run_quiz(questions, 'sequential', bank_path=bank_path, bank_name=bank_name, resume_data=resume_data)
            display_stats(total, correct, len(wrong), bank_name)

        elif choice == '6':
            resume_data = _check_resume_progress(bank_path, bank_name, 'random', 'all')
            if resume_data:
                from bank_manager import delete_quiz_progress
                delete_quiz_progress(bank_path)
            total, correct, wrong = run_quiz(questions, 'random', bank_path=bank_path, bank_name=bank_name, resume_data=resume_data)
            display_stats(total, correct, len(wrong), bank_name)

        elif choice == '7':
            review_bank_wrong_questions(bank_path, bank_name)

        elif choice == '8':
            bank_handle_flagged_questions(bank_path, bank_name)

        elif choice == '9':
            bank_batch_delete_questions(bank_path, bank_name, questions)

        elif choice == '10':
            bank_collections_menu(bank_path, bank_name)

        else:
            print_colored("⚠ 无效选择，请重新输入", Colors.YELLOW)
            input("\n按 Enter 继续...")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\n\n程序已中断", Colors.YELLOW)
        sys.exit(0)
