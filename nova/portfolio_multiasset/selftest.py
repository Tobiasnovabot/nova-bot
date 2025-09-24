#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import sys
from pathlib import Path

try:
    from .portfolio_multiasset import vol_parity_weights, apply_var_cap, per_symbol_regime, set_params
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.portfolio_multiasset.portfolio_multiasset import vol_parity_weights, apply_var_cap, per_symbol_regime, set_params

def _approx(a,b,tol=1e-9): return abs(float(a)-float(b))<=tol

def main() -> int:
    vols = {"BTC":0.6,"ETH":0.8,"XRP":1.2}
    w = vol_parity_weights(vols)
    s = sum(w.values())
    assert _approx(s,1.0), f"vekter summerer ikke: {s}"
    assert w["BTC"] > w["XRP"], "lavere vol burde gi høyere vekt"

    # VaR cap
    weights = {"BTC":0.5,"ETH":0.5}
    vols2 = {"BTC":1.0,"ETH":1.0}
    set_params(VAR_CAP_PCT=0.5)
    w2 = apply_var_cap(1000.0, weights, vols2)
    risk_before = sum(abs(weights[s])*vols2[s] for s in weights)
    risk_after = sum(abs(w2[s])*vols2[s] for s in w2)
    assert risk_after <= 0.5+1e-9, f"VAR cap brutt: {risk_after}"

    # Per-symbol regime
    rets_up = [0.01]*50
    rets_dn = [-0.01]*50
    rets_chop = [0.0,0.001,-0.001]
    assert per_symbol_regime(rets_up) == "bull"
    assert per_symbol_regime(rets_dn) == "bear"
    assert per_symbol_regime(rets_chop) == "chop"

    print("portfolio_multiasset selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
