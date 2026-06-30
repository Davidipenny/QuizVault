#!/usr/bin/env python3
"""题库选择页"""

import tkinter as tk
from tkinter import messagebox
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from bank_manager import scan_banks_folder


class BankSelectPage(tk.Frame):
    """题库选择页 - 显示 banks/ 下所有题库"""

    def __init__(self, master, app, banks_folder):
        super().__init__(master)
        self.app = app
        self.banks_folder = banks_folder
        self._build_ui()

    def _build_ui(self):
        # 标题
        tk.Label(self, text="选择题库", font=("Microsoft YaHei", 16, "bold")).pack(pady=15)

        # 题库列表
        list_frame = tk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        self.listbox = tk.Listbox(list_frame, font=("Microsoft YaHei", 12), height=15)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 双击进入
        self.listbox.bind('<Double-1>', self._on_double_click)

        # 按钮区
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="进入", command=self._enter_bank, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="退出", command=self.app.quit, width=10).pack(side=tk.LEFT, padx=5)

        self.refresh()

    def refresh(self):
        """刷新题库列表"""
        self.banks = scan_banks_folder(self.banks_folder)
        self.listbox.delete(0, tk.END)
        for bank in self.banks:
            q_count = len(bank['questions'])
            self.listbox.insert(tk.END, f"{bank['name']}（{q_count} 题）")

    def _on_double_click(self, event):
        self._enter_bank()

    def _enter_bank(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个题库")
            return
        idx = selection[0]
        bank = self.banks[idx]
        self.app.selected_bank = bank
        self.app.show_page('operations')
