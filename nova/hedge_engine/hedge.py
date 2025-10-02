#!/usr/bin/env python3
from __future__ import annotations

def hedge_size(beta: float, exposure_usd: float, cap_frac: float=0.5) -> float:
    """
    beta: mål-betasammenheng (0..1 for delvis hedge)
    exposure_usd: netto long eksponering
    cap_frac: hvor stor del som kan hedges
    returnerer USD å hedge (short)
    """
    beta=max(0.0, float(beta)); cap=max(0.0, float(cap_frac))
    return max(0.0, float(exposure_usd) * beta * cap)