#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
import math
from typing import Dict, Any, List, Optional

import pandas as pd

# Standardparametere for trailing/TP
DEFAULTS: Dict[str, Any] = {
    "trail_k": 1.5,            # ATR-mult for trail
    "trail_k_add": 1.2,        # strammere trail ved pyramidering
    "arm_atr": 0.5,            # arm trail etter X*ATR i pluss
    "be_arm_atr": 1.0,         # arm break-even etter X*ATR
    "use_close_for_trail": True,
    "min_trail_bps": 5.0,      # min trail-avstand i bps av pris
    "debounce_bps": 2.0,       # filtrer små sving
    "struct_look": 10,         # lookback for struktur-low/high
    "chandelier_k": 3.0,       # chandelier-k * ATR
    "tp_R": [1.0, 2.0],        # R-multipler for partial TPs
    "tp_frac": [0.5, 0.5],     # fraksjoner for partials
    "time_stop_bars": 100,     # enkel stagnasjons-sjekk
    "add_atr": [1.0, 2.0],     # pyramidering-nivåer i ATR
}

# ---------- helpers ----------

def _p(ctx: Dict[str, Any], key: str) -> Any:
    return (ctx.get("params") or {}).get(key, DEFAULTS[key])

def _compute_atr(df: pd.DataFrame, period: int = 14) -> float:
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1.0/period, adjust=False).mean()
    return float(atr.iloc[-1])

def _last_price(df: pd.DataFrame, use_close: bool) -> float:
    if use_close:
        return float(df["close"].iloc[-1])
    # wick-beskyttelse: bruk midt av HL
    return float((df["high"].iloc[-1] + df["low"].iloc[-1]) * 0.5)

def _roll_hh(df: pd.DataFrame, look: int) -> float:
    look = max(1, int(look))
    return float(df["high"].iloc[-look:].max())

def _roll_ll(df: pd.DataFrame, look: int) -> float:
    look = max(1, int(look))
    return float(df["low"].iloc[-look:].min())

def _initial_r(entry: float, trail_k: float, atr_val: float) -> float:
    # grunn-R basert på trail-avstand ved entry
    return float(trail_k * atr_val)

def _be_floor(entry: float, armed: bool, price: float, be_arm_atr: float, atr_val: float,
              prev_be: bool) -> (float, bool):
    # break-even: når pris gått >= be_arm_atr*ATR i pluss, løft gulv til entry
    if prev_be or (armed and (price - entry) >= be_arm_atr * atr_val):
        return (entry, True)
    return (-math.inf, False)

def _apply_debounce(prev_stop: Optional[float], candidate: float, price: float, debounce_bps: float) -> float:
    if prev_stop is None:
        return candidate
    band = float(debounce_bps) / 10_000.0 * price
    # bare aksepter hvis flytting er større enn terskel
    if abs(candidate - prev_stop) >= band:
        return candidate
    return prev_stop

def _add_levels(entry: float, atr_val: float, add_atr: List[float], side: str = "long") -> List[float]:
    if side == "short":
        return [float(entry - a * atr_val) for a in add_atr]
    return [float(entry + a * atr_val) for a in add_atr]

# ---------- main ----------

