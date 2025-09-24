#!/usr/bin/env python3
from __future__ import annotations
import time, random, threading, collections, os
from typing import Any

class CircuitOpen(Exception): pass
_ERRS_PER_PATH: dict[str, collections.deque] = {}
_LOCK = threading.Lock()
def _now() -> float: return time.monotonic()
def _clean(dq: collections.deque, window: float) -> None:
    t = _now()
    while dq and (t - dq[0]) > window:
        dq.popleft()

def patch_ccxt(ex: Any) -> Any:
    rl_per_sec = float(os.getenv("NOVA_RL_PER_SEC", "10"))
    min_interval = 1.0 / max(rl_per_sec, 0.1)
    max_retries = int(os.getenv("NOVA_RETRIES", "3"))
    backoff_base = float(os.getenv("NOVA_BACKOFF_BASE", "0.4"))
    jitter = float(os.getenv("NOVA_BACKOFF_JITTER", "0.3"))
    err_window = float(os.getenv("NOVA_CIRCUIT_WINDOW", "60"))
    err_threshold = int(os.getenv("NOVA_CIRCUIT_ERRS", "6"))

    original_request = ex.request
    last_call: dict[str, float] = {}

    def guarded_request(path, api='public', method='GET', params={}, headers=None, body=None, config=None):
        tlast = last_call.get(path, 0.0)
        dt = _now() - tlast
        if dt < min_interval:
            time.sleep(min_interval - dt)
        last_call[path] = _now()

        with _LOCK:
            dq = _ERRS_PER_PATH.setdefault(path, collections.deque())
            _clean(dq, err_window)
            if len(dq) >= err_threshold:
                raise CircuitOpen(f"ccxt circuit OPEN for {path}")

        attempt = 0
        while True:
            try:
                return original_request(path, api, method, params, headers, body, config)
            except Exception:
                attempt += 1
                with _LOCK:
                    dq = _ERRS_PER_PATH.setdefault(path, collections.deque())
                    dq.append(_now()); _clean(dq, err_window)
                if attempt > max_retries:
                    raise
                time.sleep((backoff_base * (2 ** (attempt-1))) * (1.0 + random.random()*jitter))

    ex.request = guarded_request
    return ex