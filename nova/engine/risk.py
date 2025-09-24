from __future__ import annotations
from pathlib import Path
import json, time
from nova.config import MAX_GROSS_EXPOSURE, STOP_PCT, dd_size_multiplier

STATE = Path("/home/nova/nova-bot/state")

def _load(name, d):
    p = STATE/f"{name}.json"
    try: return json.loads(p.read_text())
    except: return d

def calc_gross_exposure():
    eq = _load("equity", {"equity":0})
    pos = _load("positions", {"positions":{},"prices":{}})
    equity = float(eq.get("equity",0)) or 1.0
    gross = 0.0
    for s,qty in (pos.get("positions") or {}).items():
        px=float((pos.get("prices") or {}).get(s,0.0))
        gross+=abs(float(qty))*px
    return gross, equity, gross/equity

def size_limit_by_risk(symbol: str, desired_notional: float) -> float:
    # 1) gross exposure tak
    gross, equity, ratio = calc_gross_exposure()
    if ratio >= MAX_GROSS_EXPOSURE:
        return 0.0
    # 2) drawdown basert trimming
    eq = _load("equity", {"equity":0,"equity_high":0})
    eq_hi=float(eq.get("equity_high",0)) or 0.0
    cur=float(eq.get("equity",0)) or 0.0
    dd = 0.0 if eq_hi<=0 else (eq_hi-cur)/eq_hi
    desired_notional *= dd_size_multiplier(dd)
    return desired_notional

def hit_stop(symbol: str) -> bool:
    # enkel trailing/entry stop mot avg_cost
    pos = _load("positions", {"positions":{},"prices":{},"avg_cost":{}})
    qty = float((pos.get("positions") or {}).get(symbol,0.0))
    if qty==0: return False
    px  = float((pos.get("prices") or {}).get(symbol,0.0))
    ac  = float((pos.get("avg_cost") or {}).get(symbol,px))
    # long stop
    if qty>0 and px <= ac*(1.0-STOP_PCT): return True
    # short stop (om short støttes senere)
    if qty<0 and px >= ac*(1.0+STOP_PCT): return True
    return False

def clamp_order(symbol: str, side: str, desired_qty: float, price: float) -> float:
    # gjør qty til notional, trim med risk, tilbake til qty
    notional = abs(desired_qty)*price
    notional = size_limit_by_risk(symbol, notional)
    qty = 0.0 if price<=0 else notional/price
    # force flat ved stop
    if hit_stop(symbol):
        return 0.0
    return qty if side=="buy" else -qty
