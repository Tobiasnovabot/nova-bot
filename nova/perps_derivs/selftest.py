#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

try:
    from .perps_derivs import set_params, check_perps_ok, apply_carry_pnl, basis_arbitrage_signal
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.perps_derivs.perps_derivs import set_params, check_perps_ok, apply_carry_pnl, basis_arbitrage_signal

def _approx(a,b,tol=1e-9): return abs(float(a)-float(b))<=tol

def main() -> int:
    # Funding spike -> veto
    set_params(FUNDING_SPIKE_ABS=0.005)  # 0.5% per 8h
    ok, why = check_perps_ok({"funding_rate": 0.006, "interval_hours": 8, "spot_px": 100.0, "perps_px": 100.5})
    assert not ok and why == "funding_spike"

    # Normal funding, men ekstrem basis -> veto
    ok, why = check_perps_ok({"funding_rate": 0.0001, "interval_hours": 8, "spot_px": 100.0, "perps_px": 103.5})
    assert not ok and why == "basis_extreme"

    # OK case
    ok, why = check_perps_ok({"funding_rate": 0.0002, "interval_hours": 8, "spot_px": 100.0, "perps_px": 100.2})
    assert ok

    # Carry PnL: long betaler når rate>0
    pnl_long = apply_carry_pnl("long", notional_usd=10_000.0, funding_rate=0.001, hours_held=8.0, ref_interval_hours=8.0)
    assert _approx(pnl_long, -10.0)
    pnl_short = apply_carry_pnl("short", notional_usd=10_000.0, funding_rate=0.001, hours_held=8.0, ref_interval_hours=8.0)
    assert _approx(pnl_short, +10.0)

    # Basis-arb signal
    sig1 = basis_arbitrage_signal(spot_px=100.0, perps_px=101.0, thresh_bps=50.0)  # 100 bps
    assert sig1["action"] == "short_perp_long_spot"
    sig2 = basis_arbitrage_signal(spot_px=100.0, perps_px=99.0, thresh_bps=50.0)   # -100 bps
    assert sig2["action"] == "long_perp_short_spot"
    sig3 = basis_arbitrage_signal(spot_px=100.0, perps_px=100.2, thresh_bps=50.0)  # 20 bps
    assert sig3["action"] == "none"

    print("perps_derivs selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
