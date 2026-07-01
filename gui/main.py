#!/usr/bin/env python3
"""QuizVault - 选择题刷题系统 GUI 版本"""

import os
import sys

# Windows 高 DPI 支持 - 必须在创建 tk 窗口之前设置
if sys.platform == 'win32':
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)  # Per-Monitor DPI Aware
    except Exception:
        try:
            windll.user32.SetProcessDPIAware()
        except Exception:
            pass

import tkinter as tk

# gui 目录
GUI_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GUI_DIR)

from pages.bank_select import BankSelectPage
from pages.operations import OperationsPage
from pages.quiz import QuizPage
from pages.result import ResultPage
from pages.wrong_book import WrongBookPage
from pages.collection import CollectionPage, CollectionDetailPage
from pages.flagged import FlaggedPage
from pages.batch_delete import BatchDeletePage

# 项目根目录
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 将项目根目录加入 sys.path，以便导入 bank_manager 等模块
sys.path.insert(0, BASE_DIR)

BANKS_FOLDER = os.path.join(BASE_DIR, 'banks')


class App(tk.Tk):
    """主应用程序窗口"""

    def __init__(self):
        super().__init__()
        self.title("QuizVault 选择题刷题系统")
        self.geometry("700x500")
        self.resizable(True, True)
        self.minsize(600, 400)

        self.pages = {}
        self.current_page = None
        self.selected_bank = None

        # 注册页面
        self.pages['bank_select'] = BankSelectPage(self, self, BANKS_FOLDER)
        self.pages['operations'] = OperationsPage(self, self)
        self.pages['quiz'] = QuizPage(self, self)
        self.pages['result'] = ResultPage(self, self)
        self.pages['wrong_book'] = WrongBookPage(self, self)
        self.pages['collection'] = CollectionPage(self, self)
        self.pages['collection_detail'] = CollectionDetailPage(self, self)
        self.pages['flagged'] = FlaggedPage(self, self)
        self.pages['batch_delete'] = BatchDeletePage(self, self)
        self.pages['bank_select'].pack(fill=tk.BOTH, expand=True)
        self.current_page = self.pages['bank_select']

        # 窗口关闭时保存刷题进度
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_closing(self):
        """窗口关闭时保存当前进度"""
        try:
            if self.current_page is self.pages.get('quiz'):
                self.current_page._save_progress()
        except Exception:
            pass  # 保存进度失败不应阻止窗口关闭
        self.destroy()

    def show_page(self, page_name: str):
        """切换到指定页面"""
        if self.current_page:
            self.current_page.pack_forget()
        page = self.pages[page_name]
        if hasattr(page, 'refresh'):
            if page_name == 'quiz':
                resume_data = getattr(self, 'quiz_resume_data', None)
                page.refresh(resume_data=resume_data)
                self.quiz_resume_data = None  # 清除，避免下次重复使用
            else:
                page.refresh()
        page.pack(fill=tk.BOTH, expand=True)
        self.current_page = page


if __name__ == '__main__':
    app = App()
    app.mainloop()
