#!/usr/bin/env python3
from __future__ import annotations
import os, json, tempfile, shutil
from pathlib import Path
from typing import Any, Dict

_BACKUPS = 5

def _atomic_write(p: Path, data: bytes) -> None:
    fd, tmppath = tempfile.mkstemp(prefix=p.name, dir=str(p.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmppath, p)
    finally:
        try: os.path.exists(tmppath) and os.remove(tmppath)
        except Exception: pass

def _rotate_backups(p: Path) -> None:
    for i in range(_BACKUPS-1, 0, -1):
        src = p.with_suffix(p.suffix + f".{i}")
        dst = p.with_suffix(p.suffix + f".{i+1}")
        if src.exists(): src.replace(dst)
    b1 = p.with_suffix(p.suffix + ".1")
    if p.exists(): shutil.copy2(p, b1)

def monkey_patch_stateio() -> bool:
    from nova.stateio import stateio as s
    def safe_save(state: Dict[str, Any], path: str | None = None) -> bool:
        p = Path(path or s.STATE_PATH)
        p.parent.mkdir(parents=True, exist_ok=True)
        _rotate_backups(p)
        payload = json.dumps(state, sort_keys=True, ensure_ascii=False, indent=2).encode("utf-8")
        _atomic_write(p, payload)
        return True
    s.save_state = safe_save
    return True