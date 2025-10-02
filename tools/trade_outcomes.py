#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, time, math, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRADES = ROOT/"data"/"trades.json"
STATE  = ROOT/"data"/"state.json"
OUTJS  = ROOT/"data"/"trade_outcomes.json"
PROM   = ROOT/"metrics"/"novax_trades.prom"

def _load(p, d):
    try:
        txt = p.read_text()
        return json.loads(txt) if txt.strip() else d
    except Exception:
        return d

def _safe_num(x, d=0.0):
    try:
        if x is None: return d
        return float(x)
    except Exception:
        return d

def _closed(tr):
    # status == closed, eller har ts_close/closed_ts og ikke "open"
    st = str(tr.get("status","")).lower()
    if st == "open": return False
    if tr.get("ts_close") or tr.get("closed_ts"): return True
    # fallback: hvis har pnl_usd og ikke open
    return "pnl_usd" in tr and st != "open"

def _key(tr):
    # stabil hash-basert nøkkel av symbol+åpningstid+strategi
    s = f"{tr.get('symbol','')}|{tr.get('ts') or tr.get('ts_open') or ''}|{tr.get('strategy','')}"
    return hashlib.md5(s.encode()).hexdigest()

def collect():
    trades = _load(TRADES, [])
    if not isinstance(trades, list):
        trades = []
    closed = [t for t in trades if isinstance(t, dict) and _closed(t)]
    now = int(time.time())

    # Aggreger PnL, win/loss
    wins, losses = [], []
    per_strat = {}  # strat -> [wins, losses]
    for t in closed:
        pnl = _safe_num(t.get("pnl_usd"))
        fees = _safe_num(t.get("fees_usd"))
        net = pnl - fees
        strat = t.get("strategy") or "unknown"
        if net > 0:
            wins.append(net)
            per_strat.setdefault(strat, [0,0])[0] += 1
        else:
            losses.append(-net)
            per_strat.setdefault(strat, [0,0])[1] += 1

    n = len(closed)
    w = len(wins)
    l = len(losses)
    winrate = (w / n) if n>0 else 0.0
    avg_win = (sum(wins)/w) if w>0 else 0.0
    avg_loss = (sum(losses)/l) if l>0 else 0.0
    payoff = (avg_win/avg_loss) if avg_loss>0 else (1.0 if avg_win>0 else 0.0)

    out = {
        "ts": now,
        "closed_trades": n,
        "wins": w,
        "losses": l,
        "winrate": winrate,
        "avg_win_usd": avg_win,
        "avg_loss_usd": avg_loss,
        "payoff": payoff,
        "per_strategy": {
            k: {"wins":v[0], "losses":v[1],
                "winrate": (v[0]/(v[0]+v[1])) if (v[0]+v[1])>0 else 0.0}
            for k,v in sorted(per_strat.items())
        }
    }
    OUTJS.parent.mkdir(parents=True, exist_ok=True)
    OUTJS.write_text(json.dumps(out, indent=2))

    # Prometheus
    PROM.parent.mkdir(parents=True, exist_ok=True)
    ts_ms = now*1000
    lines = []
    lines += [
        "# HELP novax_trades_closed_total Total closed trades",
        "# TYPE novax_trades_closed_total gauge",
        f"novax_trades_closed_total {n} {ts_ms}",
        "# HELP novax_trades_winrate Winrate 0-1 over all closed trades",
        "# TYPE novax_trades_winrate gauge",
        f"novax_trades_winrate {winrate:.6f} {ts_ms}",
        "# HELP novax_trades_payoff Payoff ratio avg_win/avg_loss",
        "# TYPE novax_trades_payoff gauge",
        f"novax_trades_payoff {payoff:.6f} {ts_ms}",
        "# HELP novax_trades_avg_win_usd Average win in USD",
        "# TYPE novax_trades_avg_win_usd gauge",
        f"novax_trades_avg_win_usd {avg_win:.6f} {ts_ms}",
        "# HELP novax_trades_avg_loss_usd Average loss in USD",
        "# TYPE novax_trades_avg_loss_usd gauge",
        f"novax_trades_avg_loss_usd {avg_loss:.6f} {ts_ms}",
    ]
    # per-strategy winrate
    lines += [
        "# HELP novax_trades_winrate_strategy Winrate by strategy 0-1",
        "# TYPE novax_trades_winrate_strategy gauge",
    ]
    for strat, vals in out["per_strategy"].items():
        sname = strat.replace('"','')
        lines.append(f'novax_trades_winrate_strategy{{strategy="{sname}"}} {vals["winrate"]:.6f} {ts_ms}')
    PROM.write_text("\n".join(lines)+"\n")
    print("trade_outcomes: wrote metrics and summary")

if __name__ == "__main__":
    collect()
