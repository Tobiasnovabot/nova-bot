#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from pathlib import Path
import sys

try:
    from .backtest_sim import run_backtest, grid_search
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.backtest_sim.backtest_sim import run_backtest, grid_search

def _mk_df(n=600, start=100.0, seed=123):
    rng = np.random.default_rng(seed)
    ret = rng.normal(0.0006, 0.006, n)  # svakt opp + realistisk vol
    price = start * np.exp(np.cumsum(ret))
    high = price * (1.0 + 0.0015)
    low  = price * (1.0 - 0.0015)
    open_ = np.r_[price[0], price[:-1]]
    vol = np.full(n, 1000.0)
    return pd.DataFrame({"open":open_, "high":high, "low":low, "close":price, "volume":vol})

def main() -> int:
    df = _mk_df()

    cfg = {
        "df": df,
        "params": {
            "ema_fast": 12, "ema_slow": 26, "atr_p": 14,
            "atr_k_stop": 2.0, "tp_R": 2.0,
            "fee_bps": 10.0, "slip_bps": 10.0,
            "risk_usd": 100.0, "cash0": 10_000.0,
        },
        "seed": 42,
    }

    r1 = run_backtest(cfg)
    r2 = run_backtest(cfg)
    # Reproduserbar PnL
    assert abs(r1["metrics"]["net_pnl"] - r2["metrics"]["net_pnl"]) < 1e-12
    assert len(r1["equity_curve"]) == len(r2["equity_curve"])
    assert all(abs(a - b) < 1e-12 for a, b in zip(r1["equity_curve"], r2["equity_curve"]))

    # Grid search deterministisk
    grid = {"ema_fast":[8,12], "ema_slow":[20,26], "atr_p":[14], "atr_k_stop":[1.5,2.0], "tp_R":[1.5,2.0],
            "fee_bps":[10.0], "slip_bps":[10.0], "risk_usd":[100.0], "cash0":[10_000.0]}
    g1 = grid_search(df, grid, seed=7)
    g2 = grid_search(df, grid, seed=7)
    assert g1["best"]["score"] == g2["best"]["score"]
    assert g1["best"]["params"] == g2["best"]["params"]

    print("backtest_sim selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
