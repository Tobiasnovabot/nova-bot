#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Selftest for exchange:
- Bygg både binance og okx i papermodus (uten keys).
- Hent markets og et par tick/ohlcv for BTC/USDT.
Exit 0 ved suksess.
"""
import sys
from pathlib import Path

try:
    from .exchange import build_exchange, ccxtx
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.exchange.exchange import build_exchange, ccxtx

SYMS = {
    "binance": "BTC/USDT",
    "okx":     "BTC/USDT",
}

def _probe(name: str) -> None:
    ex = build_exchange(name)
    mkts = ccxtx.fetch_markets(ex)
    assert isinstance(mkts, list) and len(mkts) > 0
    sym = SYMS[name]
    tkr = ccxtx.fetch_ticker(ex, sym)
    assert "symbol" in tkr and "last" in tkr
    candles = ccxtx.fetch_ohlcv(ex, sym, "1m", limit=5)
    assert isinstance(candles, list) and len(candles) > 0

def main() -> int:
    _probe("binance")
    _probe("okx")
    print("exchange selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
