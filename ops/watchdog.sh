#!/usr/bin/env bash
set -euo pipefail

HB_MAX_AGE="${HB_MAX_AGE:-600}"     # sekunder
COOLDOWN="${COOLDOWN:-900}"         # 15 min
STATE="${NOVA_HOME:-/home/nova/nova-bot}/data/watchdog_state.json"
TG="${NOVA_HOME:-/home/nova/nova-bot}/alerts/novax_alerts.py"
METRICS="http://127.0.0.1:9108/metrics"

metrics_alive(){ curl -fsS "$METRICS" | grep -q '^novax_watch_count'; }
send_tg(){ ${NOVA_HOME:-/home/nova/nova-bot}/.venv/bin/python -u "$TG" --msg "$1" || echo "$1"; }

cooldown_ok(){
  local action="$1" now_s ts
  now_s=$(date +%s)
  ts=$( [ -f "$STATE" ] && jq -r ".last[\"$action\"]" "$STATE" 2>/dev/null || echo null )
  [ -z "$ts" ] || [ "$ts" = null ] && return 0
  [ $(( now_s - ts )) -ge "$COOLDOWN" ]
}
set_last(){
  local action="$1" now_s tmp
  now_s=$(date +%s)
  tmp=$(mktemp)
  if [ -f "$STATE" ]; then
    jq --arg a "$action" --argjson t "$now_s" '.last=(.last//{})|.last[$a]=$t' "$STATE" >"$tmp"
  else
    printf '{"last":{"%s":%s}}\n' "$action" "$now_s" >"$tmp"
  fi
  mv "$tmp" "$STATE"
}

main(){
  mkdir -p "$(dirname "$STATE")"

  # Finnes heartbeat i siste HB_MAX_AGE sek?
  if journalctl -u novax.service -b --since "-${HB_MAX_AGE} sec" --no-pager | grep -q 'heartbeat #'; then
    echo "PASS: heartbeat i siste ${HB_MAX_AGE}s"
    exit 0
  fi

  # Fallback: metrics oppe?
  if metrics_alive; then
    action="warn"; reason="journal stille >${HB_MAX_AGE}s, men metrics OK"
  else
    action="restart"; reason="journal stille >${HB_MAX_AGE}s og metrics mangler"
  fi

  # Throttle TG
  if cooldown_ok "$action"; then
    send_tg "Watchdog: ${reason}"
    set_last "$action"
  fi

  # Restart kun ved 'restart'
  if [ "${action}" = "restart" ]; then
    systemctl try-restart novax.service || true
    echo "ACTION: restart novax.service pga ${reason}"
  else
    echo "WARN: ${reason}"
  fi
}
main