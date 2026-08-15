from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if "QUIZVAULT_DATA_DIR" not in os.environ:
    os.environ["QUIZVAULT_DATA_DIR"] = tempfile.mkdtemp(prefix="quizvault-e2e-")
os.environ["QUIZVAULT_ACCESS_TOKEN"] = "e2e-token"
sys.path.insert(0, str(ROOT / "server"))

import uvicorn


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8765, log_level="warning", access_log=False)
