#!/usr/bin/env python3
"""题库文件夹扫描和管理模块"""

import os
import json
from typing import List, Dict, Optional
from parse_markdown import parse_markdown


def scan_banks_folder(banks_dir: str = 'banks') -> List[Dict]:
    """
    扫描 banks/ 文件夹，返回题库列表

    Args:
        banks_dir: banks 文件夹路径

    Returns:
        题库列表，每个题库包含 name, path, questions
    """
    if not os.path.exists(banks_dir):
        os.makedirs(banks_dir, exist_ok=True)
        return []

    banks = []
    for entry in sorted(os.listdir(banks_dir)):
        entry_path = os.path.join(banks_dir, entry)
        if not os.path.isdir(entry_path):
            continue

        questions = _load_bank_questions(entry_path)
        if questions:
            banks.append({
                'name': entry,
                'path': entry_path,
                'questions': questions,
            })

    return banks


def _load_bank_questions(bank_path: str) -> List[Dict]:
    """加载单个题库文件夹的所有题目（过滤已删除的，去重）"""
    questions = []
    seen_texts = set()  # (question_text, type) 去重
    for filename in sorted(os.listdir(bank_path)):
        filepath = os.path.join(bank_path, filename)
        if not os.path.isfile(filepath):
            continue

        if filename.endswith('.md'):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                parsed = parse_markdown(content)
                for q in parsed:
                    key = (q['question'], q['type'])
                    if key in seen_texts:
                        continue
                    seen_texts.add(key)
                    q['source'] = filename
                    questions.append(q)
            except Exception as e:
                print(f"Warning: failed to parse {filename}: {e}")

        elif filename.endswith('.json'):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                loaded = []
                if isinstance(data, dict) and 'questions' in data:
                    loaded = data['questions']
                elif isinstance(data, list):
                    loaded = data
                for q in loaded:
                    if 'source' not in q:
                        q['source'] = filename
                    key = (q.get('question', ''), q.get('type', ''))
                    if key in seen_texts:
                        continue
                    seen_texts.add(key)
                    questions.append(q)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: failed to parse {filename}: {e}")

    # 过滤已删除的题目
    deleted_data = load_bank_deleted(bank_path)
    deleted_set = set()
    for q in deleted_data.get("deleted", []):
        deleted_set.add((q['id'], q['type']))

    questions = [q for q in questions if (q['id'], q['type']) not in deleted_set]

    return questions


WRONG_QUESTIONS_FILE = 'wrong_questions.json'
COLLECTIONS_FILE = 'collections.json'
QUIZ_PROGRESS_FILE = 'quiz_progress.json'


def load_bank_wrong_questions(bank_path: str) -> dict:
    """
    加载题库的错题本

    Args:
        bank_path: 题库文件夹路径

    Returns:
        {"wrong_books": {"错题本名": [...]}}
    """
    filepath = os.path.join(bank_path, WRONG_QUESTIONS_FILE)
    if not os.path.exists(filepath):
        return {"wrong_books": {}}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 兼容旧格式
        if 'wrong_questions' in data and 'wrong_books' not in data:
            return {"wrong_books": {"default": data['wrong_questions']}}
        return data
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: cannot read wrong questions: {e}")
        return {"wrong_books": {}}


def save_bank_wrong_question(bank_path: str, book_name: str, question: dict) -> None:
    """
    保存错题到指定错题本

    Args:
        bank_path: 题库文件夹路径
        book_name: 错题本名称
        question: 题目字典
    """
    data = load_bank_wrong_questions(bank_path)
    wrong_books = data.get("wrong_books", {})

    if book_name not in wrong_books:
        wrong_books[book_name] = []

    book = wrong_books[book_name]

    # 检查是否已存在
    existing_keys = [(q['id'], q['type']) for q in book]
    if (question['id'], question['type']) in existing_keys:
        for q in book:
            if q['id'] == question['id'] and q['type'] == question['type']:
                q['wrong_count'] = q.get('wrong_count', 1) + 1
                break
    else:
        from datetime import datetime
        entry = {
            'id': question['id'],
            'type': question['type'],
            'question': question['question'],
            'options': question['options'],
            'answer': question['answer'],
            'explanation': question.get('explanation', ''),
            'wrong_count': 1,
            'last_wrong': datetime.now().strftime('%Y-%m-%d')
        }
        book.append(entry)

    data['wrong_books'] = wrong_books
    filepath = os.path.join(bank_path, WRONG_QUESTIONS_FILE)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Warning: cannot save wrong questions: {e}")


