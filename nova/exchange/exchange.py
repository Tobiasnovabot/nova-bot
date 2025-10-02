#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
"""
exchange: kun Binance og OKX.
- build_exchange(ex_name=None): init ccxt exchange m/ timeouts, rateLimit, retries.
- norm_symbol(sym): identitet (kun spot, ingen XBT-mapping).
- ccxtx: wrappers med retry/backoff + enkel circuit-breaker per endpoint.
"""

import os, time, math
from typing import Any, Dict, List, Optional

import ccxt  # kreves

ALLOWED = {"binance", "okx"}

def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v is not None else default

def norm_symbol(sym: str) -> str:
    return sym  # ingen oversetting nødvendig for binance/okx spot

def _mk_cfg(ex_name: str) -> Dict[str, Any]:
    # felles konfig
    cfg: Dict[str, Any] = {
        "enableRateLimit": True,
        "timeout": int(_env("EX_TIMEOUT_MS", "10000")),  # 10s
        "options": {
            "adjustForTimeDifference": True,
        },
    }
    if ex_name == "binance":
        key = _env("BINANCE_API_KEY", "")
        sec = _env("BINANCE_API_SECRET", "")
        if key and sec:
            cfg.update({"apiKey": key, "secret": sec})
    elif ex_name == "okx":
        key = _env("OKX_API_KEY", "")
        sec = _env("OKX_API_SECRET", "")
        pph = _env("OKX_API_PASSPHRASE", "")
        if key and sec and pph:
            cfg.update({"apiKey": key, "secret": sec, "password": pph})
    return cfg

def build_exchange(ex_name: Optional[str] = None, **kwargs):
    mode = (kwargs.pop('mode', None) if 'kwargs' in locals() else None)
    name = (ex_name or _env("EXCHANGE", "binance")).lower()
    if name not in ALLOWED:
        raise ValueError(f"EXCHANGE må være en av {sorted(ALLOWED)}")
    cls = getattr(ccxt, name)
    ex = cls(_mk_cfg(name))
    # bruk spot by default
    if name == "okx":
        ex.options = {**getattr(ex, "options", {}), "defaultType": "spot"}
    return ex

# ----- circuit breaker + retry -----

_CB: Dict[str, Dict[str, Any]] = {}  # key -> {open:bool, until:ts, fail:count}
_CB_WINDOW_SEC = 30
_CB_FAIL_OPEN = 3

def _cb_key(ex, fn: str) -> str:
    return f"{ex.id}:{fn}"

def _cb_check(ex, fn: str):
    k = _cb_key(ex, fn)
    st = _CB.get(k)
    if st and st.get("open") and time.time() < st.get("until", 0):
        raise RuntimeError(f"circuit-open:{k}")

def _cb_fail(ex, fn: str):
    k = _cb_key(ex, fn)
    st = _CB.setdefault(k, {"open": False, "until": 0, "fail": 0})
    st["fail"] += 1
    if st["fail"] >= _CB_FAIL_OPEN:
        st["open"] = True
        st["until"] = time.time() + _CB_WINDOW_SEC

def _cb_ok(ex, fn: str):
    k = _cb_key(ex, fn)
    _CB[k] = {"open": False, "until": 0, "fail": 0}

def _retry_call(ex, fn_name: str, call, *args, **kwargs):
    _cb_check(ex, fn_name)
    max_tries = int(_env("EX_RETRIES", "4"))
    base = float(_env("EX_BACKOFF_BASE", "0.25"))  # sekunder
    for i in range(max_tries):
        try:
            res = call(*args, **kwargs)
            _cb_ok(ex, fn_name)
            return res
        except Exception as e:
            _cb_fail(ex, fn_name)
            if i == max_tries - 1:
                raise
            # eksponentiell backoff med jitter
            sleep_s = base * (2 ** i) * (1 + 0.1 * (i+1))
            time.sleep(min(sleep_s, 4.0))

class ccxtx:
    """Tynne wrappers over ccxt med retry + breaker."""
    @staticmethod
    def fetch_markets(ex) -> List[Dict[str, Any]]:
        return _retry_call(ex, "fetch_markets", ex.fetch_markets)

    @staticmethod
    def fetch_ohlcv(ex, symbol: str, timeframe: str = "1m", since: Optional[int] = None, limit: int = 500):
        # valider tidframes lett
        tf_ok = {"1m","5m","15m","1h","4h","1d"}
        if timeframe not in tf_ok:
            raise ValueError(f"Ugyldig timeframe {timeframe}, må være en av {sorted(tf_ok)}")
        symbol = norm_symbol(symbol)
        return _retry_call(ex, "fetch_ohlcv", ex.fetch_ohlcv, symbol, timeframe, since, limit)

    @staticmethod
    def fetch_ticker(ex, symbol: str):
        symbol = norm_symbol(symbol)
        return _retry_call(ex, "fetch_ticker", ex.fetch_ticker, symbol)