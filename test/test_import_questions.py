#!/usr/bin/env python3
"""import_questions.py 的单元测试"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from import_questions import validate_question, compute_hash


class TestValidateQuestion(unittest.TestCase):
    """测试题目验证"""

    def test_valid_single_choice(self):
        """合法的单选题应通过验证"""
        q = {
            'id': 1,
            'type': 'single',
            'question': '测试题目',
            'options': {'A': '选项A', 'B': '选项B', 'C': '选项C', 'D': '选项D'},
            'answer': 'A',
            'explanation': '解析'
        }
        errors = validate_question(q)
        self.assertEqual(errors, [])

    def test_valid_multi_choice(self):
        """合法的多选题应通过验证"""
        q = {
            'id': 1,
            'type': 'multi',
            'question': '测试题目',
            'options': {'A': '选项A', 'B': '选项B', 'C': '选项C', 'D': '选项D'},
            'answer': 'ABC',
            'explanation': '解析'
        }
        errors = validate_question(q)
        self.assertEqual(errors, [])

    def test_missing_required_fields(self):
        """缺少必填字段应报错"""
        q = {'id': 1}
        errors = validate_question(q)
        self.assertTrue(len(errors) > 0)
        self.assertTrue(any('type' in e for e in errors))
        self.assertTrue(any('question' in e for e in errors))
        self.assertTrue(any('options' in e for e in errors))
        self.assertTrue(any('answer' in e for e in errors))

    def test_invalid_type(self):
        """无效的题型应报错"""
        q = {
            'id': 1,
            'type': 'essay',
            'question': '测试题目',
            'options': {'A': '选项A', 'B': '选项B', 'C': '选项C', 'D': '选项D'},
            'answer': 'A'
        }
        errors = validate_question(q)
        self.assertTrue(any('type' in e for e in errors))

    def test_single_choice_invalid_answer(self):
        """单选题答案不是 A-D 应报错"""
        q = {
            'id': 1,
            'type': 'single',
            'question': '测试题目',
            'options': {'A': '选项A', 'B': '选项B', 'C': '选项C', 'D': '选项D'},
            'answer': 'AB'
        }
        errors = validate_question(q)
        self.assertTrue(any('answer' in e for e in errors))

    def test_multi_choice_too_few_answers(self):
        """多选题答案少于 2 个应报错"""
        q = {
            'id': 1,
            'type': 'multi',
            'question': '测试题目',
            'options': {'A': '选项A', 'B': '选项B', 'C': '选项C', 'D': '选项D'},
            'answer': 'A'
        }
        errors = validate_question(q)
        self.assertTrue(any('answer' in e for e in errors))

    def test_multi_choice_too_many_answers(self):
        """多选题答案超过 4 个应报错"""
        q = {
            'id': 1,
            'type': 'multi',
            'question': '测试题目',
            'options': {'A': '选项A', 'B': '选项B', 'C': '选项C', 'D': '选项D'},
            'answer': 'ABCDE'
        }
        errors = validate_question(q)
        self.assertTrue(any('answer' in e for e in errors))

    def test_multi_choice_duplicate_answers(self):
        """多选题答案有重复应报错"""
        q = {
            'id': 1,
            'type': 'multi',
            'question': '测试题目',
            'options': {'A': '选项A', 'B': '选项B', 'C': '选项C', 'D': '选项D'},
            'answer': 'AAB'
        }
        errors = validate_question(q)
        self.assertTrue(any('answer' in e for e in errors))

    def test_insufficient_options(self):
        """选项不足 4 个应报错"""
        q = {
            'id': 1,
            'type': 'single',
            'question': '测试题目',
            'options': {'A': '选项A', 'B': '选项B', 'C': '选项C'},
            'answer': 'A'
        }
        errors = validate_question(q)
        self.assertTrue(any('options' in e for e in errors))


class TestOptionConversion(unittest.TestCase):
    """测试选项格式转换"""

    def test_dict_to_list(self):
        """dict 格式转 list 格式"""
        from import_questions import convert_options_dict_to_list
        options = {'A': '选项A', 'B': '选项B', 'C': '选项C', 'D': '选项D'}
        result = convert_options_dict_to_list(options)
        self.assertEqual(result, ['A. 选项A', 'B. 选项B', 'C. 选项C', 'D. 选项D'])

    def test_list_to_dict(self):
        """list 格式转 dict 格式"""
        from import_questions import convert_options_list_to_dict
        options = ['A. 选项A', 'B. 选项B', 'C. 选项C', 'D. 选项D']
        result = convert_options_list_to_dict(options)
        self.assertEqual(result, {'A': '选项A', 'B': '选项B', 'C': '选项C', 'D': '选项D'})


class TestComputeHash(unittest.TestCase):
    """测试内容哈希"""

    def test_same_content_same_hash(self):
        """相同内容应生成相同哈希"""
        h1 = compute_hash("测试题目")
        h2 = compute_hash("测试题目")
        self.assertEqual(h1, h2)

    def test_different_content_different_hash(self):
        """不同内容应生成不同哈希"""
        h1 = compute_hash("题目A")
        h2 = compute_hash("题目B")
        self.assertNotEqual(h1, h2)

    def test_ignores_whitespace(self):
        """应忽略首尾空格"""
        h1 = compute_hash("  测试题目  ")
        h2 = compute_hash("测试题目")
        self.assertEqual(h1, h2)

    def test_ignores_punctuation(self):
        """应忽略首尾标点"""
        h1 = compute_hash("测试题目。")
        h2 = compute_hash("测试题目")
        self.assertEqual(h1, h2)


class TestImportFromMarkdown(unittest.TestCase):
    """测试从 Markdown 导入"""

    def setUp(self):
        """每个测试前准备空题库数据"""
        self.test_data = {
            'meta': {
                'version': 1,
                'updated': '2026-01-01',
                'source_files': [],
                'total': 0,
                'single_count': 0,
                'multi_count': 0
            },
            'questions': []
        }
        self._tmp_files = []

    def tearDown(self):
        """清理临时文件"""
        for f in self._tmp_files:
            if os.path.exists(f):
                os.remove(f)
        # 清理可能生成的题库文件
        from import_questions import QUESTIONS_FILE, QUESTIONS_FILE_JSON
        for path in [QUESTIONS_FILE, QUESTIONS_FILE_JSON]:
            if os.path.exists(path):
                os.remove(path)

    def _write_md(self, directory, filename, content):
        """写入临时 Markdown 文件并返回路径"""
        filepath = os.path.join(directory, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        self._tmp_files.append(filepath)
        return filepath

    def test_import_single_file(self):
        """导入单个 Markdown 文件"""
        import tempfile
        from import_questions import import_from_markdown, load_questions, save_questions

        md_content = """## 单选题

