#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

try:
    from .quality_obs import data_quality_metrics, edge_dashboard_snapshot, canary_presets_decide
    from nova.core_boot.core_boot import NOVA_HOME, now_oslo
    from nova.stateio.stateio import read_json_atomic
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.quality_obs.quality_obs import data_quality_metrics, edge_dashboard_snapshot, canary_presets_decide
    from nova.core_boot.core_boot import NOVA_HOME, now_oslo
    from nova.stateio.stateio import read_json_atomic

def main() -> int:
    # --- Lag syntetiske data med ts og noen NaN ---
    n = 200
    ts = pd.date_range(end=pd.Timestamp.utcnow(), periods=n, freq="T")
    close = np.linspace(100, 110, n) + np.random.normal(0, 0.1, n)
    vol = np.abs(np.random.normal(1000, 50, n))
    close[5] = np.nan
    vol[7] = np.nan
    df = pd.DataFrame({"ts": ts, "close": close, "volume": vol})

    # Første kjøring init baseline
    m1 = data_quality_metrics(df)
    assert m1["completeness_ratio"] < 1.0
    # Andre kjøring med liten drift → PSI små
    m2 = data_quality_metrics(df.assign(close=lambda x: x["close"] + 0.02))
    psi_close = m2["psi_per_col"]["close"]
    assert psi_close is not None and psi_close >= 0.0

    # --- Edge dashboard snapshot ---
    snap_path = edge_dashboard_snapshot({
        "expected_edge_bps": 35.0,
        "realized_cost_bps": 18.0,
        "hit_rate": 0.55,
        "hold_time_min": 42.0,
        "alpha_decay_min": 15.0,
    })
    assert snap_path.exists() and snap_path.name == "edge_dashboard.json"

    # --- Canary beslutning ---
    control = {"net_pnl": 120.0, "hit_rate": 0.55, "dd_pct": 5.0, "n_trades": 200}
    canary_bad = {"net_pnl": 80.0, "hit_rate": 0.40, "dd_pct": 8.0, "n_trades": 200}
    d1 = canary_presets_decide(control, canary_bad, tol_drawdown_pct=2.0, tol_hitrate_drop=0.10, min_trades=20)
    assert d1["decision"] == "rollback"

    canary_good = {"net_pnl": 140.0, "hit_rate": 0.58, "dd_pct": 5.5, "n_trades": 200}
    d2 = canary_presets_decide(control, canary_good)
    assert d2["decision"] in ("promote","hold")  # begge aksepteres, typisk promote

    print("quality_obs selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
