from __future__ import annotations

import os
import json
import secrets
import socket
import sys
import tempfile
import threading
import time
import urllib.request
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


def main() -> None:
    root = app_root()
    sys.path.insert(0, str(root / "server"))
    smoke_test = "--smoke-test" in sys.argv
    if smoke_test:
        os.environ.setdefault("QUIZVAULT_DATA_DIR", str(Path(tempfile.gettempdir()) / "QuizVault-smoke"))
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
        home = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=10).read()
        health_request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/v1/health",
            headers={"X-QuizVault-Token": token},
        )
        health = json.loads(urllib.request.urlopen(health_request, timeout=10).read())
        if b'<div id="app"></div>' not in home or health.get("status") != "ok":
            raise RuntimeError("QuizVault 打包资源冒烟检查失败")
        server.should_exit = True
        thread.join(timeout=5)
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
