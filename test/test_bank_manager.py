#!/usr/bin/env python3
"""Tests for bank_manager.py - folder scanning logic"""

import os
import sys
import tempfile
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bank_manager import (
    scan_banks_folder,
    load_bank_wrong_questions,
    load_bank_collections,
    save_bank_wrong_question,
    save_bank_collection,
    remove_bank_wrong_question,
    create_bank_collection,
    delete_bank_collection,
    rename_bank_collection,
    add_to_bank_collection,
    remove_from_bank_collection,
    get_collection_names,
    load_bank_flagged,
    add_to_bank_flagged,
    remove_from_bank_flagged,
    is_bank_flagged,
    load_bank_deleted,
    add_to_bank_deleted,
    is_bank_deleted,
    restore_bank_deleted,
    save_quiz_progress,
    load_quiz_progress,
    delete_quiz_progress,
)


def test_scan_banks_folder_returns_list():
    """扫描空 banks 文件夹返回空列表"""
    with tempfile.TemporaryDirectory() as tmpdir:
        banks_dir = os.path.join(tmpdir, 'banks')
        os.makedirs(banks_dir)
        result = scan_banks_folder(banks_dir)
        assert result == []


def test_scan_banks_folder_with_md_file():
    """扫描包含 .md 文件的子文件夹"""
    with tempfile.TemporaryDirectory() as tmpdir:
        banks_dir = os.path.join(tmpdir, 'banks')
        bank_dir = os.path.join(banks_dir, '测试题库')
        os.makedirs(bank_dir)

        # 创建一个简单的 .md 文件
        md_content = """## 单选题

**1. 测试题目（　）**

A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：A**

**解析：** 测试解析

---
"""
        with open(os.path.join(bank_dir, '测试.md'), 'w', encoding='utf-8') as f:
            f.write(md_content)

        result = scan_banks_folder(banks_dir)
        assert len(result) == 1
        assert result[0]['name'] == '测试题库'
        assert len(result[0]['questions']) == 1
        assert result[0]['questions'][0]['question'] == '测试题目（　）'


def test_scan_banks_folder_ignores_non_md_json():
    """忽略非 .md/.json 文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        banks_dir = os.path.join(tmpdir, 'banks')
        bank_dir = os.path.join(banks_dir, '测试题库')
        os.makedirs(bank_dir)

        # 创建一个 .txt 文件
        with open(os.path.join(bank_dir, 'readme.txt'), 'w') as f:
            f.write('这不是题库文件')

        result = scan_banks_folder(banks_dir)
        assert result == []


def test_scan_banks_folder_ignores_empty_folder():
    """忽略空文件夹"""
    with tempfile.TemporaryDirectory() as tmpdir:
        banks_dir = os.path.join(tmpdir, 'banks')
        os.makedirs(os.path.join(banks_dir, '空文件夹'))

        result = scan_banks_folder(banks_dir)
        assert result == []


def test_scan_banks_folder_with_json_file():
    """扫描包含 .json 文件的子文件夹"""
    with tempfile.TemporaryDirectory() as tmpdir:
        banks_dir = os.path.join(tmpdir, 'banks')
        bank_dir = os.path.join(banks_dir, 'JSON题库')
        os.makedirs(bank_dir)

        # 创建一个 .json 文件（dict 格式）
        json_data = {
            'questions': [
                {
                    'id': 1,
                    'type': 'single',
                    'question': 'JSON测试题目',
                    'options': ['A. 选项A', 'B. 选项B'],
                    'answer': 'A',
                    'explanation': '测试解析'
                }
            ]
        }
        with open(os.path.join(bank_dir, 'test.json'), 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False)

        result = scan_banks_folder(banks_dir)
        assert len(result) == 1
        assert result[0]['name'] == 'JSON题库'
        assert len(result[0]['questions']) == 1
        assert result[0]['questions'][0]['question'] == 'JSON测试题目'


def test_scan_banks_folder_with_json_list():
    """扫描 .json 文件为列表格式"""
    with tempfile.TemporaryDirectory() as tmpdir:
        banks_dir = os.path.join(tmpdir, 'banks')
        bank_dir = os.path.join(banks_dir, '列表题库')
        os.makedirs(bank_dir)

        # 创建一个 .json 文件（list 格式）
        json_data = [
            {
                'id': 1,
                'type': 'single',
                'question': '列表测试题目',
                'options': ['A. 选项A', 'B. 选项B'],
                'answer': 'A',
                'explanation': ''
            }
        ]
        with open(os.path.join(bank_dir, 'test.json'), 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False)

        result = scan_banks_folder(banks_dir)
        assert len(result) == 1
        assert len(result[0]['questions']) == 1
        assert result[0]['questions'][0]['question'] == '列表测试题目'


def test_scan_banks_folder_creates_dir_if_missing():
    """如果 banks 目录不存在，自动创建"""
    with tempfile.TemporaryDirectory() as tmpdir:
        banks_dir = os.path.join(tmpdir, 'nonexistent', 'banks')
        result = scan_banks_folder(banks_dir)
        assert result == []
        assert os.path.exists(banks_dir)


def test_scan_banks_folder_merges_multiple_files():
    """多个文件合并成一个题库"""
    with tempfile.TemporaryDirectory() as tmpdir:
        banks_dir = os.path.join(tmpdir, 'banks')
        bank_dir = os.path.join(banks_dir, '合并题库')
        os.makedirs(bank_dir)

        # 创建两个 .md 文件
        md1 = """## 单选题