**1. 测试题目（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：A**

**解析：** 测试解析
"""
        tmpdir = tempfile.mkdtemp()
        test_file = self._write_md(tmpdir, "test.md", md_content)

        # 保存空题库
        save_questions(self.test_data)

        # 导入
        success, skipped, failed = import_from_markdown(test_file)

        self.assertEqual(success, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(failed, 0)

        # 验证题库
        data = load_questions()
        self.assertEqual(len(data['questions']), 1)
        self.assertEqual(data['questions'][0]['question'], '测试题目（　）')

    def test_dedup_on_reimport(self):
        """重复导入应跳过已有题目"""
        import tempfile
        from import_questions import import_from_markdown, load_questions, save_questions

        md_content = """## 单选题

**1. 测试题目（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：A**

**解析：** 测试解析
"""
        tmpdir = tempfile.mkdtemp()
        test_file = self._write_md(tmpdir, "test.md", md_content)

        save_questions(self.test_data)

        # 第一次导入
        success1, _, _ = import_from_markdown(test_file)
        self.assertEqual(success1, 1)

        # 第二次导入
        success2, skipped2, _ = import_from_markdown(test_file)
        self.assertEqual(success2, 0)
        self.assertEqual(skipped2, 1)

        # 题库中仍然只有一道题
        data = load_questions()
        self.assertEqual(len(data['questions']), 1)

    def test_import_nonexistent_file(self):
        """导入不存在的文件应返回 (0, 0, 0)"""
        from import_questions import import_from_markdown

        success, skipped, failed = import_from_markdown("/nonexistent/path.md")
        self.assertEqual(success, 0)
        self.assertEqual(skipped, 0)
        self.assertEqual(failed, 0)

    def test_import_empty_file(self):
        """导入空文件（无题目）应返回 (0, 0, 0)"""
        import tempfile
        from import_questions import import_from_markdown, save_questions

        tmpdir = tempfile.mkdtemp()
        test_file = self._write_md(tmpdir, "empty.md", "# 无题目\n\n这里是空的。\n")

        save_questions(self.test_data)

        success, skipped, failed = import_from_markdown(test_file)
        self.assertEqual(success, 0)
        self.assertEqual(skipped, 0)
        self.assertEqual(failed, 0)

    def test_import_sets_source(self):
        """导入的题目应包含 source 字段"""
        import tempfile
        from import_questions import import_from_markdown, load_questions, save_questions

        md_content = """## 单选题

