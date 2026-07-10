#!/usr/bin/env python3
"""刷题页"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from bank_manager import (
    create_bank_collection,
    add_to_bank_collection,
    get_collection_names,
    save_bank_wrong_question,
    remove_bank_wrong_question,
    save_quiz_progress,
    delete_quiz_progress,
    add_to_bank_flagged,
)
from datetime import datetime

from widgets.question_card import QuestionCard


class CollectionPickerDialog(tk.Toplevel):
    """收藏夹选择对话框 — 可选已有收藏夹或输入新名称"""

    def __init__(self, parent, existing_names):
        super().__init__(parent)
        self.result = None
        self.title("收藏")
        self.geometry("400x300")
        self.transient(parent)
        self.grab_set()

        tk.Label(self, text="选择已有收藏夹或输入新名称：", font=("Microsoft YaHei", 10)).pack(pady=5)

        # 已有收藏夹列表
        self.listbox = tk.Listbox(self, font=("Microsoft YaHei", 11), height=8)
        for name in existing_names:
            self.listbox.insert(tk.END, name)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.listbox.bind('<Double-1>', lambda e: self._pick_selected())

        # 新名称输入
        self.entry = tk.Entry(self, font=("Microsoft YaHei", 11))
        self.entry.pack(fill=tk.X, padx=10, pady=5)
        self.entry.bind('<Return>', lambda e: self._confirm())

        # 按钮
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="确定", command=self._confirm, width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", command=self.destroy, width=8).pack(side=tk.LEFT, padx=5)

        self.wait_window()

    def _pick_selected(self):
        sel = self.listbox.curselection()
        if sel:
            self.result = self.listbox.get(sel[0])
            self.destroy()

    def _confirm(self):
        name = self.entry.get().strip()
        if name:
            self.result = name
            self.destroy()
        else:
            self._pick_selected()


class QuizPage(tk.Frame):
    """刷题页 - 核心答题界面"""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.questions = []
        self.current_idx = 0
        self.correct_count = 0
        self.wrong_questions = []
        self.answered = False
        self.answers = {}  # {index: answer_snapshot}
        self._build_ui()

    def _build_ui(self):
        # 顶栏：来源 + 进度
        self.header_frame = tk.Frame(self)
        self.header_frame.pack(fill=tk.X, padx=10, pady=5)
        self.source_label = tk.Label(self.header_frame, font=self.app.get_font(9), fg="gray")
        self.source_label.pack(side=tk.LEFT)
        self.progress_label = tk.Label(self.header_frame, font=self.app.get_font(9))
        self.progress_label.pack(side=tk.RIGHT)

        # --- 可滚动的题目卡片区域 ---
        self.scroll_container = tk.Frame(self)
        self.scroll_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        self.card_canvas = tk.Canvas(self.scroll_container, highlightthickness=0)
        self.card_scrollbar = tk.Scrollbar(self.scroll_container, orient=tk.VERTICAL, command=self.card_canvas.yview)
        self.card_frame = tk.Frame(self.card_canvas)
        self.card_frame.bind("<Configure>", lambda e: self.card_canvas.configure(
            scrollregion=self.card_canvas.bbox("all")))
        self.card_canvas.create_window((0, 0), window=self.card_frame, anchor=tk.NW)
        self.card_canvas.configure(yscrollcommand=self.card_scrollbar.set)

        self.card_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.card_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 题目卡片（放入可滚动区域）
        self.card = QuestionCard(self.card_frame, app=self.app)
        self.card.pack(fill=tk.X, padx=5, pady=5)

        # --- 提交按钮（始终可见）---
        self.submit_btn = tk.Button(self, text="提交答案", command=self._submit,
                                    font=self.app.get_font(11))
        self.submit_btn.pack(pady=(0, 5))

        # --- 底部操作栏（始终可见）---
        self.bottom_frame = tk.Frame(self)
        self.bottom_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        self.flag_btn = tk.Button(self.bottom_frame, text="标记", command=self._flag,
                                  font=self.app.get_font(10))
        self.flag_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.collect_btn = tk.Button(self.bottom_frame, text="收藏", command=self._collect,
                                     font=self.app.get_font(10))
        self.collect_btn.pack(side=tk.LEFT)
        self.next_btn = tk.Button(self.bottom_frame, text="下一题 →", command=self._next,
                                  font=self.app.get_font(10))
        self.next_btn.pack(side=tk.RIGHT)
        self.next_btn.pack_forget()

        # 返回按钮
        self.back_btn = tk.Button(self.bottom_frame, text="← 返回", command=self._save_and_go_back,
                                  font=self.app.get_font(10))
        self.back_btn.pack(side=tk.LEFT)

        # 上一题按钮（回顾）
        self.prev_btn = tk.Button(self.bottom_frame, text="← 上一题", command=self._prev,
                                  font=self.app.get_font(10))

        # 快捷键 - 绑定到本 frame，refresh 时获取焦点
        self.bind('<Return>', self._on_return)
        self.bind('<space>', self._on_space)
        self.bind('<Escape>', self._on_escape)
        self.bind('f', self._on_f)
        self.bind('F', self._on_f)
        for letter in 'abcd':
            self.bind(letter, lambda e, l=letter.upper(): self.card.select_option(l))

    def _on_canvas_mousewheel(self, event):
        """鼠标滚轮滚动卡片区域"""
        self.card_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def refresh(self, resume_data=None):
        """开始新一轮刷题"""
        self.focus_set()
        self.questions = list(self.app.quiz_questions)

        if resume_data:
            # 恢复模式
            if resume_data.get('question_order'):
                order = resume_data['question_order']
                ordered = []
                for idx in order:
                    if idx < len(self.questions):
                        ordered.append(self.questions[idx])
                self.questions = ordered
            self.current_idx = resume_data.get('current_idx', 0)
            self.correct_count = resume_data.get('correct_count', 0)
            # 恢复错题
            self.wrong_questions = []
            if resume_data.get('wrong_questions'):
                for wr in resume_data['wrong_questions']:
                    for q in self.questions:
                        if q['id'] == wr['id'] and q['type'] == wr['type']:
                            self.wrong_questions.append(q)
                            break
            # 恢复作答历史
            self.answers = {
                i: a for i, a in enumerate(resume_data.get('answers', [])) if a is not None
            }
        else:
            if self.app.quiz_mode == 'random':
                indices = list(range(len(self.questions)))
                random.shuffle(indices)
                self.questions = [self.questions[i] for i in indices]
                self._shuffle_order = indices
            else:
                self._shuffle_order = None
            self.current_idx = 0
            self.correct_count = 0
            self.wrong_questions = []
            self.answers = {}

        self.answered = False
        # 设置鼠标滚轮绑定（在 show_page 的 unbind_all 之后重新绑定）
        self.bind_all("<MouseWheel>", self._on_canvas_mousewheel)
        self._show_question()

    def _show_question(self):
        """显示当前题目"""
        q = self.questions[self.current_idx]

        # 来源
        source = q.get('source', '')
        self.source_label.config(text=f"来源：{source}" if source else "")

        # 进度
        self.progress_label.config(text=f"[{self.current_idx + 1}/{len(self.questions)}]")

        # 加载题目到卡片
        self.card.load_question(q)

        # 判断模式：已答题 → 回顾模式，否则 → 答题模式
        if self.current_idx in self.answers:
            self._show_review_question()
        else:
            self._show_active_question()

    def _show_review_question(self):
        """以回顾模式显示当前已答题（只读）"""
        q = self.questions[self.current_idx]
        ans = self.answers[self.current_idx]

        # 还原用户选择的答案
        user_ans = ans['user_answer']
        if q['type'] == 'multi':
            for letter in user_ans:
                self.card.select_option(letter)
        else:
            self.card.select_option(user_ans)

        self.card.lock_options()
        self.card.show_feedback(ans['is_correct'], ans['correct_answer'], ans['explanation'])

        # 按钮控制
        self.submit_btn.pack_forget()
        self.prev_btn.pack(side=tk.LEFT) if self.current_idx > 0 else self.prev_btn.pack_forget()
        self.next_btn.pack(side=tk.RIGHT)

    def _show_active_question(self):
        """以答题模式显示当前未答题"""
        self.answered = False
        self.submit_btn.pack(pady=(0, 5))
        self.next_btn.pack_forget()
        self.prev_btn.pack(side=tk.LEFT) if self.answers else self.prev_btn.pack_forget()

    def _submit(self):
        """提交答案"""
        user_answer = self.card.get_answer()
        if not user_answer:
            messagebox.showwarning("提示", "请先选择答案")
            return

        q = self.questions[self.current_idx]
        correct_answer = q['answer'].upper()
        is_correct = sorted(user_answer.upper()) == sorted(correct_answer)

        self.answered = True
        self.submit_btn.pack_forget()

        # 存储作答记录
        self.answers[self.current_idx] = {
            'user_answer': user_answer,
            'is_correct': is_correct,
            'correct_answer': correct_answer,
            'explanation': q.get('explanation', ''),
        }

        # 显示反馈
        explanation = q.get('explanation', '')
        self.card.show_feedback(is_correct, correct_answer, explanation)
        self.card.lock_options()

        # 记录结果
        bank = self.app.selected_bank
        if is_correct:
            self.correct_count += 1
            remove_bank_wrong_question(bank['path'], q['id'], q['type'])
        else:
            self.wrong_questions.append(q)
            default_book = f"{bank['name']}错题"
            save_bank_wrong_question(bank['path'], default_book, q)

        # 显示下一题按钮
        self.next_btn.pack(side=tk.RIGHT)

    def _next(self):
        """下一题"""
        if self.current_idx in self.answers:
            # 回顾模式：始终可以前进
            self.current_idx += 1
            if self.current_idx >= len(self.questions):
                self._show_result()
            else:
                self._show_question()
        else:
            # 答题模式：必须先提交
            if not self.answered:
                return
            self.current_idx += 1
            if self.current_idx >= len(self.questions):
                self._show_result()
            else:
                self._show_question()

    def _prev(self):
        """上一题（回顾）"""
        if self.current_idx > 0:
            self.current_idx -= 1
            self._show_question()

    def _show_result(self):
        """显示刷题结果"""
        # 刷题完成，删除进度文件
        delete_quiz_progress(self.app.selected_bank['path'])

        total = len(self.questions)
        correct = self.correct_count
        wrong = total - correct

        self.app.quiz_total = total
        self.app.quiz_correct = correct
        self.app.quiz_wrong_count = wrong
        self.app.show_page('result')

    def _collect(self):
        """收藏当前题目"""
        if not self.questions:
            return
        q = self.questions[self.current_idx]
        bank = self.app.selected_bank
        existing = get_collection_names(bank['path'])
        dialog = CollectionPickerDialog(self, existing)
        name = dialog.result
        if name:
            create_bank_collection(bank['path'], name)  # 已存在则无操作
            add_to_bank_collection(bank['path'], name, q['id'], q['type'])
            messagebox.showinfo("成功", f'已加入收藏夹"{name}"')

    def _flag(self):
        """标记当前题目为待修改"""
        if not self.questions:
            return
        q = self.questions[self.current_idx]
        bank = self.app.selected_bank
        from tkinter import simpledialog
        reason = simpledialog.askstring("标记", "输入标记原因（可选）：", parent=self)
        if reason is None:  # 用户取消
            return
        if add_to_bank_flagged(bank['path'], q['id'], q['type'], reason):
            messagebox.showinfo("成功", "已标记题目")
        else:
            messagebox.showinfo("提示", "题目已被标记")

    def _save_progress(self):
        """保存当前刷题进度"""
        bank = self.app.selected_bank
        if not bank or not self.questions:
            return

        # 判断题型
        types = set(q['type'] for q in self.questions)
        if types == {'single'}:
            question_type = 'single'
        elif types == {'multi'}:
            question_type = 'multi'
        else:
            question_type = 'all'

        progress = {
            'bank_name': bank['name'],
            'mode': self.app.quiz_mode,
            'question_type': question_type,
            'total_questions': len(self.questions),
            'current_idx': self.current_idx,
            'correct_count': self.correct_count,
            'wrong_questions': [{'id': q['id'], 'type': q['type']} for q in self.wrong_questions],
            'question_order': getattr(self, '_shuffle_order', None),
            'answers': list(self.answers.values()),
            'saved_at': datetime.now().isoformat()
        }
        save_quiz_progress(bank['path'], progress)

    def _save_and_go_back(self):
        """保存进度并返回操作页"""
        if self.current_idx < len(self.questions):
            self._save_progress()
        self.app.show_page('operations')

    # --- 快捷键处理 ---

    def _on_return(self, event):
        """Enter 键"""
        if self.current_idx in self.answers or self.answered:
            self._next()
        else:
            self._submit()

    def _on_space(self, event):
        """空格键"""
        if self.answered:
            self._next()

    def _on_escape(self, event):
        """Escape 键保存进度并返回"""
        if self.current_idx < len(self.questions):
            self._save_progress()
        self.app.show_page('operations')

    def _on_f(self, event):
        """F 键标记题目"""
        self._flag()
