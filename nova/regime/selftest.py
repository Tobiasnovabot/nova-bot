#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from pathlib import Path
import sys

try:
    from .regime import detect_regime, auto_preset
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.regime.regime import detect_regime, auto_preset

def _mk_df_trend(n=300, start=100.0, drift_total=+0.50, noise=0.005, seed=1):
    """
    Geometrisk random walk med tydelig total drift.
    Viktig: noise >= 0.003 for å komme over rv-threshold i detect_regime().
    """
    rng = np.random.default_rng(seed)
    mu_step = np.log(1.0 + drift_total) / n
    ret = rng.normal(mu_step, noise, n)
    price = start * np.exp(np.cumsum(ret))
    return pd.DataFrame({"close": price})

def _mk_df_flat(n=300, level=100.0, noise=0.00015, seed=2):
    rng = np.random.default_rng(seed)
    ret = rng.normal(0.0, noise, n)
    price = level * np.exp(np.cumsum(ret))
    return pd.DataFrame({"close": price})

def main() -> int:
    # Bull: høyere vol enn rv-cutoff + klar oppdrift
    btc_bull = _mk_df_trend(drift_total=+0.60, noise=0.006, seed=7)
    eth_bull = _mk_df_trend(drift_total=+0.55, noise=0.006, seed=8)
    res_bull = detect_regime(btc_bull, eth_bull)
    assert res_bull["regime"] == "bull", f"Forventet bull, fikk {res_bull['regime']}"

    # Bear: tilsvarende men negativ drift
    btc_bear = _mk_df_trend(drift_total=-0.60, noise=0.006, seed=9)
    eth_bear = _mk_df_trend(drift_total=-0.55, noise=0.006, seed=10)
    res_bear = detect_regime(btc_bear, eth_bear)
    assert res_bear["regime"] == "bear", f"Forventet bear, fikk {res_bear['regime']}"

    # Chop: svært lav vol under rv-cutoff
    btc_chop = _mk_df_flat(noise=0.00015, seed=11)
    eth_chop = _mk_df_flat(noise=0.00015, seed=12)
    res_chop = detect_regime(btc_chop, eth_chop)
    assert res_chop["regime"] == "chop", f"Forventet chop, fikk {res_chop['regime']}"

    # Auto preset + guards
    a1 = auto_preset(res_bull, hour_local=10, breadth_up_frac=0.6, var_1h_pct=1.0)
    assert a1["preset"] == "trend" and a1["allow"] is True
    a2 = auto_preset(res_bull, hour_local=3, breadth_up_frac=0.2, var_1h_pct=1.0)
    assert a2["allow"] is False and a2["why"] == "narrow_breadth"
    a3 = auto_preset(res_chop, hour_local=14, breadth_up_frac=0.6, var_1h_pct=3.5)
    assert a3["allow"] is False and a3["why"] == "var_guard"

    print("regime selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

