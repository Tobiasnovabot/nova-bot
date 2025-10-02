#!/usr/bin/env python3
def whatif(sym: str, price: float, qty: float, cfg: dict)->dict:
    return {"sym":sym,"notional":qty*price}

def main()->int:
    r = whatif("BTC/USDT", 100.0, 2.0, {})
    assert r["notional"] == 200.0
    print("whatif selftest: OK")
    return 0

if __name__=="__main__": raise SystemExit(main())
