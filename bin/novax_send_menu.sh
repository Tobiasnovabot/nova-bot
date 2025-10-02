#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; [ -f .env ] && . .env; set +a
: "${TELEGRAM_BOT_TOKEN:?}"; : "${TELEGRAM_CHAT_ID:?}"
read -r -d '' MENU <<'TXT'
**Kommandoliste**
/status – systemstatus
/pnl – PnL-oversikt
/pos – åpne posisjoner
/risk <1-30> – sett risk
/halt – stopp nye entries
/resume – fjern HALT
/restart_engine – restart engine
/stop_engine – stopp engine
/restart_tg – restart Telegram-kontroller
/heartbeat_on <min> – slå på heartbeat
/heartbeat_off – slå av heartbeat
/report day|week
/params list|get K|set K V|level N|preset N
/watch list|add SYM|rm SYM|bulk SYM1,SYM2|clear
/engine once|loop SEC|speed SEC
/train on|off
/bandit show|reset
/scores show|reset
/cfg save TAG | /cfg load TAG | /cfg diff A B
TXT
curl -fsS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d chat_id="${TELEGRAM_CHAT_ID}" -d parse_mode=Markdown \
  --data-urlencode text="$MENU" >/dev/null && echo "Menu sent."