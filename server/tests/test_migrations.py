import sqlite3

from sqlalchemy import create_engine

import app.database as database_module
from app.database import Base
from app import models  # noqa: F401


def revision(path):
    with sqlite3.connect(path) as connection:
        return connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]


def test_alembic_initializes_an_empty_database(monkeypatch, tmp_path):
    path = tmp_path / "empty.db"
    monkeypatch.setattr(database_module, "database_path", lambda: path)

    database_module.run_migrations()

    with sqlite3.connect(path) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"question_banks", "import_errors", "alembic_version"}.issubset(tables)
    assert revision(path) == "0002"


def test_alembic_stamps_and_upgrades_an_existing_unversioned_database(monkeypatch, tmp_path):
    path = tmp_path / "existing.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE import_errors")
    engine.dispose()
    monkeypatch.setattr(database_module, "database_path", lambda: path)

    database_module.run_migrations()

    assert revision(path) == "0002"
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='import_errors'").fetchone()
