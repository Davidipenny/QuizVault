# QuizVault v2

QuizVault v2 是 Windows 本地刷题应用，使用 Vue 3、FastAPI 和 SQLite，支持单选、多选、任意选、判断、填空、问答六类题型。数据全部存本机，断网可用。旧版（Tkinter）代码保留在 [legacy 分支](https://github.com/Davidipenny/QuizVault/tree/legacy)。

仓库自带三个毛课题库（共 1187 题，位于 `banks/`），应用首次启动时自动导入，也可以在"导入"页添加自己的题库。

## 使用方式一：下载 EXE（推荐普通用户）

到 [Releases](https://github.com/Davidipenny/QuizVault/releases/latest) 下载 `QuizVault.exe`，双击运行即可：

- 题库已内置，首次启动自动导入；
- 数据和自动备份保存在 `%APPDATA%\QuizVault\`，卸载或移动程序不影响数据；
- 无需安装 Python、Node 或任何运行时。

## 使用方式二：WebUI（源码运行）

需要 Python 3.13+ 和 Node.js（pnpm 管理前端依赖）：

```powershell
git clone https://github.com/Davidipenny/QuizVault.git
cd QuizVault-v2
./scripts/setup.ps1    # 创建虚拟环境并安装前后端依赖
./scripts/dev.ps1      # 启动 API(127.0.0.1:8000) 和前端(127.0.0.1:5173)
```

浏览器打开 `http://127.0.0.1:5173`。`banks/` 同样会在启动时自动导入。开发模式与 EXE 使用同一个数据库位置，看到的数据一致。

## 功能

- 题库中心：新建、编辑、删除、合并题库，题数统计
- 题目管理：分页、搜索、题型筛选、单题编辑、批量删除
- 导入：文本 / Excel / Word / AI JSON 四种来源，预览、行级校验、去重、事务提交，可下载错误报告
- 刷题：顺序/随机、选项乱序、背题模式（提交前可查看答案）、自动切题、答案比对、中断恢复
- 学习记录：错题本、收藏夹、笔记、标记、未做题筛选、正确率统计
- 数据安全：每次启动自动备份（SQLite Online Backup API）、手动备份与校验恢复、Alembic 启动迁移
- 夜间模式、答题字体调节

## 测试与构建

```powershell
cd server; ../.venv/Scripts/python -m pytest tests -v    # 后端测试
cd web; pnpm test                                        # 前端单元测试
cd web; pnpm test:e2e                                    # Playwright 全流程测试
cd web; pnpm build                                       # 类型检查 + 生产构建
.venv/Scripts/python -m PyInstaller --noconfirm desktop.spec   # 打包 EXE（会内置 banks/）
```

题目格式规范见 [docs/FORMAT.md](docs/FORMAT.md)，Windows 发布验收清单见 [docs/WINDOWS-VALIDATION.md](docs/WINDOWS-VALIDATION.md)。

## 目录结构

- `web/`：Vue 3 前端
- `server/`：FastAPI、SQLAlchemy、Alembic 迁移
- `banks/`：内置题库（旧版 JSON 格式，启动时自动导入，幂等）
- `desktop.py`：pywebview 桌面启动器（随机端口 + 临时访问令牌）
- `scripts/export_banks.py`：从数据库导出题库到 `banks/` 的维护脚本