**1. 测试来源（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：B**

**解析：** 测试来源解析
"""
        tmpdir = tempfile.mkdtemp()
        test_file = self._write_md(tmpdir, "myfile.md", md_content)

        save_questions(self.test_data)

        success, _, _ = import_from_markdown(test_file)
        self.assertEqual(success, 1)

        data = load_questions()
        self.assertEqual(data['questions'][0]['source'], 'myfile.md')
        self.assertIn('myfile.md', data['meta']['source_files'])

    def test_import_sets_content_hash(self):
        """导入的题目应包含 content_hash 字段"""
        import tempfile
        from import_questions import import_from_markdown, load_questions, save_questions

        md_content = """## 单选题

**1. 测试哈希（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：C**

**解析：** 测试哈希解析
"""
        tmpdir = tempfile.mkdtemp()
        test_file = self._write_md(tmpdir, "test.md", md_content)

        save_questions(self.test_data)

        success, _, _ = import_from_markdown(test_file)
        self.assertEqual(success, 1)

        data = load_questions()
        self.assertIn('content_hash', data['questions'][0])
        self.assertTrue(len(data['questions'][0]['content_hash']) > 0)

    def test_import_sets_flagged_fields(self):
        """导入的题目应包含 flagged 和 flag_reason 字段"""
        import tempfile
        from import_questions import import_from_markdown, load_questions, save_questions

        md_content = """## 单选题

**1. 测试标记（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：D**

**解析：** 测试标记解析
"""
        tmpdir = tempfile.mkdtemp()
        test_file = self._write_md(tmpdir, "test.md", md_content)

        save_questions(self.test_data)

        success, _, _ = import_from_markdown(test_file)
        self.assertEqual(success, 1)

        data = load_questions()
        q = data['questions'][0]
        self.assertIn('flagged', q)
        self.assertFalse(q['flagged'])
        self.assertIn('flag_reason', q)
        self.assertIsNone(q['flag_reason'])

    def test_import_multi_choice(self):
        """导入多选题"""
        import tempfile
        from import_questions import import_from_markdown, load_questions, save_questions

        md_content = """## 多选题

**1. 多选测试题目（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：ABC**

**解析：** 多选解析
"""
        tmpdir = tempfile.mkdtemp()
        test_file = self._write_md(tmpdir, "test.md", md_content)

        save_questions(self.test_data)

        success, _, _ = import_from_markdown(test_file)
        self.assertEqual(success, 1)

        data = load_questions()
        self.assertEqual(data['questions'][0]['type'], 'multi')
        self.assertEqual(data['questions'][0]['answer'], 'ABC')

    def test_import_multiple_questions(self):
        """导入包含多道题的文件"""
        import tempfile
        from import_questions import import_from_markdown, load_questions, save_questions

        md_content = """## 单选题

**1. 题目一（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：A**

**解析：** 解析一

---

**2. 题目二（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：B**

**解析：** 解析二
"""
        tmpdir = tempfile.mkdtemp()
        test_file = self._write_md(tmpdir, "test.md", md_content)

        save_questions(self.test_data)

        success, skipped, failed = import_from_markdown(test_file)
        self.assertEqual(success, 2)
        self.assertEqual(skipped, 0)
        self.assertEqual(failed, 0)

        data = load_questions()
        self.assertEqual(len(data['questions']), 2)

    def test_force_overwrite_dedup(self):
        """force=True 应跳过去重检查"""
        import tempfile
        from import_questions import import_from_markdown, load_questions, save_questions

        md_content = """## 单选题

**1. 强制导入题目（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：A**