def compute_stop_take(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    ctx:
      side: 'long'|'short'
      entry: float  (hvis ikke gitt brukes 'price' som entry)
      price: float  (siste pris; valgfri)
      bars: pd.DataFrame med kolonner [high,low,close]
      atr: float|None
      prev_stop: float|None
      prev_be_armed: bool|None
      pyramided: int (0,1,2)
      params: dict med overstyringer av DEFAULTS
    return:
      {stop, tp, partials:[{px,frac}], meta:{...}}
    """
    side = (ctx.get("side") or "long").lower()
    if side not in ("long", "short"):
        side = "long"

    df = ctx.get("bars", None)
    # robust fallback: hvis bars mangler, returner trivielle nivåer fra price/entry/atr
    if not isinstance(df, pd.DataFrame) or df.empty or len(df) < 2:
        price = float(ctx.get("price") or ctx.get("entry") or 0.0)
        atr_val = float(ctx.get("atr") or 0.0)
        if price <= 0 or atr_val <= 0:
            return {"stop": None, "tp": None, "partials": [], "meta": {"err": "too_short"}}
        k_stop = 2.0; k_tp = 3.0
        if side == "long":
            return {
                "stop": max(0.0, price - k_stop * atr_val),
                "tp": price + k_tp * atr_val,
                "partials": [{"px": price + 1.0 * atr_val, "frac": 0.5},
                             {"px": price + 2.0 * atr_val, "frac": 0.5}],
                "meta": {"fallback": True}
            }
        else:
            return {
                "stop": price + k_stop * atr_val,
                "tp": max(0.0, price - k_tp * atr_val),
                "partials": [{"px": price - 1.0 * atr_val, "frac": 0.5},
                             {"px": price - 2.0 * atr_val, "frac": 0.5}],
                "meta": {"fallback": True}
            }

    # fully featured path
    entry = float(ctx.get("entry") or ctx.get("price") or float(df["close"].iloc[-1]))
    prev_stop = ctx.get("prev_stop")
    prev_be = bool(ctx.get("prev_be_armed", False))
    pyramided = int(ctx.get("pyramided", 0))

    atr_val = float(ctx.get("atr") or _compute_atr(df, 14))
    trail_k = float(_p(ctx, "trail_k"))
    if pyramided > 0:
        trail_k = float(_p(ctx, "trail_k_add"))

    arm_atr = float(_p(ctx, "arm_atr"))
    be_arm_atr = float(_p(ctx, "be_arm_atr"))
    use_close = bool(_p(ctx, "use_close_for_trail"))
    min_trail_bps = float(_p(ctx, "min_trail_bps"))
    debounce_bps = float(_p(ctx, "debounce_bps"))
    struct_look = int(_p(ctx, "struct_look"))
    chand_k = float(_p(ctx, "chandelier_k"))

    price = _last_price(df, use_close)
    armed = price >= entry + arm_atr * atr_val if side == "long" else entry - arm_atr * atr_val >= price

    # initial R
    R = _initial_r(entry, trail_k, atr_val)

    # base trail
    if side == "long":
        base_trail = price - trail_k * atr_val
    else:
        base_trail = price + trail_k * atr_val

    # min trail-avstand
    min_dist = min_trail_bps / 10_000.0 * price
    if side == "long":
        base_trail = min(base_trail, price - min_dist)
    else:
        base_trail = max(base_trail, price + min_dist)

    # struktur + chandelier
    hh = _roll_hh(df, struct_look)
    ll = _roll_ll(df, struct_look)
    if side == "long":
        chand = hh - chand_k * atr_val
    else:
        chand = ll + chand_k * atr_val  # speilet for short

    # break-even gulv
    be_floor, be_armed = _be_floor(entry, armed, price, be_arm_atr, atr_val, prev_be)

    # kandidat
    if side == "long":
        floor = max(ll, chand, be_floor)
        candidate = max(base_trail, floor)
    else:
        ceil = min(hh, chand, be_floor if be_floor != -math.inf else hh)
        candidate = min(base_trail, ceil)

    # debounce + monotoni
    stop = _apply_debounce(prev_stop, candidate, price, debounce_bps)
    if prev_stop is not None:
        if side == "long":
            stop = max(prev_stop, stop)
        else:
            stop = min(prev_stop, stop)

    # partial TP ladder
    tp_R = list(_p(ctx, "tp_R"))
    tp_frac = list(_p(ctx, "tp_frac"))
    if side == "long":
        tp_levels = [entry + r * R for r in tp_R]
    else:
        tp_levels = [entry - r * R for r in tp_R]
    partials = [{"px": float(px), "frac": float(tp_frac[i] if i < len(tp_frac) else 0.0)}
                for i, px in enumerate(tp_levels)]
    tp = float(tp_levels[-1]) if tp_levels else None

    # time-stop enkel sjekk
    time_stop = False
    tmax = int(_p(ctx, "time_stop_bars"))
    if len(df) >= tmax:
        run_hh = _roll_hh(df, max(2, tmax // 2))
        if side == "long":
            time_stop = price < run_hh
        else:
            run_ll = _roll_ll(df, max(2, tmax // 2))
            time_stop = price > run_ll

    # pyramidering-nivåer
    adds = _add_levels(entry, atr_val, list(_p(ctx, "add_atr")), side=side)

    return {
        "stop": float(stop) if stop is not None else None,
        "tp": tp,
        "partials": partials,
        "meta": {
            "armed": bool(armed),
            "be_armed": bool(be_armed),
            "trail_k": trail_k,
            "atr": atr_val,
            "R": R,
            "struct_ll": ll,
            "struct_hh": hh,
            "chandelier": chand,
            "adds": adds,
            "time_stop": bool(time_stop),
        },
    }