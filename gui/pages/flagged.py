#!/usr/bin/env python3
"""标记题目页"""

import re
import tkinter as tk
from tkinter import messagebox, simpledialog
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from bank_manager import load_bank_flagged, remove_from_bank_flagged, add_to_bank_deleted


class EditDialog(tk.Toplevel):
    """编辑题目对话框"""

    def __init__(self, parent, question, app=None):
        super().__init__(parent)
        self.app = app
        self.question = question
        self.result = None
        self.title("编辑题目")
        self.geometry("500x400")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.wait_window()

    def _font(self, base_size):
        if self.app and hasattr(self.app, 'get_font'):
            return self.app.get_font(base_size)
        return ("Microsoft YaHei", base_size)

    def _build_ui(self):
        # 题目信息
        info_frame = tk.Frame(self)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        qtype = "单选" if self.question['type'] == 'single' else "多选"
        tk.Label(info_frame, text=f"[{qtype}] {self.question['question'][:50]}...",
                 font=self._font(10), wraplength=480).pack(anchor=tk.W)

        # 题型选择
        type_frame = tk.Frame(self)
        type_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(type_frame, text="题型：", font=self._font(10)).pack(side=tk.LEFT)
        self.type_var = tk.StringVar(value=self.question['type'])
        tk.Radiobutton(type_frame, text="单选", variable=self.type_var, value="single",
                       font=self._font(10)).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(type_frame, text="多选", variable=self.type_var, value="multi",
                       font=self._font(10)).pack(side=tk.LEFT, padx=10)

        # 答案
        ans_frame = tk.Frame(self)
        ans_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(ans_frame, text="答案：", font=self._font(10)).pack(side=tk.LEFT)
        self.answer_var = tk.StringVar(value=self.question['answer'])
        tk.Entry(ans_frame, textvariable=self.answer_var, width=10,
                 font=self._font(10)).pack(side=tk.LEFT, padx=5)

        # 选项
        opt_frame = tk.LabelFrame(self, text="选项", font=self._font(10))
        opt_frame.pack(fill=tk.X, padx=10, pady=5)
        self.option_vars = {}
        options = self.question.get('options', {})
        if isinstance(options, dict):
            for letter in sorted(options.keys()):
                row = tk.Frame(opt_frame)
                row.pack(fill=tk.X, padx=5, pady=2)
                tk.Label(row, text=f"{letter}.", font=self._font(10), width=3).pack(side=tk.LEFT)
                var = tk.StringVar(value=options[letter])
                self.option_vars[letter] = var
                tk.Entry(row, textvariable=var, font=self._font(10)).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 解析
        exp_frame = tk.LabelFrame(self, text="解析", font=self._font(10))
        exp_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.exp_text = tk.Text(exp_frame, height=4, font=self._font(10), wrap=tk.WORD)
        self.exp_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        exp = self.question.get('explanation', '')
        if exp:
            self.exp_text.insert('1.0', exp)

        # 按钮
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(btn_frame, text="保存", command=self._save, width=10).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="取消", command=self._cancel, width=10).pack(side=tk.RIGHT, padx=5)

    def _save(self):
        self.result = {
            'type': self.type_var.get(),
            'answer': self.answer_var.get().upper().strip(),
            'options': {k: v.get().strip() for k, v in self.option_vars.items()},
            'explanation': self.exp_text.get('1.0', tk.END).strip()
        }
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class FlaggedPage(tk.Frame):
    """标记题目页"""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.flagged = []
        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="标记题目", font=self.app.get_font(16, bold=True)).pack(pady=15)

        list_frame = tk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        self.listbox = tk.Listbox(list_frame, font=self.app.get_font(11), height=15)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="编辑", command=self._edit, width=10,
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="删除", command=self._delete, width=10,
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消标记", command=self._unflag, width=10,
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="返回", command=lambda: self.app.show_page('operations'), width=10,
                  font=self.app.get_font(10)).pack(side=tk.LEFT, padx=5)

    def refresh(self):
        bank = self.app.selected_bank
        data = load_bank_flagged(bank['path'])
        self.flagged = data.get('flagged', [])
        self.listbox.delete(0, tk.END)
        for i, qref in enumerate(self.flagged, 1):
            qtype = "单选" if qref['type'] == 'single' else "多选"
            reason = qref.get('reason', '无')
            self.listbox.insert(tk.END, f"{i}. [{qtype}] ID={qref['id']}  原因：{reason}")

    def _get_selected(self):
        """获取选中的题目"""
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一道题")
            return None
        idx = selection[0]
        return self.flagged[idx]

    def _find_question(self, q_id, q_type):
        """从当前题库中查找题目"""
        bank = self.app.selected_bank
        for q in bank.get('questions', []):
            if q['id'] == q_id and q['type'] == q_type:
                return q
        return None

    def _edit(self):
        """编辑题目"""
        qref = self._get_selected()
        if not qref:
            return

        q = self._find_question(qref['id'], qref['type'])
        if not q:
            messagebox.showwarning("提示", "题目已删除，无法编辑")
            return

        dialog = EditDialog(self, q, app=self.app)
        if dialog.result:
            # 更新源 .md 文件
            if self._save_to_md(q, dialog.result):
                bank = self.app.selected_bank
                remove_from_bank_flagged(bank['path'], qref['id'], qref['type'])
                messagebox.showinfo("成功", "已保存修改并取消标记")
                self.refresh()

    def _save_to_md(self, question, edits):
        """保存编辑到源 .md 文件"""
        bank = self.app.selected_bank
        source = question.get('source', '')
        if not source:
            messagebox.showwarning("提示", "无法确定题目来源文件")
            return False

        filepath = os.path.join(bank['path'], source)
        if not os.path.exists(filepath):
            messagebox.showwarning("提示", f"找不到源文件: {source}")
            return False

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except IOError as e:
            messagebox.showwarning("提示", f"无法读取文件: {e}")
            return False

        # 找到题目所在的块
        blocks = content.split('---')
        target_idx = None
        q_id = question['id']
        q_type = question['type']
        current_type = 'single'

        for i, block in enumerate(blocks):
            header_match = re.search(r'^#+\s*(.+)', block, re.MULTILINE)
            if header_match:
                header_text = header_match.group(1).strip().lower()
                if '单选' in header_text or 'single' in header_text:
                    current_type = 'single'
                elif '多选' in header_text or 'multiple' in header_text:
                    current_type = 'multi'

            if '<!-- single -->' in block:
                current_type = 'single'
            elif '<!-- multi -->' in block:
                current_type = 'multi'

            question_match = re.search(r'\*\*(\d+)\.\s*(.+?)（\s*）.*?\*\*', block)
            if question_match:
                block_id = int(question_match.group(1))
                if block_id == q_id and current_type == q_type:
                    target_idx = i
                    break

        if target_idx is None:
            messagebox.showwarning("提示", "在源文件中找不到该题目")
            return False

        block = blocks[target_idx]

        # 更新题型
        new_type = edits.get('type')
        if new_type and new_type != question['type']:
            if new_type == 'single':
                if '<!-- multi -->' in block:
                    block = block.replace('<!-- multi -->', '<!-- single -->')
                elif '<!-- single -->' not in block:
                    block = '<!-- single -->\n' + block
            elif new_type == 'multi':
                if '<!-- single -->' in block:
                    block = block.replace('<!-- single -->', '<!-- multi -->')
                elif '<!-- multi -->' not in block:
                    block = '<!-- multi -->\n' + block

        # 更新答案
        new_answer = edits['answer']
        if new_answer and new_answer != question['answer']:
            block = re.sub(r'\*\*答案：[A-D]+\*\*', f'**答案：{new_answer}**', block)

        # 更新选项
        for letter, new_text in edits['options'].items():
            old_text = question['options'].get(letter, '')
            if new_text and new_text != old_text:
                block = re.sub(rf'({letter}\.\s*).*', rf'\g<1>{new_text}', block, count=1)

        # 更新解析
        new_exp = edits['explanation']
        old_exp = question.get('explanation', '')
        if new_exp and new_exp != old_exp:
            if '**解析：**' in block:
                block = re.sub(r'\*\*解析：\*\*\s*.*', f'**解析：** {new_exp}', block, count=1)
            else:
                block = re.sub(r'(\*\*答案：[A-D]+\*\*)', f'\\1\n\n**解析：** {new_exp}', block)

        blocks[target_idx] = block
        new_content = '---'.join(blocks)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        except IOError as e:
            messagebox.showwarning("提示", f"保存失败: {e}")
            return False

    def _delete(self):
        """删除题目"""
        qref = self._get_selected()
        if not qref:
            return

        if messagebox.askyesno("确认", "确定要删除这道题吗？"):
            bank = self.app.selected_bank
            add_to_bank_deleted(bank['path'], qref['id'], qref['type'])
            remove_from_bank_flagged(bank['path'], qref['id'], qref['type'])
            messagebox.showinfo("成功", "已标记为删除")
            self.refresh()

    def _unflag(self):
        """取消标记"""
        qref = self._get_selected()
        if not qref:
            return

        bank = self.app.selected_bank
        remove_from_bank_flagged(bank['path'], qref['id'], qref['type'])
        self.refresh()
