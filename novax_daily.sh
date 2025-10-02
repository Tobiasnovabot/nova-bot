#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${NOVA_HOME:-/home/nova/nova-bot}"
DATA_DIR="$APP_DIR/data"
LOG="$DATA_DIR/logs/daily_$(date +%F).log"
ENV="$APP_DIR/.env"

# last .env for TG vars
set -a; [ -f "$ENV" ] && . "$ENV"; set +a
say(){ echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }

# 1) healthcheck
say "healthcheck start"
if [ -x "$APP_DIR/nova_healthcheck.sh" ]; then
  "$APP_DIR/nova_healthcheck.sh" >>"$LOG" 2>&1 || true
fi

# 2) backup med rotasjon (7 dager)
mkdir -p "$DATA_DIR/backups"
tar czf "$DATA_DIR/backups/nova_$(date +%F_%H%M).tgz" -C "$DATA_DIR" \
  state.json equity.json trades.json 2>/dev/null || true
find "$DATA_DIR/backups" -type f -mtime +7 -delete

# 3) diskplass-vakt
FREE_PCT=$(df -P "$DATA_DIR" | awk 'NR==2{print 100-$5}')
if [ "${FREE_PCT:-100}" -lt 10 ]; then
  MSG="NovaX: Lav diskplass! Ledig ${FREE_PCT}% på $(df -P "$DATA_DIR" | awk 'NR==2{print $1":"$6}')"
  say "$MSG"
  if [ -n "${TG_KEY:-}" ] && [ -n "${TG_CHAT:-}" ]; then
    curl -s "https://api.telegram.org/bot${TG_KEY}/sendMessage" \
      -d chat_id="$TG_CHAT" -d text="$MSG" >/dev/null || true
  fi
fi

# 4) kort status til Telegram
if [ -n "${TG_KEY:-}" ] && [ -n "${TG_CHAT:-}" ]; then
  curl -s "https://api.telegram.org/bot${TG_KEY}/sendMessage" \
    -d chat_id="$TG_CHAT" \
    -d text="NovaX: Daglig sjekk fullført ✅ ($(date +%F))" >/dev/null || true
fi
say "done"