#!/usr/bin/env python3
from __future__ import annotations
import os, time, pathlib
_FLAG = os.getenv("CFG_RELOAD_FLAG", ".cfg_reload.flag")

def touch_reload_flag() -> str:
    pathlib.Path(_FLAG).write_text(str(time.time()))
    return _FLAG

def should_reload(last_ts: float) -> bool:
    try:
        ts = os.path.getmtime(_FLAG)
        return ts > last_ts
    except Exception:
        return False