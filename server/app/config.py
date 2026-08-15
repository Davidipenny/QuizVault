from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "QuizVault"
API_PREFIX = "/api/v1"


def data_dir() -> Path:
    override = os.getenv("QUIZVAULT_DATA_DIR")
    if override:
        path = Path(override)
    elif os.name == "nt" and os.getenv("APPDATA"):
        path = Path(os.environ["APPDATA"]) / APP_NAME
    else:
        path = Path.home() / ".quizvault"
    path.mkdir(parents=True, exist_ok=True)
    (path / "backups").mkdir(exist_ok=True)
    return path


def database_path() -> Path:
    return data_dir() / "quizvault.db"


def application_root() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root)
    return Path(__file__).resolve().parents[2]


def frontend_dist_dir() -> Path:
    return application_root() / "web" / "dist"


def alembic_ini_path() -> Path:
    return application_root() / "server" / "alembic.ini"


def alembic_script_dir() -> Path:
    return application_root() / "server" / "alembic"


def legacy_banks_dir() -> Path:
    override = os.getenv("QUIZVAULT_LEGACY_BANKS")
    if override:
        return Path(override)
    project_root = application_root()
    candidates = [
        project_root / "banks",
        project_root.parent / "QuizVault" / "banks",
    ]
    return next((path for path in candidates if path.is_dir()), candidates[0])
