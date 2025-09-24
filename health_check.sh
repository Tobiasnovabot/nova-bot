#!/usr/bin/env bash
set -euo pipefail
ROOT="$HOME/nova-bot"; cd "$ROOT"
if [[ -f ".venv/bin/python" ]]; then PY=".venv/bin/python"; else PY="$(command -v python3)"; fi
echo "NovaX Health $(date)"
grep -E '^(EXCHANGE|MODE|ENGINE_LOOP_SEC|NOVA_HOME|TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID|TOP_N|WATCH_TOP_N|AUTO_WATCH|UNIVERSE_TTL_S|MAX_TRADE_USD|BUY_TRIG_PCT|TP_PCT|EXIT_AGE_S)=' .env || true
set -a; source .env; set +a
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"
echo
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
echo
$PY - <<'PY' || true
import os,json,pathlib
p=pathlib.Path(os.getenv("NOVA_HOME","data"))/"state.json"
s=json.loads(p.read_text() or "{}") if p.exists() else {}
print("state:", {"mode":s.get("mode"),"enabled":s.get("bot_enabled"),"equity":s.get("equity_usd"),
                "watch":len(s.get("watch",[])),"pos":len(s.get("positions",{}))})
PY
systemctl is-active --quiet novax.service && echo "novax: active" || echo "novax: down"
systemctl is-active --quiet novatg.service && echo "novatg: active" || echo "novatg: down"