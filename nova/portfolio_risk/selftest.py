#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, numpy as np, pandas as pd
from pathlib import Path

try:
    from .portfolio_risk import risk_parity_weights, var_cap, assign_symbol_presets
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.portfolio_risk.portfolio_risk import risk_parity_weights, var_cap, assign_symbol_presets

def _approx(a,b,tol=1e-9): return abs(float(a)-float(b)) <= tol

def main() -> int:
    # Risk parity
    rng = np.random.default_rng(42)
    rets = pd.DataFrame({
        "BTC": rng.normal(0,0.02,100),
        "ETH": rng.normal(0,0.03,100),
        "XRP": rng.normal(0,0.05,100),
    })
    w = risk_parity_weights(rets)
    assert abs(sum(w.values())-1.0) < 1e-9
    assert all(0 <= v <= 1 for v in w.values())

    # VaR cap
    ser = pd.Series(rng.normal(0,0.02,200))
    res = var_cap(ser, alpha=0.99, equity=100_000)
    assert "VaR" in res and res["VaR"] >= 0.0
    assert res["cap_equity"] <= 100_000

    # Symbol presets
    metrics = {
        "BTC":{"vol":0.02,"trend":0.02,"dd":0.05}, # positiv trend
        "DOGE":{"vol":0.10,"trend":0.00,"dd":0.15}, # høy vol
        "XRP":{"vol":0.03,"trend":0.00,"dd":0.05}, # balansert
    }
    pres = assign_symbol_presets(metrics)
    assert pres["BTC"] == 9
    assert pres["DOGE"] == 1
    assert pres["XRP"] == 5

    print("portfolio_risk selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
