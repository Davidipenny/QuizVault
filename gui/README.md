# QuizVault — GUI 版本

基于 tkinter 的桌面图形界面版本，复用终端版的全部业务逻辑。

## 运行

```bash
# 从项目根目录
python gui/main.py
```

## 打包

```bash
pyinstaller gui.spec
# 生成 dist/quiz_gui.exe
```

运行 exe 时需将 `banks/` 文件夹放在 exe 同级目录。

## 功能

- **题库选择** — 自动扫描 `banks/` 下所有题库
- **刷题模式** — 顺序/随机、单选/多选/全部
- **答题交互** — 单选按钮/复选框、提交后显示对错和解析、快捷键（A/B/C/D 选择，Enter 提交，Space 下一题，F 标记题目）
- **进度保存** — 中途退出（返回按钮/Esc）自动保存进度，下次进入可选择继续或重开
- **错题本** — 自动记录错题、答对自动移除、支持多个错题本
- **收藏夹** — 创建/删除/重命名收藏夹、收藏题目、导出为 Markdown
- **标记题目** — 标记有疑问的题目，支持编辑（修改题型/答案/选项/解析并保存到源文件）、删除、取消标记
- **批量删题** — 勾选式批量删除，确认后标记为已删除

## 文件结构

```
gui/
├── main.py              # 入口，窗口初始化，页面路由
├── pages/
│   ├── bank_select.py   # 题库选择页
│   ├── operations.py    # 操作选择页
│   ├── quiz.py          # 刷题页
│   ├── result.py        # 结算页
│   ├── wrong_book.py    # 错题本页
│   ├── collection.py    # 收藏夹页（列表 + 详情）
│   ├── flagged.py       # 标记题目页
│   └── batch_delete.py  # 批量删题页
└── widgets/
    └── question_card.py # 题目展示组件
```

## 依赖

零外部依赖，仅使用 Python 标准库（tkinter）。

## 与终端版的关系

- 两个版本并存，互不干扰
- 共享 `bank_manager.py` 和 `parse_markdown.py` 的业务逻辑
- 共享 `banks/` 文件夹中的题库数据
- 错题本、收藏夹等数据互通
