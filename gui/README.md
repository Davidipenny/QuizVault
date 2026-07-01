# GUI 版本 — 开发说明

基于 tkinter 的桌面图形界面，QuizVault 的唯一活跃版本。

## 运行

```bash
# 从项目根目录
python gui/main.py
```

## 打包

```bash
pyinstaller gui.spec
# 生成 dist/quiz_gui.exe（自带 banks/ 题库）
```

## 文件结构

```
gui/
├── main.py              # 入口，窗口初始化，页面路由
├── pages/
│   ├── bank_select.py   # 题库选择页
│   ├── operations.py    # 操作选择页（刷题/错题本/收藏夹等）
│   ├── quiz.py          # 刷题页
│   ├── result.py        # 结算页
│   ├── wrong_book.py    # 错题本页
│   ├── collection.py    # 收藏夹页（列表 + 详情）
│   ├── flagged.py       # 标记题目页
│   └── batch_delete.py  # 批量删题页
└── widgets/
    └── question_card.py # 题目展示组件（单选/复选/判断）
```

## 页面路由

`main.py` 中的 `App` 类管理页面切换：

```
bank_select → operations → quiz → result
                          → wrong_book
                          → collection
                          → flagged
                          → batch_delete
```

每个页面是一个 `tk.Frame` 子类，通过 `controller.show_frame(PageClass)` 切换。

## 题型支持

支持三种题型：

| 题型 | type 值 | 选项数量 | 答案格式 |
|------|---------|----------|----------|
| 判断题 | truefalse | 2 个 | A 或 B |
| 单选题 | single | 4 个 | A-D 中一个 |
| 多选题 | multi | 4 个 | 2-4 个不重复字母 |

## 快捷键

| 按键 | 功能 |
|------|------|
| A/B/C/D | 选择选项（判断题只响应 A/B） |
| Enter | 提交答案 |
| Space | 下一题 |
| F | 标记题目 |
| ←/→ | 上一题/下一题（回顾已答题目） |
| Esc | 返回上一页 |

## 依赖

零外部依赖，仅使用 Python 标准库（tkinter）。
