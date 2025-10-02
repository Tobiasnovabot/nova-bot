#!/usr/bin/env python3
import os, json, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTCOMES = ROOT/"data"/"trade_outcomes.json"
HOLD = ROOT/"data"/"entry_hold.lock"
PROM = ROOT/"metrics"/"novax_entry_gate.prom"

WINRATE_MIN = float(os.getenv("ENTRY_WR_MIN","0.35"))
PAYOFF_MIN  = float(os.getenv("ENTRY_PAYOFF_MIN","0.90"))
MIN_CLOSED  = int(os.getenv("ENTRY_MIN_CLOSED","20"))
COOLDOWN_S  = int(os.getenv("ENTRY_COOLDOWN_S","600"))  # 10 min hysterese

def load_outcomes():
    try:
        return json.loads(OUTCOMES.read_text())
    except Exception:
        return {"closed_trades":0,"winrate":0.0,"payoff":0.0}

def write_prom(hold:int, reason:str, now:int):
    PROM.parent.mkdir(parents=True, exist_ok=True)
    ts = now*1000
    lines = [
        "# HELP novax_entry_hold 1 if entry throttle is active",
        "# TYPE novax_entry_hold gauge",
        f"novax_entry_hold {hold} {ts}",
        "# HELP novax_entry_hold_reason Reason text (as info)",
        "# TYPE novax_entry_hold_reason gauge",
        f'novax_entry_hold_reason{{reason="{reason}"}} {hold} {ts}'
    ]
    PROM.write_text("\n".join(lines)+"\n")

def main():
    now = int(time.time())
    o = load_outcomes()
    wr = float(o.get("winrate",0.0) or 0.0)
    pf = float(o.get("payoff",0.0) or 0.0)
    n  = int(o.get("closed_trades",0) or 0)

    need_hold = (n >= MIN_CLOSED) and ((wr < WINRATE_MIN) or (pf < PAYOFF_MIN))
    reason = ""
    if n < MIN_CLOSED:
        reason = f"warmup_n<{MIN_CLOSED}"
    elif need_hold:
        conds=[]
        if wr < WINRATE_MIN: conds.append(f"wr {wr:.2f}<{WINRATE_MIN:.2f}")
        if pf < PAYOFF_MIN:  conds.append(f"payoff {pf:.2f}<{PAYOFF_MIN:.2f}")
        reason = "; ".join(conds)

    # hysterese: hvis hold finnes, ikke slipp før cooldown
    if HOLD.exists():
        try:
            ts=int(HOLD.read_text().split("|",1)[0])
        except Exception: ts=now
        if not need_hold and (now - ts) < COOLDOWN_S:
            # fortsatt hold pga cooldown
            write_prom(1, "cooldown", now)
            return
        if need_hold:
            # oppdater årsak/tid
            HOLD.write_text(f"{now}|{reason}")
            write_prom(1, reason, now)
            return
        # slippe
        HOLD.unlink(missing_ok=True)
        write_prom(0, "released", now)
        return

    # ingen hold fra før
    if need_hold:
        HOLD.write_text(f"{now}|{reason}")
        write_prom(1, reason, now)
    else:
        write_prom(0, "ok", now)

if __name__ == "__main__":
    main()
