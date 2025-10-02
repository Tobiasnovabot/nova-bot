#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time, sys
from pathlib import Path

try:
    from .robustness import RedundantFeed, FailoverRouter, LatencySLO, ReplayHarness, SimExchange
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.robustness.robustness import RedundantFeed, FailoverRouter, LatencySLO, ReplayHarness, SimExchange

def _primary(sym: str, i: int):
    # feile på annethvert kall for å trigge fallback
    if i % 2 == 0:
        raise RuntimeError("primary down")
    return {"close": 100+i}, {"bid": 100+i-0.1, "ask":100+i+0.1, "last":100+i}

def _fallback(sym: str, i: int):
    return {"close": 90+i}, {"bid": 90+i-0.1, "ask":90+i+0.1, "last":90+i}

def main() -> int:
    # RedundantFeed: sjekk fallback brukes
    rf = RedundantFeed(_primary, _fallback)
    for i in range(6):
        _ = rf.get("BTC/USDT", i)
    assert rf.stats["fallback_used"] >= 3 and rf.stats["primary_ok"] >= 3

    # FailoverRouter: binance ned -> okx valgt
    fr = FailoverRouter(["BTC/USDT"], ["binance","okx"])
    fr.mark_down("binance")
    assert fr.pick("BTC/USDT") == "okx"
    fr.mark_up("binance")
    assert fr.pick("BTC/USDT") in ("binance","okx")

    # LatencySLO: stramt budsjett for deterministisk brudd
    slo = LatencySLO(budget_ms=5.0)
    with slo.timer():
        time.sleep(0.02)  # ~20 ms arbeid
    dt = float(slo.last_ms or 0.0)
    assert dt >= 10.0, f"målt latency for lav: {dt:.3f}ms"
    assert slo.breaches == 1 and slo.samples == 1, f"slo: breaches={slo.breaches}, samples={slo.samples}, dt={dt:.3f}ms"

    # ReplayHarness: rekkefølge bevares
    ev = [("BTC/USDT", {"close":100+i}, {"last":100+i}) for i in range(5)]
    rh = ReplayHarness(ev)
    got = list(rh.iterate())
    assert got[0][1]["close"] == 100 and got[-1][1]["close"] == 104

    # SimExchange: grunnleggende fills og equity
    ex = SimExchange(cash_usdt=1000.0)
    ex.set_quote(99.9, 100.1)
    ex.market_buy(2.0)
    assert ex.qty == 2.0 and ex.cash < 1000.0
    ex.set_quote(101.0, 101.2)
    ex.market_sell(1.5)
    assert ex.qty == 0.5 and ex.cash > 0.0
    eq = ex.equity()
    assert eq > 0.0

    print("robustness selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
