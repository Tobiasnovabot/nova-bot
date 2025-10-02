#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

def _to_series(x):
    if isinstance(x, pd.Series): return x.astype(float)
    return pd.Series(np.asarray(x, dtype=float))

def ema(series, period=14):
    s = _to_series(series)
    return s.ewm(span=period, adjust=False).mean()

def rsi(close, period=14):
    c = _to_series(close)
    delta = c.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)
    # Wilder RMA
    roll_up = up.ewm(alpha=1/period, adjust=False).mean()
    roll_down = down.ewm(alpha=1/period, adjust=False).mean()
    # safe RS: hvis roll_down==0 og roll_up>0 -> RS=∞ -> RSI=100
    rs = roll_up / roll_down.replace(0.0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    # fyll spesialtilfeller eksplisitt
    zero_down = (roll_down <= 1e-12)
    rsi = rsi.where(~zero_down, 100.0)
    return rsi.fillna(0.0)

def atr(high, low, close, period=14):
    h = _to_series(high); l = _to_series(low); c = _to_series(close)
    prev_close = c.shift(1)
    tr = pd.concat([
        (h - l),
        (h - prev_close).abs(),
        (l - prev_close).abs()
    ], axis=1).max(axis=1)
    # Wilder ATR = RMA(TR, period)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    return atr

def adx(high, low, close, period=14):
    h = _to_series(high); l = _to_series(low); c = _to_series(close)
    up_move = h.diff()
    down_move = -l.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr = pd.concat([
        (h - l),
        (h - c.shift(1)).abs(),
        (l - c.shift(1)).abs()
    ], axis=1).max(axis=1)

    atr_rma = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=h.index).ewm(alpha=1/period, adjust=False).mean() / atr_rma
    minus_di = 100 * pd.Series(minus_dm, index=h.index).ewm(alpha=1/period, adjust=False).mean() / atr_rma

    dx = ( (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) ) * 100
    adx = dx.ewm(alpha=1/period, adjust=False).mean().fillna(0.0)
    return adx

def vwap(df_or_price, volume=None):
    """
    VWAP over tid.
    - Hvis df_or_price er DataFrame, forventer kolonner: high, low, close, volume
    - Ellers: df_or_price = price-serie og volume separat
    """
    if isinstance(df_or_price, (pd.DataFrame,)):
        df = df_or_price.copy()
        tp = (df["high"] + df["low"] + df["close"]) / 3.0
        vol = df["volume"].astype(float)
    else:
        price = _to_series(df_or_price)
        vol = _to_series(volume)
        tp = price
    pv = (tp * vol).cumsum()
    vv = vol.cumsum().replace(0, np.nan)
    return pv / vv
