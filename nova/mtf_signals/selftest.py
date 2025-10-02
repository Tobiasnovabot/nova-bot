#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
from .mtf import htf_trend_filter, combine_mtf

def main()->int:
    # Lag en lengre stigende HTF-serie (>20) så det alltid blir True
    s = pd.Series(list(range(1, 40)))
    df = pd.DataFrame({"close": s})
    assert htf_trend_filter(df, "close", win=20) is True
    out = combine_mtf(df, df)
    assert out["entry_ok"] is True
    print("mtf_signals selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
