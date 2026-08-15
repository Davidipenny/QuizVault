# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
datas = [
    (str(root / "web" / "dist"), "web/dist"),
    (str(root / "server" / "alembic"), "server/alembic"),
    (str(root / "parse_markdown.py"), "."),
]

a = Analysis(
    ["desktop.py"],
    pathex=[str(root / "server")],
    binaries=[],
    datas=datas,
    hiddenimports=["uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto", "uvicorn.protocols.websockets.auto", "webview.platforms.edgechromium"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="QuizVault", console=False, icon=None)
