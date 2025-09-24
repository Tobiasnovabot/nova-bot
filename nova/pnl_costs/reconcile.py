#!/usr/bin/env python3
from __future__ import annotations
from typing import Tuple
from nova.notify import send as tg_send

def _sum_usdt(balance) -> float:
    tot = 0.0
    for code, v in (balance.get("total") or {}).items():
        if code == "USDT": tot += float(v or 0.0)
    return float(tot)

def daily_pnl_check(ex, state: dict, tol_frac: float = 0.001) -> Tuple[bool, str]:
    try:
        bal = ex.fetch_balance()
        exch = _sum_usdt(bal)
        local = float(state.get("equity_usd", 0.0))
        if exch <= 0 or local <= 0:
            return True, "pnl_check: skipped (non-positive equity)"
        diff = abs(exch - local)
        ok = diff <= tol_frac * max(exch, local)
        return ok, f"pnl_check: exch={exch:.2f} local={local:.2f} diff={diff:.2f} tol={tol_frac*100:.2f}%"
    except Exception as e:
        return False, f"pnl_check error: {e}"

_last_pnl_day = None
def maybe_daily_pnl_check(ex, state):
    import datetime as dt
    global _last_pnl_day
    d = dt.datetime.now(timezone.utc).date()
    if _last_pnl_day == d: return
    _last_pnl_day = d
    ok, msg = daily_pnl_check(ex, state)
    if not ok:
        tg_send("🔴 " + msg)
        state["block_new_entries"] = True
    else:
        tg_send("🟢 " + msg)
#!/usr/bin/env python3
from typing import Tuple
from nova.notify import send as tg_send

def _sum_usdt(balance) -> float:
    tot = 0.0
    for code, v in (balance.get("total") or {}).items():
        if code == "USDT": tot += float(v or 0.0)
    return float(tot)

def daily_pnl_check(ex, state: dict, tol_frac: float = 0.001) -> Tuple[bool, str]:
    try:
        bal = ex.fetch_balance()
        exch = _sum_usdt(bal)
        local = float(state.get("equity_usd", 0.0))
        if exch <= 0 or local <= 0:
            return True, "pnl_check: skipped (non-positive equity)"
        diff = abs(exch - local)
        ok = diff <= tol_frac * max(exch, local)
        return ok, f"pnl_check: exch={exch:.2f} local={local:.2f} diff={diff:.2f} tol={tol_frac*100:.2f}%"
    except Exception as e:
        return False, f"pnl_check error: {e}"

_last_pnl_day = None
def maybe_daily_pnl_check(ex, state):
    import datetime as dt
    global _last_pnl_day
    d = dt.datetime.now(timezone.utc).date()
    if _last_pnl_day == d: return
    _last_pnl_day = d
    ok, msg = daily_pnl_check(ex, state)
    if not ok:
        tg_send("🔴 " + msg)
        state["block_new_entries"] = True
    else:
        tg_send("🟢 " + msg)