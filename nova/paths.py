from __future__ import annotations
import os
from pathlib import Path

# Prosjektrot
ROOT = Path(os.getenv("NOVA_HOME", os.getenv("NOVA_HOME","/home/nova/nova-bot"))).resolve()

# Standard underkataloger
DATA    = (ROOT / "data")
LOGS    = (ROOT / "logs")
CONFIG  = (ROOT / "config")
EXPORTS = (ROOT / "exports")
TMP     = (ROOT / "tmp")

def ensure_dirs() -> None:
    for d in (DATA, LOGS, CONFIG, EXPORTS, TMP):
        d.mkdir(parents=True, exist_ok=True)
