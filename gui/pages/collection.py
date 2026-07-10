#!/usr/bin/env python3
"""收藏夹页"""

import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from bank_manager import (
    load_bank_collections,
    create_bank_collection,
    delete_bank_collection,
    rename_bank_collection,
    remove_from_bank_collection,
)


def _get_collection_questions(collection_value):
    """兼容两种收藏夹格式，返回题目列表。

    create_bank_collection 存储为 {"created": ..., "questions": [...]}
    save_bank_collection 存储为直接的列表 [...]
    """
    if isinstance(collection_value, dict):
        return collection_value.get('questions', [])
    if isinstance(collection_value, list):
        return collection_value
    return []


class CollectionPage(tk.Frame):
    """收藏夹页 - 列表视图"""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.collections = {}
        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="收藏夹管理", font=self.app.get_font(16, bold=True)).pack(pady=15)

        list_frame = tk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        self.listbox = tk.Listbox(list_frame, font=self.app.get_font(12), height=15)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox.bind('<Double-1>', lambda e: self._open_detail())

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="打开", command=self._open_detail, width=10,
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="新建", command=self._create, width=10,
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="删除", command=self._delete, width=10,
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="返回", command=lambda: self.app.show_page('operations'), width=10,
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=5)

    def refresh(self):
        bank = self.app.selected_bank
        data = load_bank_collections(bank['path'])
        self.collections = data.get('collections', {})
        self.listbox.delete(0, tk.END)
        for name, value in self.collections.items():
            items = _get_collection_questions(value)
            self.listbox.insert(tk.END, f"{name}（{len(items)} 题）")

    def _open_detail(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个收藏夹")
            return
        idx = selection[0]
        name = list(self.collections.keys())[idx]
        self.app.selected_collection = name
        self.app.show_page('collection_detail')

    def _create(self):
        name = simpledialog.askstring("新建收藏夹", "输入名称：", parent=self)
        if name:
            bank = self.app.selected_bank
            if create_bank_collection(bank['path'], name):
                self.refresh()
            else:
                messagebox.showwarning("提示", "收藏夹已存在")

    def _delete(self):
        selection = self.listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        name = list(self.collections.keys())[idx]
        if messagebox.askyesno("确认", f'删除收藏夹"{name}"？'):
            bank = self.app.selected_bank
            delete_bank_collection(bank['path'], name)
            self.refresh()


class CollectionDetailPage(tk.Frame):
    """收藏夹详情页"""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.items = []
        self._build_ui()

    def _build_ui(self):
        self.title_label = tk.Label(self, font=self.app.get_font(16, bold=True))
        self.title_label.pack(pady=15)

        list_frame = tk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        self.listbox = tk.Listbox(list_frame, font=self.app.get_font(11), height=15)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="顺序刷题", command=lambda: self._start_quiz('sequential'), width=10,
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="随机刷题", command=lambda: self._start_quiz('random'), width=10,
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="重命名", command=self._rename, width=8,
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="删除", command=self._delete, width=8,
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="导出MD", command=self._export, width=8,
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="移除题目", command=self._remove_question, width=8,
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="返回", command=lambda: self.app.show_page('collection'), width=8,
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=3)

    def refresh(self):
        name = self.app.selected_collection
        bank = self.app.selected_bank
        self.title_label.config(text=f"收藏夹：{name}")

        data = load_bank_collections(bank['path'])
        raw = data.get('collections', {}).get(name, [])
        self.items = _get_collection_questions(raw)
        self.listbox.delete(0, tk.END)
        for i, qref in enumerate(self.items, 1):
            qtype = "单选" if qref['type'] == 'single' else "多选"
            qtext = qref.get('question', '')[:40]
            self.listbox.insert(tk.END, f"{i}. [{qtype}] {qtext}")

    def _start_quiz(self, mode):
        if not self.items:
            messagebox.showinfo("提示", "收藏夹为空")
            return
        # 构建完整题目列表
        questions = []
        bank = self.app.selected_bank
        for qref in self.items:
            for q in bank['questions']:
                if q['id'] == qref['id'] and q['type'] == qref['type']:
                    questions.append(q)
                    break
        if not questions:
            messagebox.showinfo("提示", "收藏夹中题目已全部删除")
            return
        self.app.quiz_questions = questions
        self.app.quiz_mode = mode
        self.app.quiz_type = 'all'
        self.app.show_page('quiz')

    def _rename(self):
        new_name = simpledialog.askstring("重命名", "新名称：", parent=self)
        if new_name:
            bank = self.app.selected_bank
            old_name = self.app.selected_collection
            if rename_bank_collection(bank['path'], old_name, new_name):
                self.app.selected_collection = new_name
                self.refresh()
            else:
                messagebox.showwarning("提示", "名称已存在或无效")

    def _delete(self):
        name = self.app.selected_collection
        if messagebox.askyesno("确认", f'删除收藏夹"{name}"？'):
            bank = self.app.selected_bank
            delete_bank_collection(bank['path'], name)
            self.app.show_page('collection')

    def _export(self):
        if not self.items:
            messagebox.showinfo("提示", "收藏夹为空")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md")],
            initialfile=f"{self.app.selected_collection}.md",
        )
        if not filename:
            return
        bank = self.app.selected_bank
        questions = []
        for qref in self.items:
            for q in bank['questions']:
                if q['id'] == qref['id'] and q['type'] == qref['type']:
                    questions.append(q)
                    break
        lines = []
        for i, q in enumerate(questions, 1):
            lines.append(f"**{i}. {q['question']}（　）**")
            if isinstance(q['options'], dict):
                for letter in sorted(q['options'].keys()):
                    lines.append(f"{letter}. {q['options'][letter]}")
            elif isinstance(q['options'], list):
                for opt in q['options']:
                    lines.append(opt)
            lines.append(f"\n**答案：{q['answer']}**\n")
            if q.get('explanation'):
                lines.append(f"**解析：** {q['explanation']}\n")
            lines.append("---")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        messagebox.showinfo("成功", f"已导出到 {filename}")

    def _remove_question(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一道题目")
            return
        idx = selection[0]
        qref = self.items[idx]
        bank = self.app.selected_bank
        remove_from_bank_collection(bank['path'], self.app.selected_collection, qref['id'], qref['type'])
        self.refresh()