def remove_bank_wrong_question(bank_path: str, question_id: int, question_type: str) -> None:
    """
    从题库的所有错题本中移除题目（答对时调用）

    Args:
        bank_path: 题库文件夹路径
        question_id: 题目 ID
        question_type: 题目类型 ('single' 或 'multi')
    """
    data = load_bank_wrong_questions(bank_path)
    wrong_books = data.get("wrong_books", {})
    changed = False

    for book_name in list(wrong_books.keys()):
        book = wrong_books[book_name]
        original_len = len(book)
        wrong_books[book_name] = [
            q for q in book
            if not (q['id'] == question_id and q['type'] == question_type)
        ]
        if len(wrong_books[book_name]) != original_len:
            changed = True

    if changed:
        data['wrong_books'] = wrong_books
        filepath = os.path.join(bank_path, WRONG_QUESTIONS_FILE)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Warning: cannot save wrong questions: {e}")


def load_bank_collections(bank_path: str) -> dict:
    """
    加载题库的收藏夹

    Args:
        bank_path: 题库文件夹路径

    Returns:
        {"collections": {"收藏夹名": [...]}}
    """
    filepath = os.path.join(bank_path, COLLECTIONS_FILE)
    if not os.path.exists(filepath):
        return {"collections": {}}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: cannot read collections: {e}")
        return {"collections": {}}


def save_bank_collection(bank_path: str, collection_name: str, question: dict) -> None:
    """
    保存题目到指定收藏夹

    Args:
        bank_path: 题库文件夹路径
        collection_name: 收藏夹名称
        question: 题目字典
    """
    data = load_bank_collections(bank_path)
    collections = data.get("collections", {})

    if collection_name not in collections:
        collections[collection_name] = []

    collection = collections[collection_name]

    # 检查是否已存在
    existing_keys = [(q['id'], q['type']) for q in collection]
    if (question['id'], question['type']) not in existing_keys:
        entry = {
            'id': question['id'],
            'type': question['type'],
            'question': question['question'],
            'options': question['options'],
            'answer': question['answer'],
            'explanation': question.get('explanation', ''),
        }
        collection.append(entry)

    data['collections'] = collections
    filepath = os.path.join(bank_path, COLLECTIONS_FILE)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Warning: cannot save collections: {e}")


def create_bank_collection(bank_path: str, name: str) -> bool:
    """
    创建新收藏夹（银行模式）

    Args:
        bank_path: 题库文件夹路径
        name: 收藏夹名称

    Returns:
        是否创建成功（已存在返回 False）
    """
    from datetime import datetime
    data = load_bank_collections(bank_path)
    collections = data.get("collections", {})

    if name in collections:
        return False

    collections[name] = {
        'created': datetime.now().strftime('%Y-%m-%d'),
        'questions': []
    }

    data['collections'] = collections
    filepath = os.path.join(bank_path, COLLECTIONS_FILE)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except IOError as e:
        print(f"Warning: cannot create collection: {e}")
        return False


def delete_bank_collection(bank_path: str, name: str) -> bool:
    """
    删除收藏夹（银行模式）

    Args:
        bank_path: 题库文件夹路径
        name: 收藏夹名称

    Returns:
        是否删除成功（不存在返回 False）
    """
    data = load_bank_collections(bank_path)
    collections = data.get("collections", {})

    if name not in collections:
        return False

    del collections[name]
    data['collections'] = collections

    filepath = os.path.join(bank_path, COLLECTIONS_FILE)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except IOError as e:
        print(f"Warning: cannot delete collection: {e}")
        return False


def rename_bank_collection(bank_path: str, old_name: str, new_name: str) -> bool:
    """
    重命名收藏夹（银行模式）

    Args:
        bank_path: 题库文件夹路径
        old_name: 旧名称
        new_name: 新名称

    Returns:
        是否重命名成功（old不存在或new已存在返回 False）
    """
    data = load_bank_collections(bank_path)
    collections = data.get("collections", {})

    if old_name not in collections:
        return False
    if new_name in collections:
        return False

    collections[new_name] = collections.pop(old_name)
    data['collections'] = collections

    filepath = os.path.join(bank_path, COLLECTIONS_FILE)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except IOError as e:
        print(f"Warning: cannot rename collection: {e}")
        return False


