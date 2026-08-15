import importlib.util
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("quizvault_desktop", PROJECT_ROOT / "desktop.py")
assert SPEC and SPEC.loader
desktop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(desktop)


def test_uvicorn_config_without_console_streams(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    config = desktop.uvicorn_config(object(), 12345)

    assert config.log_config is None
    assert config.access_log is False
