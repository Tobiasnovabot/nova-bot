#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
from typing import Dict, List, Tuple

# ---------------- Rebate farming ----------------
def rebate_farming_pnl(volume_usd: float, maker_rebate_bps: float, slip_bps: float) -> float:
    """
    Beregn netto PnL fra rebate farming:
      rebate = volume_usd * maker_rebate_bps/10000
      slip_cost = volume_usd * slip_bps/10000
    """
    rebate = volume_usd * maker_rebate_bps / 1e4
    slip_cost = volume_usd * slip_bps / 1e4
    return rebate - slip_cost

# ---------------- Fee-tier optimizer ----------------
def fee_tier_optimizer(volume_30d: float, tiers: List[Tuple[float, float]]) -> Dict[str, float]:
    """
    tiers: liste av (vol_grense, fee_bps).
    Returner beste gjeldende tier gitt volume_30d.
    """
    tiers_sorted = sorted(tiers, key=lambda t: t[0])
    cur = tiers_sorted[0]
    for v, fee in tiers_sorted:
        if volume_30d >= v:
            cur = (v, fee)
    return {"vol_threshold": cur[0], "fee_bps": cur[1]}

# ---------------- Cross-account routing ----------------
def cross_account_router(accounts: Dict[str, float], trade_size: float) -> Dict[str, float]:
    """
    Fordel trade_size proporsjonalt etter account-balansene.
    accounts: dict account->balance
    Return: dict account->size
    """
    tot = sum(accounts.values())
    if tot <= 0:
        return {k: 0.0 for k in accounts}
    return {k: trade_size * (bal / tot) for k, bal in accounts.items()}

# ---------------- Stablecoin rotation ----------------
def stablecoin_rotation(rates: Dict[str, float], balances: Dict[str, float]) -> Tuple[str, str]:
    """
    Velg fra laveste yield → høyeste yield for rotasjon.
    rates: dict coin->apy%
    balances: dict coin->saldo
    Return (from_coin,to_coin).
    """
    if not rates: return ("","")
    from_coin = min(rates, key=lambda c: rates[c])
    to_coin = max(rates, key=lambda c: rates[c])
    if from_coin == to_coin: return ("","")
    if balances.get(from_coin, 0.0) <= 0: return ("","")
    return (from_coin, to_coin)