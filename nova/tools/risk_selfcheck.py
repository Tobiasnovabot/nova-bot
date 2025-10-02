#!/usr/bin/env python3
from nova.exchange import build_exchange
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
    ex = build_exchange()
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