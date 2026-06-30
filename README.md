# QuizVault — 选择题练习工具

交互式刷题程序，适用于各学科选择题复习。支持终端版和 GUI 版两种界面，提供错题本、收藏夹、标记等功能。

## 快速开始

### 1. 安装依赖

Python 3.6+ 即可运行，无强制外部依赖。安装 PyYAML 可获得更好的 YAML 格式支持（不安装则自动使用 JSON 格式）：

```bash
pip install pyyaml  # 可选
```

### 2. 导入题库

```bash
# 从 Markdown 文件导入
python import_questions.py import 毛概选择题（含解析）.md

# 从目录批量导入所有 .md 文件
python import_questions.py import --dir 题库/
```

导入时自动完成格式校验和去重，重复题目默认跳过。

### 3. 开始刷题

```bash
# 终端版本
python quiz.py

# GUI 版本（图形界面）
python gui/main.py
```

启动后显示主菜单，选择练习模式即可：

```
╔══════════════════════════════════════════════╗
║            QuizVault 选择题刷题系统           ║
╠══════════════════════════════════════════════╣
║  题库：75 道（单选 50 / 多选 25）            ║
╠══════════════════════════════════════════════╣
║  1. 顺序刷题（单选题 50道）                  ║
║  2. 随机刷题（单选题 50道）                  ║
║  3. 顺序刷题（多选题 25道）                  ║
║  4. 随机刷题（多选题 25道）                  ║
║  5. 顺序刷题（全部 75道）                    ║
║  6. 随机刷题（全部 75道）                    ║
║  7. 错题回顾                                 ║
║  8. 处理标记题目                             ║
║  9. 批量删题                                 ║
║  0. 退出                                     ║
╚══════════════════════════════════════════════╝
```

答题时输入答案字母（单选如 `A`，多选如 `ABC`），输入 `F` 可标记题目为"待修改"，输入 `Q` 退出。

### 刷题进度自动保存

中途退出刷题（按 Q 或关闭窗口）时自动保存进度，下次进入同一模式时可选择继续上次或重新开始。进度文件保存在题库文件夹内（如 `banks/毛概往年题/quiz_progress.json`），答完全部题目后自动清除。

## 题库管理

### 导入题目

```bash
# 导入单个文件
python import_questions.py import 第一章.md

# 导入目录下所有 .md 文件
python import_questions.py import --dir 题库/

# 强制覆盖已有题目（默认跳过重复）
python import_questions.py import --force 新题目.md
```

### 校验题目格式

仅检查不导入，用于提前发现格式问题：

```bash
python import_questions.py validate 第一章.md
```

输出示例：
```
校验结果：50 题中 48 题通过，2 题有问题
  ✗ 题号 7：单选答案必须是 A-D 中的一个字母，当前为 "AB"
  ✗ 题号 19：选项不足 4 个，当前为 3 个
```

### 查看统计

```bash
python import_questions.py stats
```

显示题库总题数、单选/多选分布、标记题数、来源文件和最后更新时间。

### 处理标记题目

刷题时输入 `F` 可标记有疑问的题目。管理标记题目：

```bash
# 列出所有标记题目
python import_questions.py flagged

# 取消标记
python import_questions.py unflag --id 42
```

在主菜单选择【8】处理标记题目，可对每道标记题选择：

| 操作 | 说明 |
|------|------|
| E - 编辑 | 修改题型、答案、选项、解析，直接保存到源 .md 文件 |
| D - 删除 | 标记为已删除（不再显示） |
| C - 取消标记 | 移除标记，保留题目 |
| S - 跳过 | 暂不处理 |

### 批量删题

主菜单选择【9】进入批量删题模式，可快速清理不需要的题目。

**操作流程：**

1. 分页浏览所有题目（每页 20 题）
2. 输入题号切换选中/取消选中
3. 输入 `done` 确认删除，删除前二次确认
4. 删除的题目自动备份到 `deleted_questions.json`

**支持的输入：**

| 输入 | 示例 | 说明 |
|------|------|------|
| 题号 | `3` | 切换第 3 题的选中状态 |
| 范围 | `3-7` | 切换第 3 到第 7 题 |
| 混合 | `3-7,12,15-18` | 同时切换多个范围和单题 |
| `all` | | 选中当前页所有题目 |
| `none` | | 取消当前页所有选择 |
| `n` / `p` | | 翻页（下一页 / 上一页） |
| `done` | | 确认选择，进入删除确认 |
| `q` | | 取消，返回主菜单 |

### 导出题库

将题库导出为 Markdown 格式：

```bash
python import_questions.py export --output 导出题库.md
```

## 格式规范

题库使用 YAML 格式存储在 `questions.yaml` 中（未安装 PyYAML 时自动 fallback 到 `questions.json`）。

详细的格式规范见 [FORMAT.md](docs/FORMAT.md)，包括：

- **Markdown 导入格式**：章节标题区分题型、单题类型覆盖、题目各元素的格式要求
- **YAML 存储格式**：meta 字段、questions 字段的完整说明
- **校验规则**：必填字段、答案合法性、选项数量、去重策略

