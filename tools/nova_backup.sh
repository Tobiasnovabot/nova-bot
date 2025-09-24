#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
STAMP=$(date +%Y%m%d-%H%M)
OUT="backups/nova-backup-$STAMP.tar.gz"
mkdir -p backups
tar -czf "$OUT" \
  --exclude='data/logs/*' \
  --exclude='data/*.lock' \
  .env data/ metrics/ tools/ nova/ prometheus.yml
echo "$OUT"

if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="$TELEGRAM_CHAT_ID" -d text="NovaX backup: $(basename "$OUT")" >/dev/null || true
fi