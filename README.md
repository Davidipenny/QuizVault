# QuizVault v2

QuizVault v2 是独立于旧 Tkinter 版本的 Windows 本地刷题应用，使用 Vue 3、FastAPI 和 SQLite。支持单选、多选、任意选、判断、填空和问答六类题型。

## 直接使用

双击 `dist/QuizVault.exe`。应用数据和备份保存在 `%APPDATA%\QuizVault\`。

若旧版位于同级目录 `QuizVault/`，迁移向导会自动读取 `../QuizVault/banks/`。进入“录题中心 -> 旧版迁移”，先扫描报告，再执行备份和迁移；旧文件不会被修改。

## 本地开发

```powershell
./scripts/setup.ps1
./scripts/dev.ps1
```

开发前端默认运行在 `http://127.0.0.1:5173`，API 监听 `127.0.0.1:8000`。

## 测试与构建

```powershell
cd server
../.venv/Scripts/python -m pytest tests -v

cd ../web
pnpm test
pnpm build

cd ..
.venv/Scripts/python -m PyInstaller --noconfirm desktop.spec
```

主要目录：

- `web/`：Vue 3 桌面界面。
- `server/`：FastAPI、SQLAlchemy、SQLite 和 Alembic。
- `desktop.py`：随机本地端口、临时访问令牌和 WebView2 启动器。
- `docs/`：题目格式与重构方案。
- `dist/QuizVault.exe`：可直接运行的 Windows 程序。

