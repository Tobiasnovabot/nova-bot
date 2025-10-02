#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

LOG="data/dd_reopen.log"
HOLD="data/dd_hold.lock"
COOLDOWN="${DD_REOPEN_COOLDOWN_S:-300}"   # 5m default
GRACE="${DD_REOPEN_GRACE_S:-30}"          # ekstra pust før start

ts(){ date -Is; }

# 1) hvis hold-fil finnes => gjør ingenting
if [ -f "$HOLD" ]; then
  echo "$(ts) hold_present skip" | tee -a "$LOG"
  exit 0
fi

# 2) sjekk sist breach (fra risk_dd_guard.log)
last=$(grep -E '\[DD GUARD\]' -n data/risk_dd_guard.log 2>/dev/null | tail -n1 | cut -d: -f1)
if [ -n "${last:-}" ]; then
  line=$(sed -n "${last}p" data/risk_dd_guard.log)
  # trekk ut tidspunktet (ISO først i linja)
  t_iso=$(echo "$line" | awk '{print $1}')
  t_s=$(date -d "$t_iso" +%s 2>/dev/null || echo 0)
  now=$(date +%s)
  age=$((now - t_s))
  if [ "$age" -lt "$COOLDOWN" ]; then
    left=$((COOLDOWN - age))
    echo "$(ts) cooldown ${age}<${COOLDOWN} (${left}s left)" | tee -a "$LOG"
    exit 0
  fi
fi

# 3) start motoren (med litt grace) + varsle
sleep "$GRACE"
msg="[DD REOPEN] cooldown ok. Starting novax.service"
if [ -x ./alerts/trade_to_tg.sh ]; then ./alerts/trade_to_tg.sh "$msg" || true; else echo "$msg"; fi
if systemctl is-active --quiet novax.service; then
  echo "$(ts) already_active" | tee -a "$LOG"
else
# DISABLED   sudo -n systemctl start novax.service && echo "$(ts) start_ok" | tee -a "$LOG" || echo "$(ts) start_failed" | tee -a "$LOG"
fi