**1. 第一题（　）**

A. A选项
B. B选项
C. C选项
D. D选项

**答案：A**

**解析：** 解析1

---
"""
        md2 = """## 单选题

**2. 第二题（　）**

A. A选项
B. B选项
C. C选项
D. D选项

**答案：B**

**解析：** 解析2

---
"""
        with open(os.path.join(bank_dir, '第一章.md'), 'w', encoding='utf-8') as f:
            f.write(md1)
        with open(os.path.join(bank_dir, '第二章.md'), 'w', encoding='utf-8') as f:
            f.write(md2)

        result = scan_banks_folder(banks_dir)
        assert len(result) == 1
        assert len(result[0]['questions']) == 2


def test_scan_banks_folder_skips_invalid_json():
    """跳过格式错误的 JSON 文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        banks_dir = os.path.join(tmpdir, 'banks')
        bank_dir = os.path.join(banks_dir, '错误题库')
        os.makedirs(bank_dir)

        with open(os.path.join(bank_dir, 'bad.json'), 'w') as f:
            f.write('这不是JSON')

        result = scan_banks_folder(banks_dir)
        assert result == []


def test_scan_banks_folder_returns_path_key():
    """返回的题库包含 path 字段"""
    with tempfile.TemporaryDirectory() as tmpdir:
        banks_dir = os.path.join(tmpdir, 'banks')
        bank_dir = os.path.join(banks_dir, '测试')
        os.makedirs(bank_dir)

        md_content = """## 单选题

**1. 测试（　）**

A. A选项
B. B选项
C. C选项
D. D选项

**答案：A**

**解析：** 解析

---
"""
        with open(os.path.join(bank_dir, 'test.md'), 'w', encoding='utf-8') as f:
            f.write(md_content)

        result = scan_banks_folder(banks_dir)
        assert result[0]['path'] == bank_dir


def test_scan_banks_folder_multiple_banks():
    """扫描多个题库文件夹"""
    with tempfile.TemporaryDirectory() as tmpdir:
        banks_dir = os.path.join(tmpdir, 'banks')

        for name in ['题库A', '题库B']:
            bank_dir = os.path.join(banks_dir, name)
            os.makedirs(bank_dir)
            md_content = """## 单选题

**1. 测试（　）**

A. A选项
B. B选项
C. C选项
D. D选项

**答案：A**

**解析：** 解析

---
"""
            with open(os.path.join(bank_dir, 'test.md'), 'w', encoding='utf-8') as f:
                f.write(md_content)

        result = scan_banks_folder(banks_dir)
        assert len(result) == 2
        names = [b['name'] for b in result]
        assert '题库A' in names
        assert '题库B' in names


# --- per-bank data loading tests ---

