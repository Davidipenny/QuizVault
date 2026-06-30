#!/usr/bin/env python3
"""结算页"""

import tkinter as tk


class ResultPage(tk.Frame):
    """结算页 - 显示刷题结果"""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="刷题结束", font=("Microsoft YaHei", 18, "bold")).pack(pady=30)

        self.stats_frame = tk.Frame(self)
        self.stats_frame.pack(pady=10)

        self.total_label = tk.Label(self.stats_frame, font=("Microsoft YaHei", 13))
        self.total_label.pack(pady=3)
        self.correct_label = tk.Label(self.stats_frame, font=("Microsoft YaHei", 13), fg="green")
        self.correct_label.pack(pady=3)
        self.wrong_label = tk.Label(self.stats_frame, font=("Microsoft YaHei", 13), fg="red")
        self.wrong_label.pack(pady=3)
        self.accuracy_label = tk.Label(self.stats_frame, font=("Microsoft YaHei", 13), fg="blue")
        self.accuracy_label.pack(pady=3)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=30)
        tk.Button(btn_frame, text="重新刷题", command=self._retry, width=15, font=("Microsoft YaHei", 11)).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="返回操作页", command=self._back, width=15, font=("Microsoft YaHei", 11)).pack(side=tk.LEFT, padx=10)

    def refresh(self):
        total = self.app.quiz_total
        correct = self.app.quiz_correct
        wrong = self.app.quiz_wrong_count
        accuracy = (correct / total * 100) if total > 0 else 0

        self.total_label.config(text=f"总题数：{total}")
        self.correct_label.config(text=f"正确数：{correct}")
        self.wrong_label.config(text=f"错误数：{wrong}")
        self.accuracy_label.config(text=f"正确率：{accuracy:.1f}%")

    def _retry(self):
        self.app.show_page('quiz')

    def _back(self):
        self.app.show_page('operations')
