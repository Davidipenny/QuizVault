# AGENTS.md

## Project Overview

QuizVault v2 is a local Web desktop quiz application. It is independent from the sibling legacy Tkinter project.

GitHub: this workspace pushes to `Davidipenny/QuizVault` — `master` holds QuizVault v2, the `legacy` branch preserves the old Tkinter app. Releases carry the packaged `QuizVault.exe`; the bundled `banks/` content is the shared question-bank source (export from SQLite with `scripts/export_banks.py`).

## Architecture

- `web/`: Vue 3, TypeScript, Vite, Pinia, Vue Router, and Element Plus.
- `server/app/`: FastAPI API, SQLAlchemy 2 models, import and migration services.
- `server/alembic/`: SQLite schema migrations.
- `desktop.py`: pywebview launcher bound to `127.0.0.1` with a random port and temporary token.
- `%APPDATA%/QuizVault/`: runtime database and backups.
- `web/src/views/`: page components (Banks, Questions with a QuestionEditor drawer, Import, QuizSetup, Quiz, Study, Settings); routes live in `web/src/router.ts`.
- `scripts/e2e_server.py`: backend entry used by the Playwright e2e suite (`web/e2e/full-flow.spec.ts`).
- `parse_markdown.py`: CLI check for the legacy Markdown parser in `server/app/legacy_markdown.py`.

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

Environment notes for this machine: pnpm (installed globally via npm) manages the web toolchain. If pytest raises `PermissionError` creating `%TEMP%/pytest-of-david`, rerun with `--basetemp=<fresh dir> -p no:cacheprovider`. Git may flag this checkout as dubious ownership; use `git -c safe.directory=<path>` rather than editing global config. The Element Plus resolver runs with `importStyle: false` under Vitest because externalized node_modules cannot load injected CSS; `src/auto-imports.d.ts` and `src/components.d.ts` are plugin-generated but committed so `vue-tsc` works before the first dev/build run.

Update `README.md`, `docs/FORMAT.md`, and tests with behavioral changes.

Application startup must call Alembic through `app.database.run_migrations`; do not restore `Base.metadata.create_all()` as the upgrade path. Backup and restore behavior belongs in `app.backups`, and request payloads belong in strict models in `app.schemas`. Browser and packaged smoke tests must set `QUIZVAULT_DATA_DIR` to a unique temporary directory.

## Status (verified 2026-09-11)

The plan in `docs/plans/local-web-rebuild-improvement-plan.md` is implemented: SQLite Online Backup API and validated restore, Alembic startup migrations with baseline stamping, legacy migration plus automatic idempotent bank import, all six question types with `answer_meta`, recite mode, undone-question filter, strict Pydantic schemas, `import_errors` table, Playwright e2e spec, PyInstaller build (`dist/QuizVault.exe`), and Inno Setup installer validation scripts. Verified in this workspace: backend pytest 35/35, vitest 6/6, Playwright e2e 2/2 via `QV_E2E_CHANNEL=msedge`, `vue-tsc` + `vite build` clean, no TODO/FIXME markers.

The sibling legacy Tkinter project (`../QuizVault`) was deleted on 2026-09-11 after verifying all three banks (1187 questions) were imported into the production SQLite in `%APPDATA%/QuizVault/`. That database is now the single source of truth; the legacy auto-import code paths remain and degrade gracefully when no sibling directory exists. `dist/QuizVault.exe` was rebuilt with PyInstaller on 2026-09-11 (includes the Element Plus on-demand refactor) and passed the packaged `--smoke-test` twice with a unique temp `QUIZVAULT_DATA_DIR`; note the EXE no longer bundles `banks/` because the legacy source directory is gone.

Open items: the Playwright-managed Chromium is not downloaded, so the standard `pnpm run test:e2e` path needs `playwright install chromium` first (locally verified via the Edge channel instead); frontend unit tests are smoke-level only; the manual Windows 10/11 checklist in `docs/WINDOWS-VALIDATION.md` has no recorded sign-off; the cloud phase (PostgreSQL, auth, multi-user) is intentionally deferred per `docs/plans/local-web-rebuild-plan.md`. Element Plus is imported on demand through `unplugin-auto-import`/`unplugin-vue-components` in `vite.config.ts` — the main chunk is ~250 kB and EP components split into their own lazy chunks automatically.
