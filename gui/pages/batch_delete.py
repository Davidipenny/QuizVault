#!/usr/bin/env python3
"""批量删题页"""

import tkinter as tk
from tkinter import messagebox
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from bank_manager import add_to_bank_deleted, scan_banks_folder


class BatchDeletePage(tk.Frame):
    """批量删题页"""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.check_vars = []
        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="批量删题", font=self.app.get_font(16, bold=True)).pack(pady=15)

        # 全选/取消
        ctrl_frame = tk.Frame(self)
        ctrl_frame.pack(fill=tk.X, padx=20)
        tk.Button(ctrl_frame, text="全选", command=self._select_all, width=8,
                  font=self.app.get_font(10)).pack(side=tk.LEFT)
        tk.Button(ctrl_frame, text="取消全选", command=self._select_none, width=8,
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=5)

        # 题目列表（带复选框）
        list_frame = tk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        self.canvas = tk.Canvas(list_frame)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor=tk.NW)
        self.canvas.config(yscrollcommand=scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 鼠标滚轮绑定方法
        self._batch_mousewheel = lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="确认删除", command=self._delete_selected, width=12, fg="red",
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="返回", command=lambda: self.app.show_page('operations'), width=12,
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=5)

    def refresh(self):
        # 设置本页面的鼠标滚轮绑定（show_page 的 unbind_all 之后重新绑定）
        self.bind_all("<MouseWheel>", self._batch_mousewheel)
        for w in self.scrollable_frame.winfo_children():
            w.destroy()
        self.check_vars = []
        bank = self.app.selected_bank
        questions = bank['questions']
        for i, q in enumerate(questions):
            var = tk.BooleanVar()
            self.check_vars.append((var, q))
            qtype = "单选" if q['type'] == 'single' else "多选"
            text = f"{i+1}. [{qtype}] {q['question'][:50]}"
            cb = tk.Checkbutton(self.scrollable_frame, text=text, variable=var, anchor=tk.W,
                                font=self.app.get_font(10))
            cb.pack(fill=tk.X, pady=1)

    def _select_all(self):
        for var, _ in self.check_vars:
            var.set(True)

    def _select_none(self):
        for var, _ in self.check_vars:
            var.set(False)

    def _delete_selected(self):
        to_delete = [q for var, q in self.check_vars if var.get()]
        if not to_delete:
            messagebox.showwarning("提示", "未选择任何题目")
            return
        if not messagebox.askyesno("确认", f"确定删除 {len(to_delete)} 道题目？"):
            return
        bank = self.app.selected_bank
        for q in to_delete:
            add_to_bank_deleted(bank['path'], q['id'], q['type'])
        messagebox.showinfo("成功", f"已删除 {len(to_delete)} 道题目")
        # 刷新题库数据
        banks_dir = os.path.dirname(bank['path'])
        banks = scan_banks_folder(banks_dir)
        for b in banks:
            if b['name'] == bank['name']:
                self.app.selected_bank = b
                break
        self.refresh()
