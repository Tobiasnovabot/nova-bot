#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

STATE="data/state.json"
HOLD="data/dd_hold.lock"
LOG="data/heartbeat_guard.log"

# respekter DD-hold
if [ -f "$HOLD" ]; then
  echo "$(date -Is) hold_present skip" | tee -a "$LOG"
  exit 0
fi

test -f "$STATE" || { echo "$(date -Is) no state.json" | tee -a "$LOG"; exit 0; }

AGE=$(jq -r '.heartbeat_age_s // 999999' "$STATE" 2>/dev/null || echo 999999)
THRESH="${HEARTBEAT_MAX_AGE_S:-180}"
echo "$(date -Is) age=${AGE}s thresh=${THRESH}s" | tee -a "$LOG"

if [ "$AGE" -gt "$THRESH" ]; then
  msg="Heartbeat stale: ${AGE}s > ${THRESH}s. Restarting novax.service"
  ( command -v ./alerts/trade_to_tg.sh >/dev/null && timeout 5s ./alerts/trade_to_tg.sh "$msg" >>"$LOG" 2>&1 ) || true
  if sudo -n systemctl restart novax.service 2>>"$LOG"; then
    echo "$(date -Is) restart_ok" | tee -a "$LOG"
  else
    echo "$(date -Is) restart_failed" | tee -a "$LOG"
  fi
else
  echo "$(date -Is) ok" | tee -a "$LOG"
fi
exit 0