def add_to_bank_collection(bank_path: str, name: str, question_id: int, question_type: str) -> bool:
    """
    将题目加入收藏夹（银行模式）

    Args:
        bank_path: 题库文件夹路径
        name: 收藏夹名称
        question_id: 题目 ID
        question_type: 题目类型

    Returns:
        是否添加成功（已存在返回 False）
    """
    from datetime import datetime
    data = load_bank_collections(bank_path)
    collections = data.get("collections", {})

    if name not in collections:
        return False

    questions = collections[name].get('questions', [])
    for q in questions:
        if q['id'] == question_id and q['type'] == question_type:
            return False

    questions.append({
        'id': question_id,
        'type': question_type,
        'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    collections[name]['questions'] = questions
    data['collections'] = collections

    filepath = os.path.join(bank_path, COLLECTIONS_FILE)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except IOError as e:
        print(f"Warning: cannot add to collection: {e}")
        return False


def remove_from_bank_collection(bank_path: str, name: str, question_id: int, question_type: str) -> bool:
    """
    从收藏夹移除题目（银行模式）

    Args:
        bank_path: 题库文件夹路径
        name: 收藏夹名称
        question_id: 题目 ID
        question_type: 题目类型

    Returns:
        是否移除成功（不存在返回 False）
    """
    data = load_bank_collections(bank_path)
    collections = data.get("collections", {})

    if name not in collections:
        return False

    questions = collections[name].get('questions', [])
    for i, q in enumerate(questions):
        if q['id'] == question_id and q['type'] == question_type:
            questions.pop(i)
            collections[name]['questions'] = questions
            data['collections'] = collections

            filepath = os.path.join(bank_path, COLLECTIONS_FILE)
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return True
            except IOError as e:
                print(f"Warning: cannot remove from collection: {e}")
                return False

    return False


# --- Bank flagged questions ---

FLAGGED_FILE = 'flagged.json'


def load_bank_flagged(bank_path: str) -> dict:
    """
    加载题库的标记题目

    Args:
        bank_path: 题库文件夹路径

    Returns:
        {"flagged": [{"id": 1, "type": "single", "reason": "...", "flagged_at": "..."}]}
    """
    filepath = os.path.join(bank_path, FLAGGED_FILE)
    if not os.path.exists(filepath):
        return {"flagged": []}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: cannot read flagged questions: {e}")
        return {"flagged": []}


def save_bank_flagged(bank_path: str, data: dict) -> None:
    """
    保存标记题目数据

    Args:
        bank_path: 题库文件夹路径
        data: 标记数据
    """
    filepath = os.path.join(bank_path, FLAGGED_FILE)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Warning: cannot save flagged questions: {e}")


def add_to_bank_flagged(bank_path: str, question_id: int, question_type: str, reason: str = '') -> bool:
    """
    标记题目

    Args:
        bank_path: 题库文件夹路径
        question_id: 题目 ID
        question_type: 题目类型
        reason: 标记原因

    Returns:
        是否标记成功（已存在返回 False）
    """
    from datetime import datetime
    data = load_bank_flagged(bank_path)
    flagged = data.get("flagged", [])

    # 检查是否已标记
    for q in flagged:
        if q['id'] == question_id and q['type'] == question_type:
            return False

    flagged.append({
        'id': question_id,
        'type': question_type,
        'reason': reason,
        'flagged_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

    data['flagged'] = flagged
    save_bank_flagged(bank_path, data)
    return True


def remove_from_bank_flagged(bank_path: str, question_id: int, question_type: str) -> bool:
    """
    取消标记题目

    Args:
        bank_path: 题库文件夹路径
        question_id: 题目 ID
        question_type: 题目类型

    Returns:
        是否取消成功（不存在返回 False）
    """
    data = load_bank_flagged(bank_path)
    flagged = data.get("flagged", [])

    for i, q in enumerate(flagged):
        if q['id'] == question_id and q['type'] == question_type:
            flagged.pop(i)
            data['flagged'] = flagged
            save_bank_flagged(bank_path, data)
            return True

    return False


def is_bank_flagged(bank_path: str, question_id: int, question_type: str) -> bool:
    """
    检查题目是否被标记

    Args:
        bank_path: 题库文件夹路径
        question_id: 题目 ID
        question_type: 题目类型

    Returns:
        是否被标记
    """
    data = load_bank_flagged(bank_path)
    flagged = data.get("flagged", [])

    for q in flagged:
        if q['id'] == question_id and q['type'] == question_type:
            return True

    return False


# --- Bank deleted questions ---

DELETED_FILE = 'deleted.json'


def load_bank_deleted(bank_path: str) -> dict:
    """
    加载题库的删除记录

    Args:
        bank_path: 题库文件夹路径

    Returns:
        {"deleted": [{"id": 1, "type": "single", "deleted_at": "..."}]}
    """
    filepath = os.path.join(bank_path, DELETED_FILE)
    if not os.path.exists(filepath):
        return {"deleted": []}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: cannot read deleted questions: {e}")
        return {"deleted": []}


def save_bank_deleted(bank_path: str, data: dict) -> None:
    """
    保存删除记录

    Args:
        bank_path: 题库文件夹路径
        data: 删除记录数据
    """
    filepath = os.path.join(bank_path, DELETED_FILE)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Warning: cannot save deleted questions: {e}")


def add_to_bank_deleted(bank_path: str, question_id: int, question_type: str) -> bool:
    """
    标记题目为已删除

    Args:
        bank_path: 题库文件夹路径
        question_id: 题目 ID
        question_type: 题目类型

    Returns:
        是否标记成功（已存在返回 False）
    """
    from datetime import datetime
    data = load_bank_deleted(bank_path)
    deleted = data.get("deleted", [])

    # 检查是否已删除
    for q in deleted:
        if q['id'] == question_id and q['type'] == question_type:
            return False

    deleted.append({
        'id': question_id,
        'type': question_type,
        'deleted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

    data['deleted'] = deleted
    save_bank_deleted(bank_path, data)
    return True


def is_bank_deleted(bank_path: str, question_id: int, question_type: str) -> bool:
    """
    检查题目是否被删除

    Args:
        bank_path: 题库文件夹路径
        question_id: 题目 ID
        question_type: 题目类型

    Returns:
        是否被删除
    """
    data = load_bank_deleted(bank_path)
    deleted = data.get("deleted", [])

    for q in deleted:
        if q['id'] == question_id and q['type'] == question_type:
            return True

    return False


def restore_bank_deleted(bank_path: str, question_id: int, question_type: str) -> bool:
    """
    恢复已删除的题目

    Args:
        bank_path: 题库文件夹路径
        question_id: 题目 ID
        question_type: 题目类型

    Returns:
        是否恢复成功（不存在返回 False）
    """
    data = load_bank_deleted(bank_path)
    deleted = data.get("deleted", [])

    for i, q in enumerate(deleted):
        if q['id'] == question_id and q['type'] == question_type:
            deleted.pop(i)
            data['deleted'] = deleted
            save_bank_deleted(bank_path, data)
            return True

    return False


# --- Quiz progress ---

def save_quiz_progress(bank_path: str, progress: dict) -> bool:
    """
    保存刷题进度到题库文件夹

    Args:
        bank_path: 题库文件夹路径
        progress: 进度数据字典

    Returns:
        是否保存成功
    """
    filepath = os.path.join(bank_path, QUIZ_PROGRESS_FILE)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
        return True
    except IOError as e:
        print(f"Warning: cannot save quiz progress: {e}")
        return False


def load_quiz_progress(bank_path: str) -> Optional[dict]:
    """
    加载刷题进度

    Args:
        bank_path: 题库文件夹路径

    Returns:
        进度数据字典，无进度返回 None
    """
    filepath = os.path.join(bank_path, QUIZ_PROGRESS_FILE)
    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 验证必要字段
        required_fields = ['bank_name', 'mode', 'question_type', 'total_questions', 'current_idx', 'correct_count']
        if not all(field in data for field in required_fields):
            return None
        return data
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: cannot read quiz progress: {e}")
        return None


def delete_quiz_progress(bank_path: str) -> bool:
    """
    删除进度文件

    Args:
        bank_path: 题库文件夹路径

    Returns:
        是否删除成功（文件不存在也返回 True）
    """
    filepath = os.path.join(bank_path, QUIZ_PROGRESS_FILE)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
        return True
    except IOError as e:
        print(f"Warning: cannot delete quiz progress: {e}")
        return False
