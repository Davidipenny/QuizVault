from __future__ import annotations

import os
import sqlite3
import tempfile
import threading
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


MAX_BACKUP_SIZE = 512 * 1024 * 1024
REQUIRED_TABLES = {"question_banks", "questions", "quiz_sessions"}
SUPPORTED_REVISIONS = {"0001", "0002"}
SQLITE_HEADER = b"SQLite format 3\x00"

_backup_lock = threading.RLock()


@dataclass(frozen=True)
class BackupValidation:
    valid: bool
    revision: str | None = None
    error: str | None = None


def validate_database(path: Path) -> BackupValidation:
    try:
        if not path.is_file() or path.stat().st_size < 100:
            return BackupValidation(False, error="备份文件为空或过小")
        with path.open("rb") as stream:
            if stream.read(len(SQLITE_HEADER)) != SQLITE_HEADER:
                return BackupValidation(False, error="SQLite 文件头无效")
        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            result = connection.execute("PRAGMA quick_check").fetchone()
            if not result or result[0] != "ok":
                return BackupValidation(False, error=f"数据库完整性检查失败：{result[0] if result else '无结果'}")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            missing = sorted(REQUIRED_TABLES - tables)
            if missing:
                return BackupValidation(False, error=f"缺少必要表：{', '.join(missing)}")
            revision = "unversioned"
            if "alembic_version" in tables:
                row = connection.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
                revision = str(row[0]) if row and row[0] else "unversioned"
                if revision not in SUPPORTED_REVISIONS:
                    return BackupValidation(False, revision=revision, error="数据库版本不受支持")
            return BackupValidation(True, revision=revision)
    except (OSError, sqlite3.DatabaseError) as exc:
        return BackupValidation(False, error=f"无法读取数据库：{exc}")


def _temporary_path(directory: Path, prefix: str) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=prefix, suffix=".db", dir=directory)
    os.close(descriptor)
    return Path(name)


def _online_copy(source_path: Path, destination_path: Path) -> None:
    with closing(sqlite3.connect(source_path)) as source, closing(sqlite3.connect(destination_path)) as destination:
        source.backup(destination)


def create_backup(database: Path, backup_dir: Path) -> Path:
    with _backup_lock:
        if not database.is_file():
            raise FileNotFoundError("活动数据库不存在")
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        destination = backup_dir / f"quizvault-{stamp}.db"
        temporary = _temporary_path(backup_dir, ".quizvault-backup-")
        try:
            _online_copy(database, temporary)
            validation = validate_database(temporary)
            if not validation.valid:
                raise ValueError(validation.error or "备份校验失败")
            os.replace(temporary, destination)
            return destination
        finally:
            temporary.unlink(missing_ok=True)


def backup_info(path: Path) -> dict:
    validation = validate_database(path)
    return {
        "filename": path.name,
        "size": path.stat().st_size,
        "created_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc),
        "valid": validation.valid,
        "validation_error": validation.error,
        "revision": validation.revision,
    }


def restore_database(
    uploaded: Path,
    database: Path,
    backup_dir: Path,
    dispose_connections: Callable[[], None],
) -> Path:
    with _backup_lock:
        validation = validate_database(uploaded)
        if not validation.valid:
            raise ValueError(validation.error or "不是有效的 QuizVault 备份")

        safety_backup = create_backup(database, backup_dir)
        replacement = _temporary_path(database.parent, ".quizvault-restore-")
        try:
            _online_copy(uploaded, replacement)
            copied_validation = validate_database(replacement)
            if not copied_validation.valid:
                raise ValueError(copied_validation.error or "恢复副本校验失败")
            dispose_connections()
            for suffix in ("-wal", "-shm"):
                Path(f"{database}{suffix}").unlink(missing_ok=True)
            os.replace(replacement, database)
            return safety_backup
        finally:
            replacement.unlink(missing_ok=True)
