import sys

from app.config import application_root, frontend_dist_dir


def test_source_application_root():
    assert frontend_dist_dir() == application_root() / "web" / "dist"


def test_frozen_application_root(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert application_root() == tmp_path
    assert frontend_dist_dir() == tmp_path / "web" / "dist"