**解析：** 强制导入解析
"""
        tmpdir = tempfile.mkdtemp()
        test_file = self._write_md(tmpdir, "test.md", md_content)

        save_questions(self.test_data)

        # 第一次导入
        success1, _, _ = import_from_markdown(test_file)
        self.assertEqual(success1, 1)

        # 第二次强制导入
        success2, skipped2, _ = import_from_markdown(test_file, force=True)
        self.assertEqual(success2, 1)
        self.assertEqual(skipped2, 0)

        # 题库中有两道题（重复）
        data = load_questions()
        self.assertEqual(len(data['questions']), 2)


class TestImportFromDirectory(unittest.TestCase):
    """测试从目录导入"""

    def setUp(self):
        """每个测试前准备空题库数据"""
        self.test_data = {
            'meta': {
                'version': 1,
                'updated': '2026-01-01',
                'source_files': [],
                'total': 0,
                'single_count': 0,
                'multi_count': 0
            },
            'questions': []
        }
        self._tmp_dirs = []

    def tearDown(self):
        """清理临时文件"""
        import shutil
        from import_questions import QUESTIONS_FILE, QUESTIONS_FILE_JSON
        for path in [QUESTIONS_FILE, QUESTIONS_FILE_JSON]:
            if os.path.exists(path):
                os.remove(path)
        for d in self._tmp_dirs:
            if os.path.exists(d):
                shutil.rmtree(d)

    def _make_md_dir(self, files_dict):
        """创建包含 md 文件的临时目录

        Args:
            files_dict: {filename: content} 字典

        Returns:
            目录路径
        """
        import tempfile
        tmpdir = tempfile.mkdtemp()
        self._tmp_dirs.append(tmpdir)
        for filename, content in files_dict.items():
            filepath = os.path.join(tmpdir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        return tmpdir

    def test_import_directory(self):
        """从目录导入多个 .md 文件"""
        from import_questions import import_from_directory, load_questions, save_questions

        md1 = """## 单选题

**1. 题目一（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：A**

**解析：** 解析一
"""
        md2 = """## 单选题

**2. 题目二（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：B**

**解析：** 解析二
"""
        tmpdir = self._make_md_dir({"file1.md": md1, "file2.md": md2})

        save_questions(self.test_data)

        success, skipped, failed = import_from_directory(tmpdir)
        self.assertEqual(success, 2)
        self.assertEqual(skipped, 0)
        self.assertEqual(failed, 0)

        data = load_questions()
        self.assertEqual(len(data['questions']), 2)

    def test_import_nonexistent_directory(self):
        """导入不存在的目录应返回 (0, 0, 0)"""
        from import_questions import import_from_directory

        success, skipped, failed = import_from_directory("/nonexistent/dir")
        self.assertEqual(success, 0)
        self.assertEqual(skipped, 0)
        self.assertEqual(failed, 0)

    def test_import_empty_directory(self):
        """导入空目录应返回 (0, 0, 0)"""
        import tempfile
        from import_questions import import_from_directory, save_questions

        tmpdir = tempfile.mkdtemp()
        self._tmp_dirs.append(tmpdir)

        save_questions(self.test_data)

        success, skipped, failed = import_from_directory(tmpdir)
        self.assertEqual(success, 0)
        self.assertEqual(skipped, 0)
        self.assertEqual(failed, 0)

    def test_import_directory_ignores_non_md(self):
        """目录中的非 .md 文件应被忽略"""
        import tempfile
        from import_questions import import_from_directory, load_questions, save_questions

        md_content = """## 单选题

**1. MD题目（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：A**

**解析：** MD解析
"""
        tmpdir = tempfile.mkdtemp()
        self._tmp_dirs.append(tmpdir)

        # 写入 .md 文件
        with open(os.path.join(tmpdir, "valid.md"), 'w', encoding='utf-8') as f:
            f.write(md_content)
        # 写入 .txt 文件（应被忽略）
        with open(os.path.join(tmpdir, "ignore.txt"), 'w', encoding='utf-8') as f:
            f.write("这不是markdown")

        save_questions(self.test_data)

        success, skipped, failed = import_from_directory(tmpdir)
        self.assertEqual(success, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(failed, 0)

        data = load_questions()
        self.assertEqual(len(data['questions']), 1)


if __name__ == '__main__':
    unittest.main()
