#!/usr/bin/env python3
from __future__ import annotations
from typing import Dict
import math

def target_leverage(day_vol_pct: float, target_vol_pct: float = 25.0,
                    lev_max: float = 2.5, lev_min: float = 0.25) -> float:
    """
    Skaler porteføljerisiko slik at forventet årlig vol ~ target_vol_pct.
    day_vol_pct: estimert daglig vol i % (f.eks fra BTC 30d stdev * sqrt(365))
    """
    if day_vol_pct <= 0: return 1.0
    lev = target_vol_pct / max(day_vol_pct, 1e-6)
    return float(max(lev_min, min(lev_max, lev)))

def apply_qty_scale(base_qty: float, lev: float) -> float:
    return float(base_qty * lev)