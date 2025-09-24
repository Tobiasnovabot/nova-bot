#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
from typing import List, Dict, Any
import time
import pandas as pd

# Enkle cache-er + stats
_ticker_cache: Dict[str, Dict[str, Any]] = {}   # sym -> {"ts": epoch, "t": dict}
_ohlcv_cache: Dict[str, Dict[str, Any]] = {}    # key(sym,tf) -> {"ts": epoch, "df": pd.DataFrame}
_CACHE_TTL = {"ticker": 5.0, "ohlcv": 4.0}      # sekunder

CACHE_HITS = {"ticker": 0, "ohlcv": 0, "ticker_miss": 0, "ohlcv_miss": 0}

def set_params(*, ttl_ticker: float | None = None, ttl_ohlcv: float | None = None) -> None:
    """Tillat tests å tweake TTL-er."""
    global _CACHE_TTL
    if ttl_ticker is not None:
        _CACHE_TTL["ticker"] = float(ttl_ticker)
    if ttl_ohlcv is not None:
        _CACHE_TTL["ohlcv"] = float(ttl_ohlcv)

def _now() -> float:
    return time.time()

def _safe_float(t: dict, *keys: str, default: float = 0.0) -> float:
    for k in keys:
        v = t.get(k)
        if v is not None:
            try:
                return float(v)
            except Exception:
                pass
    return float(default)

def _ticker_key(sym: str) -> str:
    return sym.upper()

def _ohlcv_key(sym: str, tf: str) -> str:
    return f"{sym.upper()}::{tf}"

def last_price(ex, symbol: str) -> float:
    """Hent siste pris med liten cache."""
    key = _ticker_key(symbol)
    now = _now()
    cache = _ticker_cache.get(key)
    if cache and (now - float(cache["ts"])) <= _CACHE_TTL["ticker"]:
        CACHE_HITS["ticker"] += 1
        t = cache["t"]
    else:
        CACHE_HITS["ticker_miss"] += 1
        t = ex.fetch_ticker(symbol)
        _ticker_cache[key] = {"ts": now, "t": t}

    # prøv bid/ask/last/close i den rekkefølgen
    px = _safe_float(t, "bid", "ask", "last", "close", default=0.0)
    return px

def fetch_ohlcv(ex, symbol: str, timeframe: str = "1m", limit: int = 200) -> pd.DataFrame:
    """Pandas-innpakning for OHLCV + cache med kort TTL."""
    key = _ohlcv_key(symbol, timeframe)
    now = _now()
    cache = _ohlcv_cache.get(key)
    if cache and (now - float(cache["ts"])) <= _CACHE_TTL["ohlcv"]:
        CACHE_HITS["ohlcv"] += 1
        df = cache["df"]
        return df.copy()
    CACHE_HITS["ohlcv_miss"] += 1
    raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    # CCXT format: [ts, open, high, low, close, volume]
    df = pd.DataFrame(raw, columns=["ts","open","high","low","close","volume"])
    _ohlcv_cache[key] = {"ts": now, "df": df}
    return df.copy()

def last_candle_closed(df: pd.DataFrame) -> bool:
    """Enkel sjekk: minst 2 rader -> har én full-lukket bar."""
    try:
        return isinstance(df, pd.DataFrame) and len(df) >= 2
    except Exception:
        return False

def build_universe(ex, quotes: str = "USDT", dyn_top_n: int | None = None) -> List[str]:
    """
    Returner liste med symbols for valgt quote (spot). Hvis dyn_top_n er satt,
    sortér grovt etter volum/ticker og ta topp N. Fallback: kjerneliste.
    """
    quotes = quotes.upper()
    try:
        markets = ex.load_markets()
        syms = []
        # filtrer på spot og rett quote
        for m in markets.values():
            try:
                if not m.get("spot", True):
                    continue
                sym = m.get("symbol") or ""
                q = m.get("quote") or ""
                if q == quotes:
                    syms.append(sym)
            except Exception:
                continue

        # vol-sortering (best effort)
        scored: List[tuple[float, str]] = []
        for s in syms:
            try:
                t = ex.fetch_ticker(s)
                vol_usd = _safe_float(t, "quoteVolume", "baseVolume", default=0.0)
                px = _safe_float(t, "last", "close", "bid", "ask", default=0.0)
                # grovt anslag: bruker vol * pris hvis bare baseVolume er gitt
                if "baseVolume" in t and (vol_usd == 0.0 and px > 0):
                    vol_usd = float(t.get("baseVolume", 0.0)) * px
                scored.append((vol_usd, s))
            except Exception:
                scored.append((0.0, s))

        scored.sort(reverse=True, key=lambda x: float(x[0]))
        if dyn_top_n is not None and dyn_top_n > 0:
            scored = scored[:int(dyn_top_n)]
        return [s for _, s in scored] if scored else syms
    except Exception:
        # fallback kjerneliste
        core = ["BTC/USDT","ETH/USDT","BNB/USDT","SOL/USDT","XRP/USDT","ADA/USDT","DOGE/USDT","LINK/USDT","AVAX/USDT","TON/USDT"]
        return core[: int(dyn_top_n) ] if (dyn_top_n is not None and dyn_top_n > 0) else core
# --- Compat for selftests ---
# noen selftests forventer disse å eksistere i dette modulnavnet
try:
    CACHE_HITS
except NameError:
    CACHE_HITS = {"ohlcv": 0, "ticker": 0}

# enkel no-op/settbar TTL for tester
try:
    _CACHE_TTL
except NameError:
    _CACHE_TTL = {"ohlcv": 5, "ticker": 5}

def set_cache_ttl_defaults(ohlcv_sec: int = 5, ticker_sec: int = 5) -> None:
    global _CACHE_TTL
    _CACHE_TTL = {"ohlcv": int(ohlcv_sec), "ticker": int(ticker_sec)}