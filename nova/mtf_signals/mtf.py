#!/usr/bin/env python3
from __future__ import annotations
import pandas as pd

def htf_trend_filter(htf_df: pd.DataFrame, col: str="close", win:int=20) -> bool:
    if htf_df is None or len(htf_df) < 2:
        return False
    w = int(max(2, min(win, len(htf_df))))
    s = htf_df[col].tail(w)
    return bool(s.iloc[-1] > s.iloc[0])

def combine_mtf(l_tf_df: pd.DataFrame, h_tf_df: pd.DataFrame) -> dict:
    ok = htf_trend_filter(h_tf_df, "close", win=20)
    return {"entry_ok": bool(ok), "meta":{"htf_ok":bool(ok)}}