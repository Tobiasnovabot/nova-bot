#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
import numpy as np
from typing import Dict, List, Tuple

_PARAMS = {
    "VAR_CAP_PCT": 0.05,    # maks 5% intradag VaR av total equity
    "LOOKBACK": 20,         # lookback for vol/std
}

def set_params(**kw) -> None:
    for k,v in kw.items():
        if k in _PARAMS:
            _PARAMS[k] = v

# ---------- Vol-parity light ----------
def vol_parity_weights(vols: Dict[str, float]) -> Dict[str, float]:
    """
    vol: dict sym->annualisert std (eller ATR%)
    Returnerer normaliserte vekter ~1/vol.
    """
    inv = {sym: 1.0/max(v,1e-9) for sym,v in vols.items()}
    s = sum(inv.values())
    if s <= 0: return {sym:0.0 for sym in vols}
    return {sym: v/s for sym,v in inv.items()}

# ---------- Intradag VaR cap ----------
def apply_var_cap(equity: float, weights: Dict[str, float], vols: Dict[str,float]) -> Dict[str,float]:
    """
    Skaler vekter slik at sum(|w|*vol) <= VAR_CAP_PCT
    """
    cur_risk = sum(abs(weights[sym])*vols.get(sym,0.0) for sym in weights)
    cap = _PARAMS["VAR_CAP_PCT"]
    if cur_risk <= cap:
        return weights
    scale = cap/max(cur_risk,1e-9)
    return {sym: w*scale for sym,w in weights.items()}

# ---------- Per-symbol regime ----------
def per_symbol_regime(rets: List[float], thresh: float=0.0) -> str:
    """
    Enkel regime: bull hvis mean ret > thresh, bear hvis < -thresh, ellers chop
    """
    if len(rets)==0:
        return "chop"
    m = float(np.mean(rets))
    if m > thresh:
        return "bull"
    if m < -thresh:
        return "bear"
    return "chop"