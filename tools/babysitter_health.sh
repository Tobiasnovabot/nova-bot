#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "[babysitter] run"
./.venv/bin/python tools/position_babysitter.py || python tools/position_babysitter.py || true
tail -n 5 data/babysitter.log 2>/dev/null || true