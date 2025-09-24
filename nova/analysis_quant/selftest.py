#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from pathlib import Path
import sys

try:
    from .analysis_quant import factor_attribution, hedge_ratio, kelly_frontier, risk_premium_scores
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.analysis_quant.analysis_quant import factor_attribution, hedge_ratio, kelly_frontier, risk_premium_scores

def _approx(a,b,t=1e-2): return abs(float(a)-float(b))<=t

def main() -> int:
    rng = np.random.default_rng(7)
    n = 500

    # Factor attribution: y = 0.5*F1 -0.2*F2 + eps
    F1 = rng.normal(0, 1, n)
    F2 = rng.normal(0, 1, n)
    eps = rng.normal(0, 0.1, n)
    y = 0.5*F1 - 0.2*F2 + eps
    dfF = pd.DataFrame({"F1":F1, "F2":F2})
    out = factor_attribution(pd.Series(y), dfF)
    assert _approx(out["betas"]["F1"], 0.5, 0.05)
    assert _approx(out["betas"]["F2"], -0.2, 0.05)
    assert out["r2"] > 0.7

    # Hedge ratio: y ≈ 2*x
    x = rng.normal(0, 1, n)
    y2 = 2.0*x + rng.normal(0, 0.05, n)
    beta = hedge_ratio(pd.Series(y2), pd.Series(x))
    assert _approx(beta, 2.0, 0.05)

    # Kelly frontier
    mu = np.array([0.10, 0.05, 0.02])
    Sigma = np.diag([0.2, 0.1, 0.05])**2
    k = kelly_frontier(mu, Sigma, leverages=[0.0, 1.0, 2.0], nonneg=True)
    base = k["base"]
    assert base.sum() > 0 and np.all(base >= -1e-12)
    w1 = k["curve"][1][1]
    w2 = k["curve"][2][1]
    # vekt ved 2x skal være ~2x v1 i norm
    assert _approx(w2.sum(), 2.0, 1e-6) and _approx(w1.sum(), 1.0, 1e-6)

    # Risk premium score
    d = pd.DataFrame({
        "basis_bps":[10, 50, 100],
        "funding_rate":[0.0, 0.001, 0.002],
        "carry_bps":[5, 7, 9],
        "mom_bps":[-5, 0, 5],
    })
    s = risk_premium_scores(d)
    assert len(s) == 3 and s.min() >= 0 and s.max() <= 1

    print("analysis_quant selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
