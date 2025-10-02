#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from .microstructure import micro_ok, adjust_for_spread

def main()->int:
    # Kost/spread-veto: sett DYBDE høyt så det ikke blir depth-veto
    book_cost = {"bid": 100.0, "ask": 101.0, "depth_usd": 1_000_000.0, "fee_bps": 25.0, "slip_bps": 30.0}
    ok, why = micro_ok("BTC/USDT", book_cost, atr=2.0)
    assert (not ok) and (why in ("cost_gate","spread")), f"forventet cost/spread veto, fikk {ok},{why}"

    # Depth-veto: for liten dybde
    book_depth = {"bid": 100.0, "ask": 100.1, "depth_usd": 1_000.0, "fee_bps": 8.0, "slip_bps": 8.0}
    ok, why = micro_ok("BTC/USDT", book_depth, atr=2.0)
    assert (not ok) and (why == "depth"), f"forventet depth veto, fikk {ok},{why}"

    # OK-case
    book_ok = {"bid": 100.0, "ask": 100.02, "depth_usd": 250_000.0, "fee_bps": 8.0, "slip_bps": 8.0}
    ok, why = micro_ok("BTC/USDT", book_ok, atr=2.0)
    assert ok, f"Skulle vært OK: {why}"

    q = adjust_for_spread(10.0)
    assert q > 0

    print("microstructure selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
