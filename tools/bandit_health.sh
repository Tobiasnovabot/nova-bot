#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "[bandit] run"
./.venv/bin/python tools/bandit_train.py || python tools/bandit_train.py || true
tail -n 5 data/bandit.log 2>/dev/null || true
test -f data/strategy_policy.json && jq -r '.weights|to_entries|sort_by(.value)|reverse|.[0:10]' data/strategy_policy.json || true
test -f data/strategy_blocklist.json && echo "blocked: $(jq -r '.|join(",")' data/strategy_blocklist.json)" || true