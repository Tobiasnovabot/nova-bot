#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
from typing import Dict, Any

def suggest_alloc(strat_stats: Dict[str, Dict[str, float]], equity: float) -> Dict[str, float]:
    """
    strat_stats: {"ema_rsi":{"sharpe":1.0,"win":0.55}, ...}
    output: normaliserte vekter som summerer til 1.0
    """
    w = {}
    for k, v in strat_stats.items():
        s = max(0.0, float(v.get("sharpe", 0.0)))
        p = max(0.0, float(v.get("win", 0.5)) - 0.5)  # >0 hvis >50% hit
        w[k] = 1e-6 + s + 0.5*p
    tot = sum(w.values()) or 1.0
    return {k: v/tot for k, v in w.items()}

def per_trade_budget(equity: float, base_frac: float, weight: float) -> float:
    return float(equity) * float(base_frac) * float(max(0.0, weight))