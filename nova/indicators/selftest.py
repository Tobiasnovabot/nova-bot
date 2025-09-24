#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

from pathlib import Path
import sys

try:
    from .indicators import ema, rsi, atr, adx, vwap
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.indicators.indicators import ema, rsi, atr, adx, vwap

def _approx(a, b, tol=1e-6):
    return float(abs(a - b)) <= tol

def main() -> int:
    # Syntetiske priser 1..50
    n = 50
    close = pd.Series(np.arange(1, n+1, dtype=float))
    high  = close + 0.5
    low   = close - 0.5
    vol   = pd.Series(np.full(n, 10.0))

    # EMA test (p=3): verifiser mot manuell rekursjon
    p = 3
    alpha = 2/(p+1)
    ema_seq = ema(close, period=p)
    manual = []
    for i, x in enumerate(close):
        if i == 0:
            manual.append(x)
        else:
            manual.append(alpha*x + (1-alpha)*manual[-1])
    assert _approx(ema_seq.iloc[-1], manual[-1], 1e-9)

    # RSI: monotont stigende -> nær 100 etter oppvarming
    r = rsi(close, period=14)
    assert r.iloc[-1] > 99.0

    # ATR (Wilder): RMA starter lavt og konvergerer mot ~1.5 i denne konstruksjonen
    a = atr(high, low, close, period=14)
    val = a.iloc[30]
    assert 1.0 < val < 1.6, f"ATR utenfor forventet område: {val}"

    # ADX: jevn stigende trend → høy ADX-verdi
    ad = adx(high, low, close, period=14)
    assert ad.iloc[-1] > 50.0, f"ADX for lav, fikk {ad.iloc[-1]}"

    # VWAP: tp=(h+l+c)/3 = c; vol konstant → vwap = løpende snitt av close
    df = pd.DataFrame({"high":high, "low":low, "close":close, "volume":vol})
    vw = vwap(df)
    expected_last = close.expanding().mean().iloc[-1]
    assert _approx(vw.iloc[-1], expected_last, 1e-9)

    print("indicators selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
