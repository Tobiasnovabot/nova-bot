#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from .pnl import apply_fees_slip

def main()->int:
    f = {"side":"buy","symbol":"BTC/USDT","qty":0.01,"price":25000.0,"fee_bps":10.0,"slip_bps":20.0}
    out = apply_fees_slip(f)
    assert "eff_price" in out and out["eff_price"] > 0
    print("pnl_costs selftest: OK")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
