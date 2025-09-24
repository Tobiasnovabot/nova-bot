#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lockguard: fil-lås via fcntl. Hindrer flere instanser.
API:
  with single_instance("nova.lock"):
      ...
"""
import os
from pathlib import Path
from contextlib import contextmanager
import fcntl

try:
    from nova.core_boot.core_boot import NOVA_HOME
except Exception:
    NOVA_HOME = Path(os.getenv("NOVA_HOME", "/tmp/nova_home/nova")).resolve()

def lock_path(name: str = "nova.lock") -> Path:
    p = Path(name)
    return p if p.is_absolute() else (NOVA_HOME / name)

@contextmanager
def single_instance(name: str = "nova.lock"):
    lp = lock_path(name)
    lp.parent.mkdir(parents=True, exist_ok=True)
    f = open(lp, "a+")
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as e:
        f.close()
        raise RuntimeError(f"lockguard: already running (lock={lp})") from e
    try:
        f.seek(0); f.truncate(0); f.write(str(os.getpid())); f.flush()
        yield
    finally:
        try: fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception: pass
        try: f.close()
        except Exception: pass
