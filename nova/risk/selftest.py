#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-

from .risk import (
    apply_risk_level,
    set_market_meta,
    set_last_price,
    set_concentration_limits,
    size_order,
    get_active_profile,
)

def main() -> int:
    # Sett profil (skal tåle legacy og ny bruk)
    apply_risk_level(10, equity_usd=10_000.0)
    prof = get_active_profile()
    assert prof["level"] == 10

    sym = "BTC/USDT"
    # Børsmeta (samme feltnavn som risk.risk forventer)
    set_market_meta(sym, min_qty=0.001, min_cost=1.0, step=0.001, tick=0.01, quote="USDT")
    set_last_price(sym, 25_000.0)

    # 1) Legacy kall (ingen price/pos params) – vår risk.risk støtter dette
    q, usd, why = size_order(sym, atr=100.0, edge=0.5)  # bruker LAST_PRICE som pris
    assert why == "ok" and q > 0.001, f"legacy sizing feilet: {(q, usd, why)}"

    # 2) Nytt kall med alle parametre
    q2, usd2, why2 = size_order(
        sym,
        atr=100.0,
        edge=0.5,
        price=25_000.0,
        current_positions=0,
        current_symbol_exposure_usd=0.0,
        avail_usd=10_000.0,
    )
    assert why2 == "ok" and q2 > 0.0 and usd2 > 0.0

    # 3) Konsentrasjonsgrense
    set_concentration_limits(sym, usd_cap=200.0)
    q3, usd3, why3 = size_order(
        sym,
        atr=100.0,
        edge=0.5,
        price=25_000.0,
        current_positions=0,
        current_symbol_exposure_usd=0.0,
        avail_usd=10_000.0,
    )
    assert usd3 <= 200.0 + 1e-6 and why3 == "ok", f"conc limit ikke respektert: {(q3, usd3, why3)}"

    # 4) Max positions blokkering
    q4, usd4, why4 = size_order(
        sym,
        atr=100.0,
        edge=0.5,
        price=25_000.0,
        current_positions=prof.get("max_positions", 10),
        current_symbol_exposure_usd=0.0,
        avail_usd=10_000.0,
    )
    assert q4 == 0.0 and why4 == "max_positions"

    print("risk selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())