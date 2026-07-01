#!/usr/bin/env python3
"""错题本页"""

import json
import os
import tkinter as tk
from tkinter import messagebox, simpledialog

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from bank_manager import load_bank_wrong_questions


class WrongBookPage(tk.Frame):
    """错题本页 - 显示错题本列表"""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.wrong_books = {}
        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="错题本", font=("Microsoft YaHei", 16, "bold")).pack(pady=15)

        list_frame = tk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        self.listbox = tk.Listbox(list_frame, font=("Microsoft YaHei", 12), height=15)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="开始刷题", command=self._start_review, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="新建错题本", command=self._create_book, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="返回", command=lambda: self.app.show_page('operations'), width=12).pack(side=tk.LEFT, padx=5)

    def refresh(self):
        bank = self.app.selected_bank
        data = load_bank_wrong_questions(bank['path'])
        self.wrong_books = data.get('wrong_books', {})
        self.listbox.delete(0, tk.END)
        for name, questions in self.wrong_books.items():
            self.listbox.insert(tk.END, f"{name}（{len(questions)} 题）")

    def _start_review(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个错题本")
            return
        idx = selection[0]
        name = list(self.wrong_books.keys())[idx]
        questions = self.wrong_books[name]
        if not questions:
            messagebox.showinfo("提示", "该错题本为空")
            return
        self.app.quiz_questions = questions
        self.app.quiz_mode = 'sequential'
        self.app.quiz_type = 'all'
        self.app.show_page('quiz')

    def _create_book(self):
        name = simpledialog.askstring("新建错题本", "输入名称：", parent=self)
        if name:
            bank = self.app.selected_bank
            data = load_bank_wrong_questions(bank['path'])
            data.setdefault('wrong_books', {})[name] = []
            filepath = os.path.join(bank['path'], 'wrong_questions.json')
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.refresh()
