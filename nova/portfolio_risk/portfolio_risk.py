#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

# ---------- Kovarians / risk-parity ----------

def risk_parity_weights(returns: pd.DataFrame) -> Dict[str, float]:
    """
    Beregner enkle risk-parity weights basert på kovariansmatrise.
    returns: DataFrame (kolonner = symbols, rader = prosentendringer)
    """
    if returns.empty:
        return {}
    cov = returns.cov()
    inv_var = 1.0 / np.diag(cov.values)
    w = inv_var / inv_var.sum()
    return {sym: float(w[i]) for i, sym in enumerate(returns.columns)}

# ---------- VaR cap ----------

def var_cap(returns: pd.Series, *, alpha: float = 0.99, equity: float = 100_000.0) -> Dict[str, float]:
    """
    Estimerer enkel historisk Value-at-Risk.
    returns: serie av daglige pct endringer (f.eks. 0.01 = +1%).
    alpha: konfidensnivå.
    equity: total kapital.
    """
    if returns.empty:
        return {"VaR": 0.0, "cap_equity": equity}
    q = returns.quantile(1-alpha)
    var = float(abs(q) * equity)
    cap = equity - var
    return {"VaR": var, "cap_equity": max(0.0, cap)}

# ---------- Per-symbol regime / presets ----------

def assign_symbol_presets(metrics: Dict[str, Dict[str,float]]) -> Dict[str,int]:
    """
    metrics: {symbol: {"vol":float,"trend":float,"dd":float}}
    Returnerer {symbol: preset_level}.
      preset 1 = defensiv
      preset 5 = balansert
      preset 9 = aggressiv
    """
    out: Dict[str,int] = {}
    for sym, m in metrics.items():
        vol = float(m.get("vol",0.0))
        trend = float(m.get("trend",0.0))
        dd = float(m.get("dd",0.0))
        if dd > 0.2 or vol > 0.05:
            out[sym] = 1
        elif trend > 0.01:
            out[sym] = 9
        else:
            out[sym] = 5
    return out