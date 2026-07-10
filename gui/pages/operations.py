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
        self.title_label = tk.Label(self, font=self.app.get_font(16, bold=True))
        self.title_label.pack(pady=15)

        # 字体调节按钮
        font_frame = tk.Frame(self)
        font_frame.pack(pady=(0, 5))
        tk.Label(font_frame, text="字体大小：", font=self.app.get_font(10)).pack(side=tk.LEFT)
        self.font_scale_label = tk.Label(font_frame, text="100%", font=self.app.get_font(10), width=5)
        self.font_scale_label.pack(side=tk.LEFT)
        tk.Button(font_frame, text="缩小", command=self._decrease_font,
                  width=6, font=self.app.get_font(10)).pack(side=tk.LEFT, padx=3)
        tk.Button(font_frame, text="放大", command=self._increase_font,
                  width=6, font=self.app.get_font(10)).pack(side=tk.LEFT, padx=3)

        self.info_label = tk.Label(self, font=self.app.get_font(11))
        self.info_label.pack(pady=5)

        # 功能按钮（可滚动区域）
        container = tk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self._op_canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient=tk.VERTICAL, command=self._op_canvas.yview)
        self._op_btn_frame = tk.Frame(self._op_canvas)

        self._op_btn_frame.bind("<Configure>", lambda e: self._op_canvas.configure(
            scrollregion=self._op_canvas.bbox("all")))
        self._op_canvas.create_window((0, 0), window=self._op_btn_frame, anchor=tk.N)
        self._op_canvas.configure(yscrollcommand=scrollbar.set)

        self._op_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 按首次刷新创建按钮（refresh 中会重建）
        self._buttons_data = None

    def _on_op_mousewheel(self, event):
        """操作页功能按钮区鼠标滚轮"""
        self._op_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _rebuild_buttons(self):
        """（重新）创建功能按钮，使用当前字体大小"""
        for w in self._op_btn_frame.winfo_children():
            w.destroy()
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
            tk.Button(self._op_btn_frame, text=text, command=cmd, width=20,
                      font=self.app.get_font(10)).pack(pady=3)

    def _increase_font(self):
        self.app.increase_font()
        self.refresh()

    def _decrease_font(self):
        self.app.decrease_font()
        self.refresh()

    def refresh(self):
        """刷新页面信息"""
        bank = self.app.selected_bank
        if bank:
            self.title_label.config(text=bank['name'], font=self.app.get_font(16, bold=True))
            self.info_label.config(font=self.app.get_font(11))
            questions = bank['questions']
            truefalse = sum(1 for q in questions if q['type'] == 'truefalse')
            single = sum(1 for q in questions if q['type'] == 'single')
            multi = sum(1 for q in questions if q['type'] == 'multi')
            self.info_label.config(text=f"共 {len(questions)} 题（判断 {truefalse} / 单选 {single} / 多选 {multi}）")
        # 刷新按钮字体和字体缩放百分比
        self._rebuild_buttons()
        self.font_scale_label.config(text=f"{round(self.app.font_scale * 100)}%")
        # 设置本页面的鼠标滚轮绑定（show_page 的 unbind_all 之后重新绑定）
        self.bind_all("<MouseWheel>", self._on_op_mousewheel)

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
