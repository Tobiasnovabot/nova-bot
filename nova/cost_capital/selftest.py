#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

try:
    from .cost_capital import vip_tier_distance, idle_cash_yield, turnover_budget
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.cost_capital.cost_capital import vip_tier_distance, idle_cash_yield, turnover_budget

def _approx(a, b, tol=1e-9): return abs(float(a)-float(b)) <= tol

def main() -> int:
    # VIP tiers
    tiers = {0: 0, 1: 50_000, 2: 100_000, 3: 250_000}
    res = vip_tier_distance(60_000, tiers)
    assert res["cur_tier"] == 1
    assert res["next"][0] == 2
    assert _approx(res["missing_usd"], 40_000.0)

    # Idle cash yield
    y = idle_cash_yield(10_000, apy=0.05, days=1)
    assert round(y, 2) == round(10_000 * 0.05 / 365, 2)

    # Turnover budget
    tb = turnover_budget(100_000, fric_bps=10.0, daily_bps_budget=50.0)
    assert "max_turnover_usd" in tb and tb["max_turnover_usd"] > 0

    print("cost_capital selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
