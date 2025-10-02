#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${NOVA_HOME:-/home/nova/nova-bot}"
DATA_DIR="$APP_DIR/data"
LOG_DIR="$DATA_DIR/logs"

echo "[maint] start $(date -Iseconds)"
# Logrotate for NovaX-logger
if [ -x /usr/sbin/logrotate ] && [ -f /etc/logrotate.d/novax ]; then
  /usr/sbin/logrotate -f /etc/logrotate.d/novax || true
fi

# Slett gamle backup-filer (>14 dager)
find "$DATA_DIR/backups" -type f -mtime +14 -print -delete 2>/dev/null || true

# Rydd ccxt-cache (>7 dager)
find /home/nova/.cache/ccxt -type f -mtime +7 -print -delete 2>/dev/null || true

# Rydd midlertidige filer
rm -rf "$DATA_DIR/tmp/"* 2>/dev/null || true

# Komprimer store løse loggfiler hvis noen fortsatt er åpne
find "$LOG_DIR" -type f -name "*.log" -size +50M -exec gzip -f {} \; 2>/dev/null || true

echo "[maint] done  $(date -Iseconds)"