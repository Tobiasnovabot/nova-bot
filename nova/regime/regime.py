#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
import math
from typing import Dict, Any, Tuple
import pandas as pd

from nova.indicators.indicators import ema, rsi

def _realized_vol(close: pd.Series, look: int = 30) -> float:
    r = close.pct_change().dropna()
    if len(r) == 0:
        return 0.0
    v = float(r.rolling(look, min_periods=max(5, look//2)).std().iloc[-1] or 0.0)
    return v

def _ema_slope(close: pd.Series, span: int = 20, look: int = 5) -> float:
    e = ema(close, span)
    if len(e) < look + 1:
        return 0.0
    return float((e.iloc[-1] - e.iloc[-1-look]) / max(1e-12, e.iloc[-1-look]))

def detect_regime(btc_df: pd.DataFrame, eth_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Input DataFrames: kolonner minst ['close'], helst time/dag-bars.
    Returnerer: {'regime': 'bull'|'bear'|'chop', 'metrics': {...}}
    Heuristikk: EMA-slope(20), EMA(20 vs 50), RSI(14), realized vol.
    Konsensus mellom BTC og ETH.
    """
    def _metrics(df: pd.DataFrame) -> Dict[str, float]:
        c = pd.Series(df["close"], dtype=float)
        m = {
            "ema20_slope": _ema_slope(c, 20, 5),
            "ema_fast_above_slow": float(ema(c, 20).iloc[-1] > ema(c, 50).iloc[-1]),
            "rsi": float(rsi(c, 14).iloc[-1]),
            "rv": _realized_vol(c, 30),
        }
        return m

    b = _metrics(btc_df)
    e = _metrics(eth_df)

    # Score pr. aktivum
    def _score(m: Dict[str, float]) -> float:
        sc = 0.0
        sc += 1.0 if m["ema20_slope"] > 0.001 else (-1.0 if m["ema20_slope"] < -0.001 else 0.0)
        sc += 1.0 if m["ema_fast_above_slow"] > 0.5 else -1.0
        sc += 0.5 if m["rsi"] > 55 else (-0.5 if m["rsi"] < 45 else 0.0)
        return sc

    sb = _score(b)
    se = _score(e)
    avg = (sb + se) / 2.0

    # Volatilitet grense for chop
    rv_mean = (b["rv"] + e["rv"]) / 2.0
    chop_by_slope = abs(b["ema20_slope"]) < 0.0005 and abs(e["ema20_slope"]) < 0.0005
    chop_by_rsi = 45 <= b["rsi"] <= 55 and 45 <= e["rsi"] <= 55

    if avg >= 1.0 and not chop_by_slope:
        regime = "bull"
    elif avg <= -1.0 and not chop_by_slope:
        regime = "bear"
    else:
        regime = "chop"

    # hvis svært lav volatilitet → chop
    if rv_mean < 0.002:
        regime = "chop"

    return {
        "regime": regime,
        "metrics": {
            "btc": b, "eth": e,
            "score_btc": sb, "score_eth": se, "score_avg": avg,
            "rv_mean": rv_mean,
            "chop_flags": {"slope": chop_by_slope, "rsi": chop_by_rsi},
        },
    }

# ---------- Auto preset + intradag-multiplikator + breadth/VAR guard ----------

_PRESET_MAP = {
    "bull": "trend",
    "bear": "trend",
    "chop": "mean-revert",
}

def _intraday_multiplier(hour_local: int) -> float:
    # enkel time-of-day multiplikator (Oslo-tid føres inn eksternt)
    if 7 <= hour_local < 11:
        return 1.1
    if 11 <= hour_local < 17:
        return 1.0
    if 17 <= hour_local < 22:
        return 1.05
    return 0.8  # natt redusert

def auto_preset(regime_info: Dict[str, Any], *, hour_local: int, breadth_up_frac: float = 0.5, var_1h_pct: float = 1.0) -> Dict[str, Any]:
    """
    regime_info: output fra detect_regime()
    hour_local: 0..23
    breadth_up_frac: andel symbols i opptrend 0..1
    var_1h_pct: enkel VAR-proxy i %, f.eks. 99% VaR på 1 time
    Returnerer: {'preset': str, 'mult': float, 'allow': bool, 'why': str}
    """
    regime = regime_info.get("regime", "chop")
    preset = _PRESET_MAP[regime]
    mult = _intraday_multiplier(int(hour_local))

    # breadth guard: hvis svært smal bredde i bull, senk eller blokker
    allow = True
    why = ""
    if regime == "bull" and breadth_up_frac < 0.3:
        allow = False
        why = "narrow_breadth"
    # VAR guard: for høy 1h VAR blokkerer
    if var_1h_pct >= 3.0:
        allow = False
        why = "var_guard"

    return {"preset": preset, "mult": mult, "allow": allow, "why": why}