def test_load_bank_wrong_questions_empty():
    """加载不存在的错题本返回空结构"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = load_bank_wrong_questions(tmpdir)
        assert result == {"wrong_books": {}}


def test_load_bank_wrong_questions_with_data():
    """加载存在的错题本"""
    with tempfile.TemporaryDirectory() as tmpdir:
        data = {
            "wrong_books": {
                "测试错题": [
                    {"id": 1, "type": "single", "question": "测试", "wrong_count": 1}
                ]
            }
        }
        with open(os.path.join(tmpdir, 'wrong_questions.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

        result = load_bank_wrong_questions(tmpdir)
        assert "测试错题" in result["wrong_books"]
        assert len(result["wrong_books"]["测试错题"]) == 1


def test_save_bank_wrong_question():
    """保存错题到指定错题本"""
    with tempfile.TemporaryDirectory() as tmpdir:
        question = {
            "id": 1,
            "type": "single",
            "question": "测试题目",
            "options": {"A": "选项A", "B": "选项B"},
            "answer": "A",
            "explanation": "解析"
        }
        save_bank_wrong_question(tmpdir, "测试错题", question)

        # 验证保存成功
        result = load_bank_wrong_questions(tmpdir)
        assert "测试错题" in result["wrong_books"]
        assert len(result["wrong_books"]["测试错题"]) == 1
        assert result["wrong_books"]["测试错题"][0]["wrong_count"] == 1


def test_save_bank_wrong_question_increments_count():
    """重复保存同一题目增加 wrong_count"""
    with tempfile.TemporaryDirectory() as tmpdir:
        question = {
            "id": 1,
            "type": "single",
            "question": "测试题目",
            "options": {"A": "选项A", "B": "选项B"},
            "answer": "A",
            "explanation": "解析"
        }
        save_bank_wrong_question(tmpdir, "测试错题", question)
        save_bank_wrong_question(tmpdir, "测试错题", question)

        result = load_bank_wrong_questions(tmpdir)
        assert result["wrong_books"]["测试错题"][0]["wrong_count"] == 2


def test_load_bank_collections_empty():
    """加载不存在的收藏夹返回空结构"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = load_bank_collections(tmpdir)
        assert result == {"collections": {}}


def test_save_bank_collection():
    """保存题目到指定收藏夹"""
    with tempfile.TemporaryDirectory() as tmpdir:
        question = {
            "id": 1,
            "type": "single",
            "question": "收藏题目",
            "options": {"A": "选项A", "B": "选项B"},
            "answer": "A",
            "explanation": "解析"
        }
        save_bank_collection(tmpdir, "测试收藏", question)

        result = load_bank_collections(tmpdir)
        assert "测试收藏" in result["collections"]
        val = result["collections"]["测试收藏"]
        assert isinstance(val, dict)
        assert "created" in val
        assert "questions" in val
        assert len(val["questions"]) == 1
        assert val["questions"][0]["id"] == 1
        assert val["questions"][0]["type"] == "single"


# --- remove_bank_wrong_question tests ---

def test_remove_bank_wrong_question():
    """答对时从错题本中移除题目"""
    with tempfile.TemporaryDirectory() as tmpdir:
        question = {
            "id": 1,
            "type": "single",
            "question": "测试题目",
            "options": {"A": "选项A", "B": "选项B"},
            "answer": "A",
            "explanation": "解析"
        }
        save_bank_wrong_question(tmpdir, "错题本1", question)
        save_bank_wrong_question(tmpdir, "错题本2", question)

        # 确认两个错题本都有该题
        data = load_bank_wrong_questions(tmpdir)
        assert len(data["wrong_books"]["错题本1"]) == 1
        assert len(data["wrong_books"]["错题本2"]) == 1

        # 移除
        remove_bank_wrong_question(tmpdir, 1, "single")

        # 确认两个错题本都已移除
        data = load_bank_wrong_questions(tmpdir)
        assert len(data["wrong_books"]["错题本1"]) == 0
        assert len(data["wrong_books"]["错题本2"]) == 0


def test_remove_bank_wrong_question_only_target():
    """只移除匹配的题目，不影响其他题目"""
    with tempfile.TemporaryDirectory() as tmpdir:
        q1 = {"id": 1, "type": "single", "question": "题目1", "options": {}, "answer": "A", "explanation": ""}
        q2 = {"id": 2, "type": "single", "question": "题目2", "options": {}, "answer": "B", "explanation": ""}
        save_bank_wrong_question(tmpdir, "默认错题", q1)
        save_bank_wrong_question(tmpdir, "默认错题", q2)

        remove_bank_wrong_question(tmpdir, 1, "single")

        data = load_bank_wrong_questions(tmpdir)
        assert len(data["wrong_books"]["默认错题"]) == 1
        assert data["wrong_books"]["默认错题"][0]["id"] == 2


def test_remove_bank_wrong_question_no_file():
    """错题本文件不存在时静默处理"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 不应抛出异常
        remove_bank_wrong_question(tmpdir, 999, "single")


def test_remove_bank_wrong_question_id_type_composite():
    """单选和多选同 ID 不互相影响"""
    with tempfile.TemporaryDirectory() as tmpdir:
        q_single = {"id": 1, "type": "single", "question": "单选", "options": {}, "answer": "A", "explanation": ""}
        q_multi = {"id": 1, "type": "multi", "question": "多选", "options": {}, "answer": "AB", "explanation": ""}
        save_bank_wrong_question(tmpdir, "默认错题", q_single)
        save_bank_wrong_question(tmpdir, "默认错题", q_multi)

        remove_bank_wrong_question(tmpdir, 1, "single")

        data = load_bank_wrong_questions(tmpdir)
        assert len(data["wrong_books"]["默认错题"]) == 1
        assert data["wrong_books"]["默认错题"][0]["type"] == "multi"


# --- bank collection CRUD tests ---

def test_create_bank_collection():
    """创建新收藏夹"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = create_bank_collection(tmpdir, "测试收藏")
        assert result is True

        data = load_bank_collections(tmpdir)
        assert "测试收藏" in data["collections"]
        assert data["collections"]["测试收藏"]["questions"] == []


