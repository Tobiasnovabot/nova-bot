#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
FLAG = Path("/home/nova/nova-bot/halt.flag")
def is_halted() -> bool: return FLAG.exists()
def halt_now() -> bool: FLAG.touch(exist_ok=True); return True
def resume() -> bool:
    if FLAG.exists(): FLAG.unlink()
    return True