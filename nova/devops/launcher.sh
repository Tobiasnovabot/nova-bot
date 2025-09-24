#!/bin/bash
set -euo pipefail

# Aktiver venv om den finnes
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

# Sett opp loggmappe
mkdir -p "$NOVA_HOME/logs"

# Roter logg: behold siste 5
if [ -f "$NOVA_HOME/logs/run.out" ]; then
  ts=$(date +%Y%m%d_%H%M%S)
  mv "$NOVA_HOME/logs/run.out" "$NOVA_HOME/logs/run_$ts.out"
  ls -t "$NOVA_HOME/logs"/run_*.out | tail -n +6 | xargs -r rm --
fi

# Start engine
exec python -m nova.engine.run "$@" > "$NOVA_HOME/logs/run.out" 2>&1