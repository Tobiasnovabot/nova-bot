#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}
source .env
STATE=data/state.json
SIGDIR=data/signals
mkdir -p "$SIGDIR"

# signal-filer:
#   signals/arm_live.request    -> forespørsel om live
#   signals/arm_live.confirm    -> bekreftelse (andre person)
#   signals/arm_live.commit     -> (skrives av dette scriptet etter dry-run)
#   signals/kill_switch         -> global av-knapp (paper tvinges)
touch "$STATE"
now(){ date +%s; }

if [[ -f "$SIGDIR/kill_switch" ]]; then
  jq '."mode"="paper" | ."bot_enabled"=false' "$STATE" 2>/dev/null | tee "$STATE" >/dev/null
  echo "[failsafe] kill_switch aktivert -> MODE=paper, bot_enabled=false"
  exit 0
fi

if [[ -f "$SIGDIR/arm_live.request" ]]; then
  req_ts=$(stat -c %Y "$SIGDIR/arm_live.request" || echo 0)
  age=$(( $(now) - req_ts ))
  if [[ $age -gt ${FAILSAFE_ARM_WINDOW_SECS:-120} ]]; then
    echo "[failsafe] request er for gammel ($age s) -> avviser"
    rm -f "$SIGDIR/arm_live.request"
    exit 0
  fi
  if [[ -f "$SIGDIR/arm_live.confirm" ]]; then
    # dry-run periode før live
    echo "[failsafe] bekreftet -> dry-run i ${DRY_RUN_SECS:-300}s"
    sleep "${DRY_RUN_SECS:-300}"
    jq '."mode"="live" | ."bot_enabled"=true' "$STATE" 2>/dev/null | tee "$STATE" >/dev/null
    echo "[failsafe] LIVE aktivert"
    rm -f "$SIGDIR/arm_live.request" "$SIGDIR/arm_live.confirm"
    date > "$SIGDIR/arm_live.commit"
  else
    echo "[failsafe] venter på bekreftelse (arm_live.confirm)"
  fi
fi