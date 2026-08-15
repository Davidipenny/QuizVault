import sqlite3
from contextlib import closing

import pytest

from app.backups import backup_info, create_backup, restore_database, validate_database


def make_database(path, value="initial"):
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript(
            """
            CREATE TABLE question_banks (id TEXT PRIMARY KEY);
            CREATE TABLE questions (id TEXT PRIMARY KEY, prompt TEXT);
            CREATE TABLE quiz_sessions (id TEXT PRIMARY KEY);
            """
        )
        connection.execute("INSERT INTO questions VALUES ('q1', ?)", (value,))
        connection.commit()


def read_prompt(path):
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute("SELECT prompt FROM questions WHERE id='q1'").fetchone()[0]


def test_online_backup_includes_wal_data(tmp_path):
    database = tmp_path / "quizvault.db"
    backup_dir = tmp_path / "backups"
    make_database(database)

    writer = sqlite3.connect(database)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("UPDATE questions SET prompt='from-wal' WHERE id='q1'")
    writer.commit()
    try:
        backup = create_backup(database, backup_dir)
    finally:
        writer.close()

    assert validate_database(backup).valid
    assert read_prompt(backup) == "from-wal"


def test_invalid_backup_is_reported(tmp_path):
    broken = tmp_path / "broken.db"
    broken.write_bytes(b"not a sqlite database")

    info = backup_info(broken)
    assert info["valid"] is False
    assert info["validation_error"]


def test_restore_validates_before_preserving_and_replacing(tmp_path):
    database = tmp_path / "quizvault.db"
    backup_dir = tmp_path / "backups"
    incoming = tmp_path / "incoming.db"
    make_database(database, "current")
    make_database(incoming, "restored")

    safety = restore_database(incoming, database, backup_dir, lambda: None)

    assert read_prompt(database) == "restored"
    assert read_prompt(safety) == "current"


def test_invalid_restore_does_not_change_database(tmp_path):
    database = tmp_path / "quizvault.db"
    backup_dir = tmp_path / "backups"
    incoming = tmp_path / "incoming.db"
    make_database(database, "current")
    incoming.write_bytes(b"broken")

    with pytest.raises(ValueError):
        restore_database(incoming, database, backup_dir, lambda: None)

    assert read_prompt(database) == "current"
    assert not backup_dir.exists()