def test_create_bank_collection_already_exists():
    """创建已存在的收藏夹返回 False"""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_bank_collection(tmpdir, "测试收藏")
        result = create_bank_collection(tmpdir, "测试收藏")
        assert result is False


def test_delete_bank_collection():
    """删除收藏夹"""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_bank_collection(tmpdir, "测试收藏")
        result = delete_bank_collection(tmpdir, "测试收藏")
        assert result is True

        data = load_bank_collections(tmpdir)
        assert "测试收藏" not in data["collections"]


def test_delete_bank_collection_not_exists():
    """删除不存在的收藏夹返回 False"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = delete_bank_collection(tmpdir, "不存在")
        assert result is False


def test_rename_bank_collection():
    """重命名收藏夹"""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_bank_collection(tmpdir, "旧名称")
        result = rename_bank_collection(tmpdir, "旧名称", "新名称")
        assert result is True

        data = load_bank_collections(tmpdir)
        assert "旧名称" not in data["collections"]
        assert "新名称" in data["collections"]


def test_rename_bank_collection_not_exists():
    """重命名不存在的收藏夹返回 False"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = rename_bank_collection(tmpdir, "不存在", "新名称")
        assert result is False


def test_rename_bank_collection_new_name_exists():
    """重命名到已存在的名称返回 False"""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_bank_collection(tmpdir, "收藏1")
        create_bank_collection(tmpdir, "收藏2")
        result = rename_bank_collection(tmpdir, "收藏1", "收藏2")
        assert result is False


def test_add_to_bank_collection():
    """添加题目到收藏夹"""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_bank_collection(tmpdir, "测试收藏")
        result = add_to_bank_collection(tmpdir, "测试收藏", 1, "single")
        assert result is True

        data = load_bank_collections(tmpdir)
        questions = data["collections"]["测试收藏"]["questions"]
        assert len(questions) == 1
        assert questions[0]["id"] == 1
        assert questions[0]["type"] == "single"


def test_add_to_bank_collection_already_exists():
    """添加已存在的题目返回 False"""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_bank_collection(tmpdir, "测试收藏")
        add_to_bank_collection(tmpdir, "测试收藏", 1, "single")
        result = add_to_bank_collection(tmpdir, "测试收藏", 1, "single")
        assert result is False


def test_add_to_bank_collection_not_exists():
    """添加到不存在的收藏夹返回 False"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = add_to_bank_collection(tmpdir, "不存在", 1, "single")
        assert result is False


def test_remove_from_bank_collection():
    """从收藏夹移除题目"""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_bank_collection(tmpdir, "测试收藏")
        add_to_bank_collection(tmpdir, "测试收藏", 1, "single")
        result = remove_from_bank_collection(tmpdir, "测试收藏", 1, "single")
        assert result is True

        data = load_bank_collections(tmpdir)
        questions = data["collections"]["测试收藏"]["questions"]
        assert len(questions) == 0


def test_remove_from_bank_collection_not_in_collection():
    """移除不存在的题目返回 False"""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_bank_collection(tmpdir, "测试收藏")
        result = remove_from_bank_collection(tmpdir, "测试收藏", 1, "single")
        assert result is False


def test_remove_from_bank_collection_not_exists():
    """从不存在的收藏夹移除返回 False"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = remove_from_bank_collection(tmpdir, "不存在", 1, "single")
        assert result is False


# --- bank flagged questions tests ---

def test_load_bank_flagged_empty():
    """加载不存在的标记文件返回空结构"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = load_bank_flagged(tmpdir)
        assert result == {"flagged": []}


def test_add_to_bank_flagged():
    """标记题目"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = add_to_bank_flagged(tmpdir, 1, "single", "不确定")
        assert result is True

        data = load_bank_flagged(tmpdir)
        assert len(data["flagged"]) == 1
        assert data["flagged"][0]["id"] == 1
        assert data["flagged"][0]["type"] == "single"
        assert data["flagged"][0]["reason"] == "不确定"


