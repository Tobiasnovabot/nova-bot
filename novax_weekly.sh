#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${NOVA_HOME:-/home/nova/nova-bot}"
ENV="$APP_DIR/.env"
set -a; [ -f "$ENV" ] && . "$ENV"; set +a
exec "$APP_DIR/.venv/bin/python" "$APP_DIR/novax_weekly_report.py"