## AI 生成题目模板

将以下提示词粘贴给 AI，可生成符合导入格式的题目：

---

请按以下 Markdown 格式生成选择题：

````markdown
## 单选题

**1. 题目文本（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：A**

**解析：** 解析内容

---

## 多选题

**1. 题目文本（　）**
A. 选项A
B. 选项B
C. 选项C
D. 选项D

**答案：ABC**

**解析：** 解析内容

---

要求：
1. 单选题答案为 A-D 中的一个字母
2. 多选题答案为 2-4 个不重复的 A-D 字母
3. 每题必须有 4 个选项
4. 解析要说明正确答案的原因和其他选项的错误
5. 题号按顺序编号
6. 用 --- 分隔每道题
````

---

生成后保存为 `.md` 文件，用 `python import_questions.py import 文件名.md` 导入即可。

## 常见问题

### Q: 终端显示乱码怎么办？

A: 请确保终端支持 UTF-8 编码。Windows 用户建议使用 Windows Terminal 或 PowerShell。

### Q: 颜色显示不出来怎么办？

A: 部分终端可能不支持 ANSI 颜色。建议使用 Windows Terminal、PowerShell 或 Git Bash。

### Q: 如何重置错题本？

A: 删除 `wrong_questions.json` 文件即可。

### Q: 如何添加更多题目？

A: 两种方式：

1. **手动编写**：按 [FORMAT.md](docs/FORMAT.md) 中的 Markdown 格式编写题目，保存为 `.md` 文件后导入
2. **AI 生成**：将上方的提示词粘贴给 AI，生成后保存导入

### Q: 导入时提示"重复题目"怎么办？

A: 题目基于内容哈希去重。如需强制覆盖，使用 `--force` 参数：

```bash
python import_questions.py import --force 新题目.md
```

### Q: 如何恢复误删的题目？

A: 批量删除的题目会自动备份到 `deleted_questions.json`，包含完整的题目信息和删除时间。可手动查看该文件找回题目，或等待后续版本的自动恢复功能。

### Q: 刷题进度保存在哪里？

A: 进度文件保存在题库文件夹内，如 `banks/毛概往年题/quiz_progress.json`。中途退出时自动保存，下次进入同一刷题模式时会提示是否继续。答完全部题目后进度文件自动清除。

### Q: 如何将题库从 YAML 切换到 JSON？

A: 删除 `questions.yaml`，确保不安装 PyYAML，程序会自动使用 `questions.json`。可先导出再重新导入：

```bash
python import_questions.py export --output 备份.md
del questions.yaml
python import_questions.py import 备份.md
```

## 文件夹题库管理

题库存放在 `banks/` 文件夹下，每个子文件夹代表一个题库：

```
banks/
├── 毛概/
│   └── 毛概选择题.md
├── 马原/
│   └── 题库.md
├── 马克思/
│   ├── 第一章.md
│   └── 第二章.json
```

- 支持 `.md` 和 `.json` 格式
- 同一文件夹下的多个文件会自动合并成一个题库
- 启动时自动扫描 `banks/` 下的所有子文件夹
- 错题本和收藏夹按题库隔离，保存在各自题库文件夹内（`wrong_questions.json`、`collections.json`）

### 添加新题库

1. 在 `banks/` 下新建一个文件夹（如 `banks/马原/`）
2. 将 `.md` 或 `.json` 格式的题目文件放入该文件夹
3. 重新启动 `python quiz.py`，新题库会自动出现在选择菜单中

## 文件说明

| 文件 | 说明 |
|------|------|
| `quiz.py` | 终端版主程序（刷题、错题本、标记处理） |
| `gui/main.py` | GUI 版主程序（图形界面） |
| `gui/pages/` | GUI 页面模块（选择题库、刷题、结果、错题本等） |
| `gui/widgets/` | GUI 可复用组件（题目卡片等） |
| `bank_manager.py` | 文件夹题库扫描和管理模块 |
| `questions.yaml` | 题库数据文件（YAML 格式，旧模式） |
| `import_questions.py` | 题库导入、校验、统计、导出工具 |
| `parse_markdown.py` | Markdown 解析器 |
| `quiz.spec` | 终端版 PyInstaller 打包配置 |
| `gui.spec` | GUI 版 PyInstaller 打包配置 |
| `docs/FORMAT.md` | 题库格式规范文档 |
| `wrong_questions.json` | 错题本（运行后自动生成） |
| `deleted_questions.json` | 已删除题目备份（批量删题后自动生成） |
| `quiz_progress.json` | 刷题进度（中途退出时自动生成，答完自动清除） |
| `test_quiz.py` | 主程序测试 |
| `test_bank_manager.py` | 题库管理模块测试 |
| `test_import_questions.py` | 导入工具测试 |
| `test_parse_markdown.py` | 解析器测试 |

## 运行测试

```bash
python -m pytest test_quiz.py test_bank_manager.py -v
python -m pytest test_import_questions.py -v
python -m pytest test_parse_markdown.py -v
```

## 许可证

仅供学习使用。
