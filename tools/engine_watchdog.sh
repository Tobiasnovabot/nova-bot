#!/usr/bin/env bash
set -euo pipefail
ENV="${NOVA_HOME:-/home/nova/nova-bot}/.env"; [ -f "$ENV" ] && set -a && source "$ENV" && set +a
UNIT="novax.service"
THRESH="${ENGINE_HEARTBEAT_MAX_AGE_MINUTES:-5}"

tg(){ [[ -n "${TG_KEY:-}" && -n "${TG_CHAT:-}" ]] && curl -s -X POST "https://api.telegram.org/bot${TG_KEY}/sendMessage" -d chat_id="$TG_CHAT" --data-urlencode text="$1" >/dev/null || true; }

# Finn siste heartbeat timestamp via journalctl short-unix (gir epoch i kol 1)
line=$(journalctl -u "$UNIT" --grep "engine heartbeat" -n 1 --no-pager --output=short-unix | tail -n1 || true)
if [[ -z "$line" ]]; then
  sudo systemctl restart "$UNIT"; tg "Heartbeat: ingen logger – restartet $UNIT"; exit 0
fi
last_ts=$(awk '{print int($1)}' <<<"$line")
now=$(date +%s); max=$((THRESH*60)); age=$((now-last_ts))
if (( age>max )); then sudo systemctl restart "$UNIT"; tg "Heartbeat: stille i ${age}s (>${max}s). Restart."; fi