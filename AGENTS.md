# AGENTS.md

## Project Overview

QuizVault v2 is a local Web desktop quiz application. It is independent from the sibling legacy Tkinter project.

## Architecture

- `web/`: Vue 3, TypeScript, Vite, Pinia, Vue Router, and Element Plus.
- `server/app/`: FastAPI API, SQLAlchemy 2 models, import and migration services.
- `server/alembic/`: SQLite schema migrations.
- `desktop.py`: pywebview launcher bound to `127.0.0.1` with a random port and temporary token.
- `%APPDATA%/QuizVault/`: runtime database and backups.

Question types are `single`, `multi`, `any`, `truefalse`, `fill`, and `essay`. Keep validation, normalization, fingerprints, and grading in `server/app/domain.py`.

Imports must retain the preview, row validation, deduplication, and atomic commit workflow. Legacy migration must never modify the sibling `QuizVault/banks/` source files.

## Commands

```powershell
./scripts/setup.ps1
./scripts/dev.ps1
cd server; ../.venv/Scripts/python -m pytest tests -v
cd web; pnpm test; pnpm build
.venv/Scripts/python -m PyInstaller --noconfirm desktop.spec
```

Update `README.md`, `docs/FORMAT.md`, and tests with behavioral changes.

