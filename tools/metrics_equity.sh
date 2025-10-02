#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
STATE="data/state.json"
OUT="metrics/nova_equity.prom"
mkdir -p metrics
eq=$(jq -r '.equity_usd // .equity // empty' "$STATE" 2>/dev/null || true)
[ -n "${eq:-}" ] || exit 0
ts=$(date +%s)
cat > "$OUT" <<EOF
# HELP nova_equity_usd Latest account equity in USD.
# TYPE nova_equity_usd gauge
nova_equity_usd $eq $((ts*1000))
EOF