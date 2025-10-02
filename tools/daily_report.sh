#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

prom_val () {
  # prom_val <metric_name> <file>
  local m="$1" f="$2"
  awk -v m="$m" '$1==m {print $2;found=1} END{if(!found) print "0"}' "$f" 2>/dev/null
}

EQ=$(jq -r '.equity_usd // .equity // 0' data/state.json 2>/dev/null || echo 0)
POS=$(jq -r '
  if (.positions|type)=="array" then (.positions|length)
  elif (.positions|type)=="object" then (to_entries|map(select(.value|tostring|test("^(closed|flat|0)$")|not))|length)
  else (.positions//0) end' data/state.json 2>/dev/null || echo 0)

DD1=$(prom_val novax_dd_1h_pct metrics/novax.prom)
DD24=$(prom_val novax_dd_24h_pct metrics/novax.prom)
TRC=$(prom_val novax_trades_closed_total metrics/novax_trades.prom)
WR=$(prom_val novax_trades_winrate metrics/novax_trades.prom)
PAY=$(prom_val novax_trades_payoff metrics/novax_trades.prom)

MSG=$(printf "NovaX Daily\nEquity: %.2f\nOpen pos: %s\nDD(1h/24h): %.2f%% / %.2f%%\nClosed trades: %s\nWinrate: %.2f\nPayoff: %.2f" \
     "$EQ" "$POS" "$DD1" "$DD24" "$TRC" "$WR" "$PAY")
echo "$MSG"

if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="$TELEGRAM_CHAT_ID" -d text="$MSG" >/dev/null || true
fi