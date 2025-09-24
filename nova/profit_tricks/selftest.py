#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

try:
    from .profit_tricks import rebate_farming_pnl, fee_tier_optimizer, cross_account_router, stablecoin_rotation
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.profit_tricks.profit_tricks import rebate_farming_pnl, fee_tier_optimizer, cross_account_router, stablecoin_rotation

def _approx(a,b,tol=1e-9): return abs(float(a)-float(b))<=tol

def main() -> int:
    # Rebate farming
    pnl = rebate_farming_pnl(100_000, maker_rebate_bps=2.0, slip_bps=1.0)
    assert _approx(pnl, 10.0)

    # Fee tier optimizer
    tiers = [(0, 10.0), (50_000, 8.0), (100_000, 5.0)]
    res = fee_tier_optimizer(60_000, tiers)
    assert res["fee_bps"] == 8.0

    # Cross-account routing
    accs = {"acc1": 200, "acc2": 800}
    alloc = cross_account_router(accs, 100)
    assert _approx(alloc["acc1"], 20.0) and _approx(alloc["acc2"], 80.0)

    # Stablecoin rotation
    rates = {"USDT": 0.02, "USDC": 0.05, "DAI": 0.01}
    bals = {"USDT": 500, "DAI": 200}
    f, t = stablecoin_rotation(rates, bals)
    assert f == "DAI" and t == "USDC"

    print("profit_tricks selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
