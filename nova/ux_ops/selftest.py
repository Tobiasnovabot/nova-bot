#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

try:
    from .ux_ops import what_if_trade, diag_snapshot, cfg_save, cfg_load, cfg_diff
    from nova.core_boot.core_boot import NOVA_HOME
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.ux_ops.ux_ops import what_if_trade, diag_snapshot, cfg_save, cfg_load, cfg_diff
    from nova.core_boot.core_boot import NOVA_HOME

def main() -> int:
    # What-if: long med bedre TP enn stop
    r = what_if_trade("buy", entry=100.0, qty=1.0, stop=95.0, tp=105.0, prob_tp=0.6, fee_bps=10.0, slip_bps=10.0)
    assert "EV_usd" in r and "R" in r
    assert r["PnL_tp"] > 0 and r["PnL_stop"] < 0

    # Diag
    d = diag_snapshot()
    assert "ok" in d and "paths" in d

    # Config versioning
    cfg1 = {"risk_level": 3, "policy": "auto", "watch": ["BTC/USDT","ETH/USDT"]}
    cfg2 = {"risk_level": 5, "policy": "auto", "watch": ["BTC/USDT"]}
    p1 = cfg_save("t1", cfg1)
    p2 = cfg_save("t2", cfg2)
    assert p1.exists() and p2.exists()
    l1 = cfg_load("t1"); l2 = cfg_load("t2")
    assert l1 == cfg1 and l2 == cfg2
    diff = cfg_diff("t1", "t2")
    assert "changed" in diff and "risk_level" in diff["changed"]

    print("ux_ops selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
