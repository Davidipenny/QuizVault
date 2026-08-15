from __future__ import annotations

from contextlib import closing, contextmanager
import sqlite3

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import alembic_ini_path, alembic_script_dir, database_path


class Base(DeclarativeBase):
    pass


def make_engine(url: str | None = None):
    db_url = url or f"sqlite:///{database_path().as_posix()}"
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {},
        future=True,
    )
    if db_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _configure_sqlite(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
    return engine


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def run_migrations() -> None:
    path = database_path()
    configuration = Config(str(alembic_ini_path()))
    configuration.set_main_option("script_location", str(alembic_script_dir()))
    configuration.set_main_option("sqlalchemy.url", f"sqlite:///{path.as_posix()}")
    if path.exists():
        with closing(sqlite3.connect(path)) as connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "question_banks" in tables and "alembic_version" not in tables:
            command.stamp(configuration, "0001")
    command.upgrade(configuration, "head")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
