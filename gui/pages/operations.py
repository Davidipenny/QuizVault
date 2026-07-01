#!/usr/bin/env python3
"""操作选择页"""

import tkinter as tk
from tkinter import messagebox
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from bank_manager import load_quiz_progress, delete_quiz_progress


class OperationsPage(tk.Frame):
    """操作选择页 - 显示题库信息和功能按钮"""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        self.title_label = tk.Label(self, font=("Microsoft YaHei", 16, "bold"))
        self.title_label.pack(pady=15)

        self.info_label = tk.Label(self, font=("Microsoft YaHei", 11))
        self.info_label.pack(pady=5)

        # 功能按钮（可滚动区域）
        container = tk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        btn_frame = tk.Frame(canvas)

        btn_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=btn_frame, anchor=tk.N)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        buttons = [
            ("顺序刷题（判断）", lambda: self._start_quiz('sequential', 'truefalse')),
            ("随机刷题（判断）", lambda: self._start_quiz('random', 'truefalse')),
            ("顺序刷题（单选）", lambda: self._start_quiz('sequential', 'single')),
            ("随机刷题（单选）", lambda: self._start_quiz('random', 'single')),
            ("顺序刷题（多选）", lambda: self._start_quiz('sequential', 'multi')),
            ("随机刷题（多选）", lambda: self._start_quiz('random', 'multi')),
            ("顺序刷题（全部）", lambda: self._start_quiz('sequential', 'all')),
            ("随机刷题（全部）", lambda: self._start_quiz('random', 'all')),
            ("错题回顾", lambda: self.app.show_page('wrong_book')),
            ("收藏夹管理", lambda: self.app.show_page('collection')),
            ("标记题目", lambda: self.app.show_page('flagged')),
            ("批量删题", lambda: self.app.show_page('batch_delete')),
            ("返回题库选择", lambda: self.app.show_page('bank_select')),
        ]

        for text, cmd in buttons:
            tk.Button(btn_frame, text=text, command=cmd, width=20, font=("Microsoft YaHei", 10)).pack(pady=3)

    def refresh(self):
        """刷新页面信息"""
        bank = self.app.selected_bank
        if bank:
            self.title_label.config(text=bank['name'])
            questions = bank['questions']
            truefalse = sum(1 for q in questions if q['type'] == 'truefalse')
            single = sum(1 for q in questions if q['type'] == 'single')
            multi = sum(1 for q in questions if q['type'] == 'multi')
            self.info_label.config(text=f"共 {len(questions)} 题（判断 {truefalse} / 单选 {single} / 多选 {multi}）")

    def _start_quiz(self, mode, q_type):
        """开始刷题"""
        bank = self.app.selected_bank
        questions = bank['questions']
        if q_type != 'all':
            questions = [q for q in questions if q['type'] == q_type]
        if not questions:
            messagebox.showinfo("提示", "没有该类型的题目")
            return

        # 检测是否有可恢复的进度
        progress = load_quiz_progress(bank['path'])
        resume_data = None

        if progress and progress.get('mode') == mode and progress.get('question_type') == q_type:
            current = progress.get('current_idx', 0)
            total = progress.get('total_questions', 0)
            correct = progress.get('correct_count', 0)
            answer = messagebox.askyesno(
                "检测到未完成的刷题",
                f"上次做到第 {current}/{total} 题，已答对 {correct} 题\n\n是否继续？",
                icon='question'
            )
            if answer:
                resume_data = progress
            else:
                delete_quiz_progress(bank['path'])

        self.app.quiz_questions = questions
        self.app.quiz_mode = mode
        self.app.quiz_type = q_type
        self.app.quiz_resume_data = resume_data
        self.app.show_page('quiz')
