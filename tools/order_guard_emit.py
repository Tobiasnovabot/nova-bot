#!/usr/bin/env python3
import os, sys, json, time, fcntl
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG  = ROOT/"data"/"order_gate.log"
PROM = ROOT/"metrics"/"novax_order_guard.prom"
PROM.parent.mkdir(parents=True, exist_ok=True)
LOG.parent.mkdir(parents=True, exist_ok=True)

def atomic_write(path: Path, data: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data)
    os.replace(tmp, path)

def main():
    # argv: action symbol notional max min
    # action in {"capped","below_min","breach_allowed"}
    try:
        action  = sys.argv[1]
        symbol  = sys.argv[2]
        notional = float(sys.argv[3])
        max_n   = float(sys.argv[4])
        min_n   = float(sys.argv[5])
    except Exception:
        print("usage: order_guard_emit.py <action> <symbol> <notional> <max> <min>", file=sys.stderr)
        sys.exit(2)

    ts_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    line = f"{ts_iso} action={action} symbol={symbol} notional={notional:.2f} max={max_n:.2f} min={min_n:.2f}\n"
    with open(LOG, "a") as fh:
        fh.write(line)

    # last kjente stats
    stats = {"capped":0,"below_min":0,"breach_allowed":0}
    if PROM.exists():
        try:
            # grov lesing: tell siste tall fra fil hvis finnes
            txt = PROM.read_text()
            for key in stats:
                for l in txt.splitlines():
                    if l.startswith(f'novax_order_guard_total{{action="{key}"}}'):
                        stats[key] = int(l.rsplit(" ",1)[-1])
        except Exception:
            pass
    stats[action] = stats.get(action,0) + 1
    now_ms = int(time.time()*1000)

    out = []
    out.append("# HELP novax_order_guard_total Total events by order notional guard.")
    out.append("# TYPE novax_order_guard_total counter")
    for k,v in stats.items():
        out.append(f'novax_order_guard_total{{action="{k}"}} {v} {now_ms}')
    out.append("# HELP novax_order_guard_last_notional Last seen order notional USD")
    out.append("# TYPE novax_order_guard_last_notional gauge")
    out.append(f"novax_order_guard_last_notional {notional:.2f} {now_ms}")
    out.append("# HELP novax_order_guard_limits Current min/max USD limits")
    out.append("# TYPE novax_order_guard_limits gauge")
    out.append(f'novax_order_guard_limits{{type="min"}} {min_n:.2f} {now_ms}')
    out.append(f'novax_order_guard_limits{{type="max"}} {max_n:.2f} {now_ms}')
    out.append("# HELP novax_order_guard_last_action Last action as gauge label=1")
    out.append("# TYPE novax_order_guard_last_action gauge")
    for k in ("capped","below_min","breach_allowed"):
        val = 1 if k==action else 0
        out.append(f'novax_order_guard_last_action{{action="{k}"}} {val} {now_ms}')
    atomic_write(PROM, "\n".join(out)+"\n")

if __name__ == "__main__":
    main()
