# QuizVault v2

QuizVault v2 是独立于旧 Tkinter 版本的 Windows 本地刷题应用，使用 Vue 3、FastAPI 和 SQLite。支持单选、多选、任意选、判断、填空和问答六类题型。

## 直接使用

双击 `dist/QuizVault.exe`。应用数据和备份保存在 `%APPDATA%\QuizVault\`。

若同级旧项目中存在 `QuizVault/banks/`，应用启动时会自动、幂等地导入其中的题库，无需手动迁移；旧文件不会被修改。PyInstaller 构建时会将检测到的原 `banks` 一并打入 EXE，因此安装后也能直接识别这些题库。

数据库在每次启动时通过 Alembic 升级。备份使用 SQLite Online Backup API，包含 WAL 中已提交的数据；损坏备份会保留并标记为不可恢复。普通刷题不会在提交前返回答案，背题模式可显式查看答案，学习记录支持筛选未做题。

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
pnpm run test:e2e:install  # 首次运行安装 Chromium
pnpm test:e2e

cd ..
.venv/Scripts/python -m PyInstaller --noconfirm desktop.spec
./scripts/build-installer.ps1
./scripts/validate-installer.ps1
```

主要目录：

- `web/`：Vue 3 桌面界面。
- `server/`：FastAPI、SQLAlchemy、SQLite 和 Alembic。
- `desktop.py`：随机本地端口、临时访问令牌和 WebView2 启动器。
- `docs/`：题目格式与重构方案。
- `dist/QuizVault.exe`：可直接运行的 Windows 程序。

`build-installer.ps1` 要求 Inno Setup 6 和经过 SHA-256 校验的 WebView2 x64 离线安装程序。先运行 `scripts/fetch-webview2.ps1 -ExpectedSha256 <固定哈希>`，再构建安装包。完整 Windows 10/11 验收步骤见 `docs/WINDOWS-VALIDATION.md`。