def test_add_to_bank_flagged_already_exists():
    """标记已存在的题目返回 False"""
    with tempfile.TemporaryDirectory() as tmpdir:
        add_to_bank_flagged(tmpdir, 1, "single", "不确定")
        result = add_to_bank_flagged(tmpdir, 1, "single", "其他原因")
        assert result is False


def test_remove_from_bank_flagged():
    """取消标记题目"""
    with tempfile.TemporaryDirectory() as tmpdir:
        add_to_bank_flagged(tmpdir, 1, "single", "不确定")
        result = remove_from_bank_flagged(tmpdir, 1, "single")
        assert result is True

        data = load_bank_flagged(tmpdir)
        assert len(data["flagged"]) == 0


def test_remove_from_bank_flagged_not_exists():
    """取消不存在的标记返回 False"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = remove_from_bank_flagged(tmpdir, 1, "single")
        assert result is False


def test_is_bank_flagged():
    """检查题目是否被标记"""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert is_bank_flagged(tmpdir, 1, "single") is False

        add_to_bank_flagged(tmpdir, 1, "single", "不确定")
        assert is_bank_flagged(tmpdir, 1, "single") is True


def test_is_bank_flagged_id_type_composite():
    """单选和多选同 ID 不互相影响"""
    with tempfile.TemporaryDirectory() as tmpdir:
        add_to_bank_flagged(tmpdir, 1, "single", "不确定")

        assert is_bank_flagged(tmpdir, 1, "single") is True
        assert is_bank_flagged(tmpdir, 1, "multi") is False


# --- bank deleted questions tests ---

def test_load_bank_deleted_empty():
    """加载不存在的删除记录返回空结构"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = load_bank_deleted(tmpdir)
        assert result == {"deleted": []}


def test_add_to_bank_deleted():
    """标记题目为已删除"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = add_to_bank_deleted(tmpdir, 1, "single")
        assert result is True

        data = load_bank_deleted(tmpdir)
        assert len(data["deleted"]) == 1
        assert data["deleted"][0]["id"] == 1
        assert data["deleted"][0]["type"] == "single"


def test_add_to_bank_deleted_already_exists():
    """标记已删除的题目返回 False"""
    with tempfile.TemporaryDirectory() as tmpdir:
        add_to_bank_deleted(tmpdir, 1, "single")
        result = add_to_bank_deleted(tmpdir, 1, "single")
        assert result is False


def test_is_bank_deleted():
    """检查题目是否被删除"""
    with tempfile.TemporaryDirectory() as tmpdir:
        assert is_bank_deleted(tmpdir, 1, "single") is False

        add_to_bank_deleted(tmpdir, 1, "single")
        assert is_bank_deleted(tmpdir, 1, "single") is True


def test_restore_bank_deleted():
    """恢复已删除的题目"""
    with tempfile.TemporaryDirectory() as tmpdir:
        add_to_bank_deleted(tmpdir, 1, "single")
        result = restore_bank_deleted(tmpdir, 1, "single")
        assert result is True

        assert is_bank_deleted(tmpdir, 1, "single") is False


def test_restore_bank_deleted_not_exists():
    """恢复不存在的删除记录返回 False"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = restore_bank_deleted(tmpdir, 1, "single")
        assert result is False


def test_load_bank_questions_filters_deleted():
    """加载题库时过滤已删除的题目"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建 banks/子文件夹 结构
        banks_dir = os.path.join(tmpdir, 'banks')
        bank_dir = os.path.join(banks_dir, '测试题库')
        os.makedirs(bank_dir)

        # 创建一个 .md 文件，包含两道题
        md_content = """## 单选题

**1. 第一题（　）**

A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：A**

**解析：** 解析1

---

**2. 第二题（　）**

A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：B**

**解析：** 解析2

---
"""
        with open(os.path.join(bank_dir, '测试.md'), 'w', encoding='utf-8') as f:
            f.write(md_content)

        # 加载题库，应该有 2 道题
        banks = scan_banks_folder(banks_dir)
        assert len(banks) == 1
        assert len(banks[0]['questions']) == 2

        # 标记第一题为已删除
        add_to_bank_deleted(bank_dir, 1, "single")

        # 重新加载，应该有 1 道题
        banks = scan_banks_folder(banks_dir)
        assert len(banks) == 1
        assert len(banks[0]['questions']) == 1
        assert banks[0]['questions'][0]['id'] == 2


def test_load_bank_questions_has_source_field():
    """加载题库后每道题应有 source 字段"""
    with tempfile.TemporaryDirectory() as tmpdir:
        bank_dir = os.path.join(tmpdir, '测试题库')
        os.makedirs(bank_dir)

        md_content = """## 单选题

