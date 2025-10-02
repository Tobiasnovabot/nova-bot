#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
from typing import Dict, Tuple

# ---------- VIP tier beregning ----------

def vip_tier_distance(volume_30d: float, tiers: Dict[int, float]) -> Dict[str, float]:
    """
    volume_30d: 30-dagers trade-volum i USD.
    tiers: {tier_level: vol_threshold}
    Returnerer nåværende tier og hvor mye som mangler til neste.
    """
    cur_tier = 0
    next_tier = None
    for lvl, thresh in sorted(tiers.items()):
        if volume_30d >= thresh:
            cur_tier = lvl
        else:
            next_tier = (lvl, thresh)
            break
    missing = None
    if next_tier:
        missing = max(0.0, next_tier[1] - volume_30d)
    return {"cur_tier": cur_tier, "next": next_tier, "missing_usd": missing}

# ---------- Idle cash yield ----------

def idle_cash_yield(cash_usd: float, apy: float, days: int = 1) -> float:
    """
    Beregner forventet renteinntekt på idle cash.
    apy: annual percentage yield (f.eks. 0.05 = 5%).
    """
    return cash_usd * (apy/365.0) * days

# ---------- Turnover budsjett ----------

def turnover_budget(capital_usd: float, fric_bps: float, daily_bps_budget: float) -> Dict[str, float]:
    """
    Beregner hvor mye volum man kan omsette per dag gitt friksjon.
    capital_usd: tilgjengelig kapital
    fric_bps: antatt friksjon per trade (fees+slippage, i bps)
    daily_bps_budget: hvor mye av kapitalen man kan "bruke" i bps/dag
    """
    max_turnover = (capital_usd * daily_bps_budget / fric_bps) if fric_bps > 0 else float("inf")
    return {"max_turnover_usd": max_turnover, "fric_bps": fric_bps, "budget_bps": daily_bps_budget}