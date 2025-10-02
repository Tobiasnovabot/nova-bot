#!/usr/bin/env python3
from nova.capital_allocator.allocator import suggest_alloc, per_trade_budget
def main()->int:
    stats={"a":{"sharpe":0.5,"win":0.52},"b":{"sharpe":1.2,"win":0.55}}
    w=suggest_alloc(stats, 10000)
    assert abs(sum(w.values())-1.0)<1e-9
    assert w["b"]>w["a"]
    x=per_trade_budget(10000, 0.03, w["b"])
    assert x>0
    print("capital_allocator selftest: OK")
    return 0
if __name__=="__main__": raise SystemExit(main())
