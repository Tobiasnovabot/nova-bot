from nova import paths as NPATH
import json, math, os, time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

def _novahome() -> Path:
    p = os.getenv("NOVA_HOME", "").strip()
    return Path(p) if p else Path("data")

DATA = _novahome()
CFG  = DATA / "config" / "risk.json"
EQUITY = DATA / NPATH.EQUITY.as_posix()
STATUS = DATA / "config" / "risk_status.json"

def _load_json(p: Path, default):
    try:
        return json.loads(p.read_text())
    except Exception:
        return default

def _equity_series() -> Tuple[float, float, float]:
    """returns (equity_now, equity_day_start, peak_all_time)"""
    eq = _load_json(EQUITY, [])
    if not isinstance(eq, list) or not eq:
        return (10_000.0, 10_000.0, 10_000.0)
    # eq element: {"ts": ..., "equity": float}
    eq_sorted = sorted(eq, key=lambda x: x.get("ts", 0))
    now = float(eq_sorted[-1].get("equity", 10_000.0))
    peak = max(float(x.get("equity", 0.0)) for x in eq_sorted)
    # approx "start of day": første punkt siste 24t, ellers første
    t_now = eq_sorted[-1].get("ts", time.time())
    day_start_candidates = [x for x in eq_sorted if (t_now - x.get("ts", t_now)) <= 86400]
    day_start = float((day_start_candidates[0] if day_start_candidates else eq_sorted[0]).get("equity", now))
    return (now, day_start, peak)

def _drawdown_mult(cfg: Dict[str, Any], eq_now: float, peak: float) -> Tuple[float, float]:
    if peak <= 0:
        return (1.0, 0.0)
    dd = max(0.0, (peak - eq_now) / peak)
    tiers = cfg.get("drawdown_tiers", [])
    mult = 1.0
    for t in tiers:
        if dd <= float(t.get("dd", 0)):
            mult = float(t.get("mult", 1.0)); break
    else:
        # over største terskel
        if tiers:
            mult = float(tiers[-1].get("mult", 0.3))
        else:
            mult = 0.3
    return (mult, dd)

def _daily_guard(cfg: Dict[str, Any], eq_now: float, eq_day: float) -> bool:
    limit_bps = float(cfg.get("daily_loss_limit_bps", 200))
    limit_frac = limit_bps / 10_000.0
    return (eq_now - eq_day) <= (-limit_frac * eq_day)

def _cap_notional(cfg: Dict[str, Any], equity: float, notional: float) -> float:
    max_bps = float(cfg.get("max_notional_bps", 2000))  # 20%
    cap = (max_bps / 10_000.0) * equity
    return min(notional, cap)

def compute_position_size(price: float,
                          stop_frac: Optional[float] = None,
                          override_equity: Optional[float] = None) -> Dict[str, Any]:
    """
    Returnerer sizing-beregning gitt pris og (valgfritt) stop-avstand (fraksjon).
    """
    cfg = _load_json(CFG, {})
    eq_now, eq_day, peak = _equity_series()
    if override_equity is not None:
        eq_now = float(override_equity)

    base_bps = float(cfg.get("base_risk_bps", 50))
    base_risk = base_bps / 10_000.0

    mult, dd = _drawdown_mult(cfg, eq_now, peak)

    blocked_by_day = _daily_guard(cfg, eq_now, eq_day)

    sf = float(cfg.get("stop_frac_default", 0.010)) if stop_frac is None else float(stop_frac)
    sf = max(1e-4, sf)  # aldri 0

    # USD-risk pr trade
    usd_risk = eq_now * base_risk * mult
    # notional = usd_risk / (stop_frac)
    notional = usd_risk / sf
    notional_capped = _cap_notional(cfg, eq_now, notional)
    qty = notional_capped / max(1e-12, float(price))

    out = {
        "equity_now": eq_now,
        "equity_day": eq_day,
        "equity_peak": peak,
        "drawdown": dd,
        "dd_multiplier": mult,
        "base_risk_bps": base_bps,
        "stop_frac": sf,
        "usd_risk_per_trade": usd_risk,
        "notional_raw": notional,
        "notional_capped": notional_capped,
        "qty": qty,
        "daily_guard_triggered": blocked_by_day,
        "max_concurrent_positions": int(cfg.get("max_concurrent_positions", 5))
    }

    # skriv status for innsikt
    try:
        STATUS.write_text(json.dumps({
            "ts": int(time.time()),
            "equity_now": eq_now,
            "equity_peak": peak,
            "equity_day": eq_day,
            "drawdown": dd,
            "dd_multiplier": mult,
            "daily_block_new_trades": blocked_by_day
        }, separators=(",",":")))
    except Exception:
        pass

    return out
