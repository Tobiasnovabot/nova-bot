#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}

# --- mapper ---
mkdir -p nova/risk nova/tools data/config

# --- default config ---
cat > data/config/risk.json <<'JSON'
{
  "base_risk_bps": 50,                 // 0.50% av equity pr trade (justeres av drawdown)
  "max_notional_bps": 2000,            // maks 20% av equity i notional pr trade
  "stop_frac_default": 0.010,          // 1.0% pris-avstand hvis signal ikke gir stop
  "daily_loss_limit_bps": 200,         // stans nye trades for dagen ved -2.00%
  "max_concurrent_positions": 5,       // retningslinje (rapporteres i status)
  "drawdown_tiers": [
    {"dd": 0.05, "mult": 1.00},
    {"dd": 0.10, "mult": 0.70},
    {"dd": 0.20, "mult": 0.50},
    {"dd": 9.99, "mult": 0.30}
  ]
}
JSON

# --- riskoregler ---
cat > nova/risk/risk_rules.py <<'PY'
import json, math, os, time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

def _novahome() -> Path:
    p = os.getenv("NOVA_HOME", "").strip()
    return Path(p) if p else Path("data")

DATA = _novahome()
CFG  = DATA / "config" / "risk.json"
EQUITY = DATA / "equity.json"
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
PY

# --- CLI selvtest ---
cat > nova/tools/risk_selfcheck.py <<'PY'
#!/usr/bin/env python3
import os, sys, json
from pathlib import Path
try:
    import ccxt
except Exception as e:
    print("Mangler ccxt i venv:", e); sys.exit(1)

from nova.risk.risk_rules import compute_position_size, _novahome

NOVA_HOME = _novahome()
CFG = NOVA_HOME / "config" / "risk.json"

def load_cfg():
    try:
        return json.loads(CFG.read_text())
    except Exception:
        return {}

def fmt_usd(v): return f"${v:,.2f}"
def fmt_pct(v): return f"{v*100:.2f}%"

def main():
    symbols = sys.argv[1:] or ["BTC/USDT","ETH/USDT","SOL/USDT","BNB/USDT"]
    ex = ccxt.binance({'enableRateLimit': True})
    tickers = ex.fetch_tickers(symbols)
    cfg = load_cfg()

    print("== Risk Self-Check ==")
    print("NOVA_HOME:", NOVA_HOME)
    print("Config:", json.dumps(cfg, indent=2))
    print()

    for sym in symbols:
        t = tickers.get(sym, {})
        price = t.get("last") or t.get("close") or t.get("ask") or t.get("bid")
        if not price:
            print(f"{sym}: ingen pris fra exchange"); continue
        out = compute_position_size(price=float(price), stop_frac=None)
        print(f"[{sym}] price={price}")
        print(f"  equity_now={fmt_usd(out['equity_now'])}  peak={fmt_usd(out['equity_peak'])}  dd={fmt_pct(out['drawdown'])}  mult={out['dd_multiplier']:.2f}")
        print(f"  base_risk={out['base_risk_bps']/100:.2f} bps  stop_frac={fmt_pct(out['stop_frac'])}")
        print(f"  usd_risk={fmt_usd(out['usd_risk_per_trade'])}  notional={fmt_usd(out['notional_capped'])}")
        print(f"  qty={out['qty']:.8f}  daily_block={out['daily_guard_triggered']}  max_positions={out['max_concurrent_positions']}")
        print()
    # kort oppsummering
    status_p = NOVA_HOME / "config" / "risk_status.json"
    if status_p.exists():
        print("risk_status.json:", status_p.read_text())

if __name__ == "__main__":
    main()
PY
chmod +x nova/tools/risk_selfcheck.py

# --- mini healthcheck for risk ---
cat > nova/tools/risk_healthcheck.sh <<'HS'
#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}
echo "== Risk Healthcheck =="
echo "NOVA_HOME=${NOVA_HOME:-$(grep -E '^NOVA_HOME=' .env 2>/dev/null | cut -d= -f2)}"
test -f data/config/risk.json && echo "PASS: risk.json finnes" || { echo "FAIL: mangler data/config/risk.json"; exit 1; }
python3 - <<'PY'
from nova.risk.risk_rules import compute_position_size
print("PASS: import risk_rules OK")
out = compute_position_size(price=100.0, stop_frac=0.01, override_equity=10000)
print("PASS: compute_position_size OK ->", {k:out[k] for k in ("qty","dd_multiplier","daily_guard_triggered")})
PY
echo "PASS: risk_status.json:"; test -f data/config/risk_status.json && tail -n1 data/config/risk_status.json || echo "(skrives første gang du kjører selfcheck)"
HS
chmod +x nova/tools/risk_healthcheck.sh

# --- umiddelbar selvtest ---
${NOVA_HOME:-/home/nova/nova-bot}/nova/tools/risk_healthcheck.sh
${NOVA_HOME:-/home/nova/nova-bot}/nova/tools/risk_selfcheck.py