**1. 测试题目（　）**

A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：A**

**解析：** 测试解析
"""
        with open(os.path.join(bank_dir, '第一章.md'), 'w', encoding='utf-8') as f:
            f.write(md_content)

        result = scan_banks_folder(tmpdir)
        assert len(result) == 1
        questions = result[0]['questions']
        assert len(questions) == 1
        assert questions[0]['source'] == '第一章.md'


def test_load_bank_questions_multiple_files_source():
    """多个文件的题目来源各自不同"""
    with tempfile.TemporaryDirectory() as tmpdir:
        bank_dir = os.path.join(tmpdir, '测试题库')
        os.makedirs(bank_dir)

        md1 = """## 单选题

**1. 第一章题目（　）**

A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：A**

**解析：** 解析
"""
        md2 = """## 单选题

**1. 第二章题目（　）**

A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：B**

**解析：** 解析
"""
        with open(os.path.join(bank_dir, '第一章.md'), 'w', encoding='utf-8') as f:
            f.write(md1)
        with open(os.path.join(bank_dir, '第二章.md'), 'w', encoding='utf-8') as f:
            f.write(md2)

        result = scan_banks_folder(tmpdir)
        questions = result[0]['questions']
        sources = {q['question']: q['source'] for q in questions}
        assert sources['第一章题目（　）'] == '第一章.md'
        assert sources['第二章题目（　）'] == '第二章.md'


def test_load_bank_json_preserves_existing_source():
    """JSON 文件中已有 source 字段时保留原值不被覆盖"""
    with tempfile.TemporaryDirectory() as tmpdir:
        bank_dir = os.path.join(tmpdir, 'JSON题库')
        os.makedirs(bank_dir)

        json_data = [
            {
                'id': 1,
                'type': 'single',
                'question': '带来源的题目',
                'options': ['A. 选项A', 'B. 选项B'],
                'answer': 'A',
                'explanation': '解析',
                'source': '原始来源.json'
            }
        ]
        with open(os.path.join(bank_dir, 'test.json'), 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False)

        result = scan_banks_folder(tmpdir)
        assert len(result) == 1
        questions = result[0]['questions']
        assert len(questions) == 1
        # source 应保留 JSON 中的原始值，而非被覆盖为文件名
        assert questions[0]['source'] == '原始来源.json'


# --- quiz progress tests ---

def _sample_progress(**overrides):
    """创建一个示例进度字典，可覆盖任意字段"""
    progress = {
        'bank_name': '测试题库',
        'mode': 'sequential',
        'question_type': 'single',
        'total_questions': 10,
        'current_idx': 3,
        'correct_count': 2,
        'wrong_ids': [1],
        'answered_ids': [1, 2, 3],
        'order': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    }
    progress.update(overrides)
    return progress


def test_save_quiz_progress():
    """保存进度到题库文件夹"""
    with tempfile.TemporaryDirectory() as tmpdir:
        progress = _sample_progress()
        result = save_quiz_progress(tmpdir, progress)
        assert result is True

        filepath = os.path.join(tmpdir, 'quiz_progress.json')
        assert os.path.exists(filepath)

        with open(filepath, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        assert saved['bank_name'] == '测试题库'
        assert saved['current_idx'] == 3


def test_save_quiz_progress_overwrites_existing():
    """重复保存覆盖旧进度"""
    with tempfile.TemporaryDirectory() as tmpdir:
        save_quiz_progress(tmpdir, _sample_progress(current_idx=3))
        save_quiz_progress(tmpdir, _sample_progress(current_idx=7))

        result = load_quiz_progress(tmpdir)
        assert result['current_idx'] == 7


def test_save_quiz_progress_preserves_unicode():
    """保存包含中文的内容时 ensure_ascii=False 生效"""
    with tempfile.TemporaryDirectory() as tmpdir:
        progress = _sample_progress(bank_name='毛概题库')
        save_quiz_progress(tmpdir, progress)

        filepath = os.path.join(tmpdir, 'quiz_progress.json')
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        assert '毛概题库' in content
        assert '\\u' not in content


def test_load_quiz_progress_returns_data():
    """加载存在的进度文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        progress = _sample_progress()
        save_quiz_progress(tmpdir, progress)

        result = load_quiz_progress(tmpdir)
        assert result is not None
        assert result['bank_name'] == '测试题库'
        assert result['mode'] == 'sequential'
        assert result['current_idx'] == 3
        assert result['correct_count'] == 2


