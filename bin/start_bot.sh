#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
. .venv/bin/activate
export PYTHONPATH="$PWD"
export TELEGRAM_DISABLED=1
export TRADING_MODE=${TRADING_MODE:-paper}
exec python -u bot_main.py run
