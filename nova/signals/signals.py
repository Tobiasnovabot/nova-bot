#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

from nova.indicators.indicators import ema, rsi, atr, vwap

# ---------- gates ----------
def _momentum_gate(df: pd.DataFrame, look=10, ret_thr=0.004, vol_mult=1.2) -> bool:
    if len(df) < look + 2: return False
    cl = df["close"]
    rets = cl.pct_change().fillna(0.0)
    vol = df["volume"].astype(float)
    vol_ok = vol.iloc[-1] > vol.rolling(look).mean().iloc[-1] * vol_mult
    mom_ok = (cl.iloc[-1] / cl.iloc[-look] - 1.0) > ret_thr
    return bool(mom_ok and vol_ok)

def _vwap_bias(df: pd.DataFrame) -> bool:
    vw = vwap(df)
    return bool(df["close"].iloc[-1] > vw.iloc[-1])

def _htf_filter(ctx: dict) -> bool:
    htf = ctx.get("htf_df")
    if htf is None or len(htf) < 30: return True
    e = ema(htf["close"], 30)
    return bool(htf["close"].iloc[-1] > e.iloc[-1])

def _ml_gate(ctx: dict, meta: dict) -> bool:
    score = float(ctx.get("ml_score", 0.6))
    thr = float(ctx.get("ml_threshold", 0.5))
    meta["ml_score"] = score
    meta["ml_threshold"] = thr
    return bool(score >= thr)

def _equity_ma_gate(ctx: dict) -> bool:
    return bool(ctx.get("equity_ma_up", True))

def _all_gates(df: pd.DataFrame, ctx: dict, meta: dict) -> bool:
    g = {
        "momentum": _momentum_gate(df),
        "vwap_bias": _vwap_bias(df),
        "htf": _htf_filter(ctx),
        "ml": _ml_gate(ctx, meta),
        "equity_ma": _equity_ma_gate(ctx),
    }
    meta["gates"] = g
    return all(g.values())

# ---------- strategies ----------
def strat_ema_rsi(df: pd.DataFrame, meta: dict) -> dict:
    if len(df) < 30: return {"entry": False, "exit": False}
    f, s = ema(df["close"], 12), ema(df["close"], 26)
    r = rsi(df["close"], 14)
    cross_up = f.iloc[-2] <= s.iloc[-2] and f.iloc[-1] > s.iloc[-1]
    cross_dn = f.iloc[-2] >= s.iloc[-2] and f.iloc[-1] < s.iloc[-1]
    return {
        "entry": bool(cross_up and r.iloc[-1] > 55),
        "exit": bool(cross_dn or r.iloc[-1] < 45),
    }

def strat_macd_bb(df: pd.DataFrame, meta: dict) -> dict:
    if len(df) < 40: return {"entry": False, "exit": False}
    ema12, ema26 = ema(df["close"], 12), ema(df["close"], 26)
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    m = df["close"].rolling(20).mean()
    sd = df["close"].rolling(20).std(ddof=0)
    mid = m
    entry = bool(macd.iloc[-1] > signal.iloc[-1] and df["close"].iloc[-1] > mid.iloc[-1])
    exit_ = bool(macd.iloc[-1] < signal.iloc[-1] or df["close"].iloc[-1] < mid.iloc[-1])
    return {"entry": entry, "exit": exit_}

def strat_brk_atr(df: pd.DataFrame, meta: dict, look=20, k=0.2) -> dict:
    if len(df) < look + 15: return {"entry": False, "exit": False}
    hh = df["high"].rolling(look).max()
    a = atr(df["high"], df["low"], df["close"], 14)
    c = df["close"]
    entry = bool(c.iloc[-1] > hh.iloc[-2] + k * a.iloc[-1])
    # exit: under 20-EMA eller -k*ATR under close
    e20 = ema(c, 20)
    exit_ = bool(c.iloc[-1] < e20.iloc[-1] or c.iloc[-1] < (c.iloc[-2] - k * a.iloc[-1]))
    return {"entry": entry, "exit": exit_}

STRATS = {
    "ema_rsi": strat_ema_rsi,
    "macd_bb": strat_macd_bb,
    "brk_atr": strat_brk_atr,
}

# ---------- dispatcher ----------
def build_signals(df: pd.DataFrame, ctx: dict) -> dict:
    """
    df: DataFrame med kolonner: open, high, low, close, volume
    ctx: kan inneholde htf_df, ml_score, ml_threshold, equity_ma_up
    return: {entry, exit, meta}
    """
    meta = {"chosen": None, "per_strat": {}}
    if not isinstance(df, pd.DataFrame) or len(df) < 30:
        return {"entry": False, "exit": False, "meta": {"err": "too_short"}}

    # gates
    if not _all_gates(df, ctx or {}, meta):
        return {"entry": False, "exit": False, "meta": meta}

    # evaluer strategier
    decisions = {}
    for name, fn in STRATS.items():
        out = fn(df, meta)
        decisions[name] = out
        meta["per_strat"][name] = out

    # valg: første som har entry; hvis ingen entry, velg exit dersom noen ber om exit
    chosen = None
    for name in ("ema_rsi", "macd_bb", "brk_atr"):
        if decisions[name]["entry"]:
            chosen = name
            break
    if chosen is None:
        for name in ("ema_rsi", "macd_bb", "brk_atr"):
            if decisions[name]["exit"]:
                chosen = name
                break

    meta["chosen"] = chosen
    entry = bool(chosen and decisions[chosen]["entry"])
    exit_ = bool(chosen and decisions[chosen]["exit"])
    return {"entry": entry, "exit": exit_, "meta": meta}
