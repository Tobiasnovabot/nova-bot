#!/usr/bin/env python3
from __future__ import annotations
from collections import deque
from time import time

_lat = deque(maxlen=50)
_err = deque(maxlen=50)
_open = False
_open_t = 0.0

def record_latency(sec: float) -> None: _lat.append(sec)
def record_error() -> None: _err.append(time())

def exchange_ok(thresh_ms: float = 800, err_rate: float = 0.20,
                cool_sec: int = 90) -> bool:
    """
    Steng entries midlertidig hvis latens er høy og/eller feilrate høy.
    """
    global _open, _open_t
    now = time()
    lat_bad = [x for x in _lat if x*1000 > thresh_ms]
    err_bad = [e for e in _err if now - e < 120]
    rate = (len(err_bad) / max(1,len(_err))) if _err else 0.0

    if (_open and now - _open_t < cool_sec):
        return False  # fortsatt stengt

    if len(lat_bad) >= 5 or rate >= err_rate:
        _open = True; _open_t = now
        return False
    _open = False
    return True