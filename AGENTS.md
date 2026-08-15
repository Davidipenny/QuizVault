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
Desktop startup automatically imports detected or bundled `banks` content into SQLite. Keep this import idempotent and do not add a manual legacy-migration UI.

## Commands

```powershell
./scripts/setup.ps1
./scripts/dev.ps1
cd server; ../.venv/Scripts/python -m pytest tests -v
cd web; pnpm test; pnpm build
cd web; pnpm run test:e2e:install
cd web; pnpm test:e2e
.venv/Scripts/python -m PyInstaller --noconfirm desktop.spec
./scripts/build-installer.ps1; ./scripts/validate-installer.ps1
```

Update `README.md`, `docs/FORMAT.md`, and tests with behavioral changes.

Application startup must call Alembic through `app.database.run_migrations`; do not restore `Base.metadata.create_all()` as the upgrade path. Backup and restore behavior belongs in `app.backups`, and request payloads belong in strict models in `app.schemas`. Browser and packaged smoke tests must set `QUIZVAULT_DATA_DIR` to a unique temporary directory.
