#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./.venv/bin/python ./tools/trade_outcomes.py || python ./tools/trade_outcomes.py