#!/usr/bin/env bash
set -euo pipefail
ENV="${NOVA_HOME:-/home/nova/nova-bot}/.env"; [ -f "$ENV" ] && set -a && source "$ENV" && set +a
UNIT="novax.service"
API="https://api.telegram.org/bot${TG_KEY:-}"

msg(){ [[ -n "${TG_KEY:-}" && -n "${TG_CHAT:-}" ]] && curl -s -X POST "$API/sendMessage" -d chat_id="$TG_CHAT" --data-urlencode text="$1" >/dev/null || true; }

fix(){
  [[ -n "${TG_KEY:-}" ]] && curl -s "$API/deleteWebhook?drop_pending_updates=true" >/dev/null || true
  sudo systemctl disable --now novax-tg.service 2>/dev/null || true
  pkill -f 'nova.telegram_ctl.run' 2>/dev/null || true
  pkill -f 'getUpdates' 2>/dev/null || true
  sudo systemctl restart "$UNIT" || true
}

if journalctl -u "$UNIT" --since -2min -o cat 2>/dev/null | grep -qE '409 Client Error.*getUpdates'; then
  fix; msg "TG-watchdog: 409 Conflict – ryddet og restartet."; exit 0
fi
dups=$(pgrep -af 'getUpdates|nova\.telegram_ctl\.run' | wc -l || true)
if (( dups>0 )); then fix; msg "TG-watchdog: fant ${dups} ekstra pollere – ryddet og restartet."; fi