def test_load_quiz_progress_no_file():
    """无进度文件返回 None"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = load_quiz_progress(tmpdir)
        assert result is None


def test_load_quiz_progress_invalid_json():
    """JSON 格式错误返回 None"""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'quiz_progress.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('{bad json}')

        result = load_quiz_progress(tmpdir)
        assert result is None


def test_load_quiz_progress_missing_required_fields():
    """缺少必要字段返回 None"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 缺少 current_idx
        incomplete = {
            'bank_name': '测试题库',
            'mode': 'sequential',
            'question_type': 'single',
            'total_questions': 10,
            'correct_count': 2,
        }
        filepath = os.path.join(tmpdir, 'quiz_progress.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(incomplete, f, ensure_ascii=False)

        result = load_quiz_progress(tmpdir)
        assert result is None


def test_load_quiz_progress_all_required_fields_present():
    """所有必要字段齐全时正常返回"""
    with tempfile.TemporaryDirectory() as tmpdir:
        progress = _sample_progress()
        save_quiz_progress(tmpdir, progress)

        result = load_quiz_progress(tmpdir)
        assert result is not None
        required = ['bank_name', 'mode', 'question_type', 'total_questions', 'current_idx', 'correct_count']
        for field in required:
            assert field in result


def test_load_quiz_progress_extra_fields_preserved():
    """额外字段（如 wrong_ids）也被保留"""
    with tempfile.TemporaryDirectory() as tmpdir:
        progress = _sample_progress(wrong_ids=[1, 5], answered_ids=[1, 2, 3])
        save_quiz_progress(tmpdir, progress)

        result = load_quiz_progress(tmpdir)
        assert result['wrong_ids'] == [1, 5]
        assert result['answered_ids'] == [1, 2, 3]


def test_delete_quiz_progress():
    """删除进度文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        save_quiz_progress(tmpdir, _sample_progress())
        filepath = os.path.join(tmpdir, 'quiz_progress.json')
        assert os.path.exists(filepath)

        result = delete_quiz_progress(tmpdir)
        assert result is True
        assert not os.path.exists(filepath)


def test_delete_quiz_progress_no_file():
    """删除不存在的进度文件也返回 True"""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = delete_quiz_progress(tmpdir)
        assert result is True


def test_load_quiz_progress_after_delete():
    """删除后加载返回 None"""
    with tempfile.TemporaryDirectory() as tmpdir:
        save_quiz_progress(tmpdir, _sample_progress())
        delete_quiz_progress(tmpdir)

        result = load_quiz_progress(tmpdir)
        assert result is None


def test_save_load_delete_roundtrip():
    """完整的保存-加载-删除流程"""
    with tempfile.TemporaryDirectory() as tmpdir:
        progress = _sample_progress(
            bank_name='毛概第一章',
            mode='random',
            question_type='multi',
            total_questions=20,
            current_idx=15,
            correct_count=12,
        )

        # 保存
        assert save_quiz_progress(tmpdir, progress) is True

        # 加载
        loaded = load_quiz_progress(tmpdir)
        assert loaded is not None
        assert loaded['bank_name'] == '毛概第一章'
        assert loaded['mode'] == 'random'
        assert loaded['question_type'] == 'multi'
        assert loaded['total_questions'] == 20
        assert loaded['current_idx'] == 15
        assert loaded['correct_count'] == 12

        # 删除
        assert delete_quiz_progress(tmpdir) is True
        assert load_quiz_progress(tmpdir) is None


# --- collection format migration tests ---

def test_save_bank_collection_dict_format():
    """save_bank_collection 创建 dict 格式，含 created/questions 键"""
    with tempfile.TemporaryDirectory() as tmpdir:
        question = {
            "id": 1, "type": "single", "question": "题1",
            "options": {"A": "A", "B": "B"}, "answer": "A", "explanation": ""
        }
        save_bank_collection(tmpdir, "测试", question)
        data = load_bank_collections(tmpdir)
        val = data["collections"]["测试"]
        assert isinstance(val, dict)
        assert "created" in val
        assert "questions" in val
        assert len(val["questions"]) == 1
        assert val["questions"][0]["id"] == 1


def test_save_bank_collection_migrates_old_list():
    """save_bank_collection 自动迁移旧 list 格式到 dict 格式"""
    with tempfile.TemporaryDirectory() as tmpdir:
        raw = {"collections": {"old": [{"id": 1, "type": "single", "question": "x", "options": {}, "answer": "A", "explanation": ""}]}}
        with open(os.path.join(tmpdir, 'collections.json'), 'w', encoding='utf-8') as f:
            json.dump(raw, f, ensure_ascii=False)
        save_bank_collection(tmpdir, "old", {"id": 2, "type": "multi", "question": "y", "options": {}, "answer": "AB", "explanation": ""})
        data = load_bank_collections(tmpdir)
        val = data["collections"]["old"]
        assert isinstance(val, dict)
        assert len(val["questions"]) == 2
        assert val["questions"][0]["id"] == 1
        assert val["questions"][1]["id"] == 2


def test_add_to_bank_collection_auto_migrates_list():
    """add_to_bank_collection 自动将旧 list 转为 dict 格式"""
    with tempfile.TemporaryDirectory() as tmpdir:
        raw = {"collections": {"oldlist": [{"id": 1, "type": "single"}]}}
        with open(os.path.join(tmpdir, 'collections.json'), 'w', encoding='utf-8') as f:
            json.dump(raw, f, ensure_ascii=False)
        result = add_to_bank_collection(tmpdir, "oldlist", 2, "multi")
        assert result is True
        data = load_bank_collections(tmpdir)
        val = data["collections"]["oldlist"]
        assert isinstance(val, dict)
        assert len(val["questions"]) == 2


def test_remove_from_bank_collection_auto_migrates_list():
    """remove_from_bank_collection 自动将旧 list 转为 dict 格式"""
    with tempfile.TemporaryDirectory() as tmpdir:
        raw = {"collections": {"oldlist": [{"id": 1, "type": "single"}]}}
        with open(os.path.join(tmpdir, 'collections.json'), 'w', encoding='utf-8') as f:
            json.dump(raw, f, ensure_ascii=False)
        result = remove_from_bank_collection(tmpdir, "oldlist", 1, "single")
        assert result is True
        data = load_bank_collections(tmpdir)
        val = data["collections"]["oldlist"]
        assert isinstance(val, dict)
        assert len(val["questions"]) == 0


def test_get_collection_names():
    """get_collection_names 返回排序的名称列表"""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_bank_collection(tmpdir, "B收藏")
        create_bank_collection(tmpdir, "A收藏")
        names = get_collection_names(tmpdir)
        assert names == ["A收藏", "B收藏"]


def test_get_collection_names_empty():
    """get_collection_names 无收藏夹时返回空列表"""
    with tempfile.TemporaryDirectory() as tmpdir:
        names = get_collection_names(tmpdir)
        assert names == []


# --- wrong count tests ---

def test_wrong_count_cumulative():
    """同一错题重复保存时 wrong_count 累加，唯一题数不变"""
    with tempfile.TemporaryDirectory() as tmpdir:
        q = {"id": 1, "type": "single", "question": "x", "options": {}, "answer": "A", "explanation": ""}
        save_bank_wrong_question(tmpdir, "test", q)
        save_bank_wrong_question(tmpdir, "test", q)
        save_bank_wrong_question(tmpdir, "test", q)
        data = load_bank_wrong_questions(tmpdir)
        entry = data["wrong_books"]["test"][0]
        assert entry["wrong_count"] == 3
        assert len(data["wrong_books"]["test"]) == 1


def test_wrong_count_accumulates_across_books():
    """同一题目在不同错题本中各自独立计数"""
    with tempfile.TemporaryDirectory() as tmpdir:
        q = {"id": 1, "type": "single", "question": "x", "options": {}, "answer": "A", "explanation": ""}
        save_bank_wrong_question(tmpdir, "book_a", q)
        save_bank_wrong_question(tmpdir, "book_a", q)
        save_bank_wrong_question(tmpdir, "book_b", q)
        data = load_bank_wrong_questions(tmpdir)
        assert data["wrong_books"]["book_a"][0]["wrong_count"] == 2
        assert data["wrong_books"]["book_b"][0]["wrong_count"] == 1
        assert len(data["wrong_books"]) == 2


def test_wrong_count_unique_and_total():
    """验证唯一题数和累计错误次数的关系"""
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(1, 4):
            q = {"id": i, "type": "single", "question": f"q{i}", "options": {}, "answer": "A", "explanation": ""}
            save_bank_wrong_question(tmpdir, "test", q)
            save_bank_wrong_question(tmpdir, "test", q)  # 每道题错两次
        data = load_bank_wrong_questions(tmpdir)
        assert len(data["wrong_books"]["test"]) == 3  # 3 道唯一题
        total_wrong = sum(q.get("wrong_count", 1) for q in data["wrong_books"]["test"])
        assert total_wrong == 6  # 累计 6 次错误
