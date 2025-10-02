#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; [ -f .env ] && . .env; set +a
: "${TELEGRAM_BOT_TOKEN:?mangler TELEGRAM_BOT_TOKEN i .env}"
: "${TELEGRAM_CHAT_ID:?mangler TELEGRAM_CHAT_ID i .env}"

MSG="$(bash bin/novax_status.sh)"
curl -fsS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d chat_id="${TELEGRAM_CHAT_ID}" \
  -d parse_mode="Markdown" \
  --data-urlencode text="$MSG" >/dev/null
echo "Sent."