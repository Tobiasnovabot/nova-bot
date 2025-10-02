#!/usr/bin/env bash
set -euo pipefail
send(){ curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
 -d chat_id="$TELEGRAM_CHAT_ID" -d text="$1" >/dev/null || true; }
fail=()
systemctl is-active --quiet nova-engine || fail+=("nova-engine down")
ss -ltn | grep -q ':9093' || fail+=("alertmanager not listening")
[ -f ${NOVA_HOME:-/home/nova/nova-bot}/equity.json ] || fail+=("equity.json missing")
if [ ${#fail[@]} -gt 0 ]; then
  systemctl restart nova-engine || true
  send "Watchdog: ${fail[*]} -> attempted restart"
fi