#!/usr/bin/env python3
"""题目卡片组件 - 可复用的题目展示"""

import tkinter as tk


class QuestionCard(tk.Frame):
    """题目卡片 - 显示题干、选项、反馈，可被多个页面复用"""

    def __init__(self, master):
        super().__init__(master)
        self.selected_answer = tk.StringVar()
        self.check_vars = {}
        self.option_widgets = []
        self._locked = False
        self._build_ui()

    def _build_ui(self):
        # 题干
        self.question_label = tk.Label(
            self, font=("Microsoft YaHei", 13),
            wraplength=650, justify=tk.LEFT, anchor=tk.W,
        )
        self.question_label.pack(fill=tk.X, padx=10, pady=10)

        # 选项区
        self.options_frame = tk.Frame(self)
        self.options_frame.pack(fill=tk.X, padx=20)

        # 反馈区
        self.feedback_label = tk.Label(
            self, font=("Microsoft YaHei", 12),
            wraplength=650, justify=tk.LEFT,
        )
        self.feedback_label.pack(fill=tk.X, padx=10, pady=5)

        self.explanation_label = tk.Label(
            self, font=("Microsoft YaHei", 10), fg="gray",
            wraplength=650, justify=tk.LEFT,
        )
        self.explanation_label.pack(fill=tk.X, padx=10, pady=2)

    def load_question(self, q):
        """加载并显示一道题目

        Args:
            q: 题目字典，包含 type, question, options 等字段
        """
        self._clear_options()
        self.selected_answer.set('')
        self.check_vars = {}
        self._locked = False
        self._question_type = q['type']
        self._options = q['options']  # 保存选项引用

        # 题干
        type_tags = {
            'single': '【单选】',
            'multi': '【多选】',
            'truefalse': '【判断】',
        }
        type_tag = type_tags.get(q['type'], '【单选】')
        self.question_label.config(text=f"{type_tag} {q['question']}")

        # 选项 - 动态遍历，支持 2-4 个选项
        sorted_letters = sorted(q['options'].keys())
        if q['type'] == 'truefalse':
            # 判断题：垂直排列
            for letter in sorted_letters:
                rb = tk.Radiobutton(
                    self.options_frame,
                    text=f"{letter}. {q['options'][letter]}",
                    variable=self.selected_answer, value=letter,
                    font=("Microsoft YaHei", 11), anchor=tk.W,
                )
                rb.pack(fill=tk.X, pady=2)
                self.option_widgets.append(rb)
        elif q['type'] == 'single':
            for letter in sorted_letters:
                rb = tk.Radiobutton(
                    self.options_frame,
                    text=f"{letter}. {q['options'][letter]}",
                    variable=self.selected_answer, value=letter,
                    font=("Microsoft YaHei", 11), anchor=tk.W,
                )
                rb.pack(fill=tk.X, pady=2)
                self.option_widgets.append(rb)
        else:  # multi
            for letter in sorted_letters:
                var = tk.BooleanVar()
                self.check_vars[letter] = var
                cb = tk.Checkbutton(
                    self.options_frame,
                    text=f"{letter}. {q['options'][letter]}",
                    variable=var,
                    font=("Microsoft YaHei", 11), anchor=tk.W,
                )
                cb.pack(fill=tk.X, pady=2)
                self.option_widgets.append(cb)

        # 清空反馈
        self.feedback_label.config(text="")
        self.explanation_label.config(text="")

    def get_answer(self):
        """获取用户选择的答案

        Returns:
            单选返回单字母如 'A'，多选返回排序后字母如 'AB'，未选返回空串
        """
        if self.check_vars:  # 多选
            return ''.join(sorted(k for k, v in self.check_vars.items() if v.get()))
        else:  # 单选
            return self.selected_answer.get()

    def show_feedback(self, is_correct, correct_answer, explanation=''):
        """显示答题反馈

        Args:
            is_correct: 是否答对
            correct_answer: 正确答案
            explanation: 解析文本
        """
        if is_correct:
            self.feedback_label.config(text="✓ 正确！", fg="green")
        else:
            self.feedback_label.config(text=f"✗ 错误！正确答案是：{correct_answer}", fg="red")
        if explanation:
            self.explanation_label.config(text=f"解析：{explanation}")

    def lock_options(self):
        """锁定选项，答题后不允许修改"""
        self._locked = True
        for w in self.option_widgets:
            w.config(state=tk.DISABLED)

    def select_option(self, letter):
        """快捷键选择选项

        Args:
            letter: 选项字母 'A', 'B', 'C', 'D'
        """
        if self._locked:
            return
        # 检查选项是否存在
        if not hasattr(self, '_options') or letter not in self._options:
            return
        if self.check_vars:  # 多选 - 切换
            if letter in self.check_vars:
                self.check_vars[letter].set(not self.check_vars[letter].get())
        else:  # 单选/判断
            self.selected_answer.set(letter)

    def _clear_options(self):
        """清空选项区"""
        for w in self.option_widgets:
            w.destroy()
        self.option_widgets.clear()

    def reset(self):
        """完全重置卡片状态"""
        self._clear_options()
        self.selected_answer.set('')
        self.check_vars = {}
        self._locked = False
        self.question_label.config(text="")
        self.feedback_label.config(text="")
        self.explanation_label.config(text="")
