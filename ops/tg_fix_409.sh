#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}
set -a; source ./.env; set +a

echo "Deaktiverer ev. separat TG-service…"
sudo systemctl disable --now novax-tg.service 2>/dev/null || true
pkill -f 'nova.telegram_ctl.run' 2>/dev/null || true
pgrep -af 'getUpdates|telegram' || true

echo "Nullstiller webhook…"
curl -s "https://api.telegram.org/bot${TG_KEY}/getWebhookInfo"
curl -s "https://api.telegram.org/bot${TG_KEY}/deleteWebhook?drop_pending_updates=true"
echo
echo "Restart engine (innebygd TG-poll)…"
sudo systemctl restart novax.service
echo "Sjekk logg (Ctrl+C for å avslutte):"
sudo journalctl -u novax.service -f -o cat | grep -E '\[tg\]|409|engine|watchN' || true