#!/usr/bin/env bash
set -euo pipefail
source ${NOVA_HOME:-/home/nova/nova-bot}/ops/lib.sh
ROOT="${NOVA_HOME:-/home/nova/nova-bot}"
OUT="$ROOT/data/metrics.prom"

PID="$(pgrep -f 'nova.engine.run' | head -1 || true)"
RSS=0
if [[ -n "$PID" && -r "/proc/$PID/status" ]]; then
  RSS_KB=$(awk '/VmRSS:/ {print $2}' "/proc/$PID/status")
  RSS=$((RSS_KB*1024))
fi

TRADES=0
if [[ -f "$ROOT/data/trades.json" ]]; then
  TRADES=$(python3 - <<'PY'
import json,sys,pathlib
p=pathlib.Path('data/trades.json')
try:
  a=json.loads(p.read_text() or "[]")
  print(len(a))
except Exception as e:
print(0)
PY
)
fi

read -r EQUITY LASTTICK WATCHN <<EOF
$(python3 - <<'PY'
import json,pathlib
d=pathlib.Path('data')
s={}
try: s=json.loads((d/'state.json').read_text() or "{}")
except Exception as e:
s={}
eq=0.0
try:
  ej=json.loads((pathlib.Path('data')/'equity.json').read_text() or "[]")
  if ej and isinstance(ej,list):
    eq = ej[-1].get("equity_usd",0.0) or ej[-1].get("equity",0.0) or 0.0
except Exception as e:
pass
lt = s.get("last_tick_ts",0) or 0
wn = len(s.get("watch",[]) or s.get("universe_cache",{}).get("symbols",[]))
print(eq, lt, wn)
PY
)
EOF

DISK_FREE=$(df -P /home | awk 'NR==2{print $4*1024}')
TS=$(date +%s)

cat > "$OUT" <<MET
# HELP novax_trades_total Count of recorded trades
# TYPE novax_trades_total counter
novax_trades_total ${TRADES}

# HELP novax_equity_usd Current equity in USD (if tracked)
# TYPE novax_equity_usd gauge
novax_equity_usd ${EQUITY:-0}

# HELP novax_watch_count Number of symbols being watched
# TYPE novax_watch_count gauge
novax_watch_count ${WATCHN:-0}

# HELP novax_process_memory_bytes Resident set size of NovaX process
# TYPE novax_process_memory_bytes gauge
novax_process_memory_bytes ${RSS}

# HELP novax_disk_free_bytes Free bytes on /home
# TYPE novax_disk_free_bytes gauge
novax_disk_free_bytes ${DISK_FREE}

# HELP novax_last_tick_ts Last engine tick timestamp (from state.json)
# TYPE novax_last_tick_ts gauge
novax_last_tick_ts ${LASTTICK:-0}

# HELP novax_metrics_timestamp Export time
# TYPE novax_metrics_timestamp gauge
novax_metrics_timestamp ${TS}
MET