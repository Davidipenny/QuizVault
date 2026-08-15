from __future__ import annotations

import base64
import json
import os
import secrets
import shutil
import socket
import sqlite3
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from contextlib import closing
from html.parser import HTMLParser
from pathlib import Path


def app_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def uvicorn_config(api_app: object, port: int):
    import uvicorn

    # Windowed PyInstaller executables have no stdout/stderr. Uvicorn's default
    # color formatter probes those streams with isatty() while configuring logs.
    return uvicorn.Config(
        api_app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        log_config=None,
        access_log=False,
    )


class StaticAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.paths: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attribute = "src" if tag == "script" else "href" if tag == "link" else None
        if not attribute:
            return
        value = dict(attrs).get(attribute)
        if value and value.startswith("/assets/"):
            self.paths.append(value)


def main() -> None:
    root = app_root()
    sys.path.insert(0, str(root / "server"))
    smoke_test = "--smoke-test" in sys.argv
    configured_smoke_dir = os.environ.get("QUIZVAULT_DATA_DIR") if smoke_test else None
    owns_smoke_dir = smoke_test and not configured_smoke_dir
    smoke_dir = Path(configured_smoke_dir) if configured_smoke_dir else (Path(tempfile.mkdtemp(prefix="QuizVault-smoke-")) if smoke_test else None)
    if smoke_dir:
        smoke_dir.mkdir(parents=True, exist_ok=True)
        os.environ["QUIZVAULT_DATA_DIR"] = str(smoke_dir)
    os.environ.setdefault("QUIZVAULT_ACCESS_TOKEN", secrets.token_urlsafe(32))
    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        legacy_candidates = [
            executable_dir / "banks",
            executable_dir.parent / "banks",
            executable_dir.parent.parent / "QuizVault" / "banks",
        ]
    else:
        legacy_candidates = [root / "banks", root.parent / "QuizVault" / "banks"]
    legacy_banks = next((path for path in legacy_candidates if path.is_dir()), legacy_candidates[0])
    os.environ.setdefault("QUIZVAULT_LEGACY_BANKS", str(legacy_banks))
    port = available_port()

    from app.main import app as api_app
    import uvicorn

    config = uvicorn_config(api_app, port)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="quizvault-api", daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    if not server.started:
        raise RuntimeError("QuizVault 本地服务启动失败")

    token = os.environ["QUIZVAULT_ACCESS_TOKEN"]
    if smoke_test:
        try:
            def request(path: str, method: str = "GET", payload: dict | None = None):
                body = json.dumps(payload).encode("utf-8") if payload is not None else None
                headers = {"X-QuizVault-Token": token}
                if body is not None:
                    headers["Content-Type"] = "application/json"
                api_request = urllib.request.Request(
                    f"http://127.0.0.1:{port}{path}", data=body, headers=headers, method=method,
                )
                return urllib.request.urlopen(api_request, timeout=10).read()

            home = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=10).read()
            assets = StaticAssetParser()
            assets.feed(home.decode("utf-8"))
            asset_content = urllib.request.urlopen(f"http://127.0.0.1:{port}{assets.paths[0]}", timeout=10).read() if assets.paths else b""
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/health", timeout=10)
                raise RuntimeError("未认证请求未被拒绝")
            except urllib.error.HTTPError as exc:
                if exc.code != 401:
                    raise
            health = json.loads(request("/api/v1/health"))
            banks = json.loads(request("/api/v1/banks"))
            persisted = any(bank.get("name") == "__smoke_persistence__" for bank in banks)
            if os.environ.get("QUIZVAULT_SMOKE_EXPECT_EXISTING") == "1" and not persisted:
                raise RuntimeError("重启后未找到冒烟测试数据")
            if not persisted:
                request("/api/v1/banks", "POST", {"name": "__smoke_persistence__"})

            backup = json.loads(request("/api/v1/backups", "POST"))
            backup_path = smoke_dir / "backups" / backup["filename"]
            with closing(sqlite3.connect(backup_path)) as connection:
                quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            restored = json.loads(request("/api/v1/backups/restore", "POST", {
                "content": base64.b64encode(backup_path.read_bytes()).decode("ascii"),
            }))
            post_restore_banks = json.loads(request("/api/v1/banks"))
            if b'<div id="app"></div>' not in home or not asset_content or health.get("status") != "ok" or quick_check != "ok" or not {"questions", "alembic_version"}.issubset(tables):
                raise RuntimeError("QuizVault 打包资源冒烟检查失败")
            if not restored.get("restored") or not any(bank.get("name") == "__smoke_persistence__" for bank in post_restore_banks):
                raise RuntimeError("QuizVault 备份恢复冒烟检查失败")
        finally:
            server.should_exit = True
            thread.join(timeout=5)
            from app.database import engine
            engine.dispose()
            if owns_smoke_dir:
                shutil.rmtree(smoke_dir, ignore_errors=True)
        return

    import webview

    webview.create_window("QuizVault", f"http://127.0.0.1:{port}/?token={token}", width=1280, height=820, min_size=(900, 620))
    try:
        webview.start(gui="edgechromium", debug=False)
    finally:
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
