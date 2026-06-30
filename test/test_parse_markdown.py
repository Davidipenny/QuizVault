#!/usr/bin/env python3
"""Tests for parse_markdown.py - section header detection and comment overrides"""

import unittest
from parse_markdown import parse_markdown


class TestSectionHeaderDetection(unittest.TestCase):
    """测试章节标题区分题型"""

    def test_chinese_single_choice_header(self):
        """## 单选题 标记后续为 single"""
        md = """## 单选题

**1. 测试题目（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：A**

**解析：** 测试解析
"""
        result = parse_markdown(md)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['type'], 'single')

    def test_chinese_multi_choice_header(self):
        """## 多选题 标记后续为 multi"""
        md = """## 多选题

**1. 测试题目（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：ABC**

**解析：** 测试解析
"""
        result = parse_markdown(md)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['type'], 'multi')

    def test_english_single_choice_header(self):
        """## Single Choice 标记后续为 single"""
        md = """## Single Choice

**1. Test question（　）**
A. Option A
B. Option B
C. Option C
D. Option D

**答案：A**

**解析：** Test explanation
"""
        result = parse_markdown(md)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['type'], 'single')

    def test_english_multi_choice_header(self):
        """## Multiple Choice 标记后续为 multi"""
        md = """## Multiple Choice

**1. Test question（　）**
A. Option A
B. Option B
C. Option C
D. Option D

**答案：AB**

**解析：** Test explanation
"""
        result = parse_markdown(md)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['type'], 'multi')

    def test_mixed_sections(self):
        """单选题和多选题章节混合"""
        md = """## 单选题

**1. 单选题目（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：A**

**解析：** 解析A

---

## 多选题

**1. 多选题目（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：ABC**

**解析：** 解析B
"""
        result = parse_markdown(md)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['type'], 'single')
        self.assertEqual(result[1]['type'], 'multi')


class TestCommentOverride(unittest.TestCase):
    """测试注释覆盖章节默认类型"""

    def test_multi_override_in_single_section(self):
        """在单选题章节中用 <!-- multi --> 标记多选题"""
        md = """## 单选题

**1. 单选题目（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：A**

**解析：** 解析

---

<!-- multi -->
**2. 实际是多选（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：AB**

**解析：** 解析
"""
        result = parse_markdown(md)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['type'], 'single')
        self.assertEqual(result[1]['type'], 'multi')

    def test_single_override_in_multi_section(self):
        """在多选题章节中用 <!-- single --> 标记单选题"""
        md = """## 多选题

**1. 多选题目（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：ABC**

**解析：** 解析

---

<!-- single -->
**2. 实际是单选（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：A**

**解析：** 解析
"""
        result = parse_markdown(md)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['type'], 'multi')
        self.assertEqual(result[1]['type'], 'single')


if __name__ == '__main__':
    unittest.main()
