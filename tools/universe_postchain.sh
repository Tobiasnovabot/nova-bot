#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
VENV_PY="${VENV_PY:-./.venv/bin/python}"
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# 1) Postfilter til trading-børs
[ -x tools/universe_postfilter.py ] && ./tools/universe_postfilter.py || true
# 2) Likviditet + spread
[ -x tools/universe_lq_filter.py ] && ./tools/universe_lq_filter.py || true
# 3) Bandit-vekting
[ -x tools/universe_bandit_weight.py ] && ./tools/universe_bandit_weight.py || true
# 4) Varsle hvis under mål
CNT=$(jq -r '.symbols|length' data/universe.json 2>/dev/null || echo 0)
TARGET="${TOP_N:-300}"
if [ "$CNT" -lt "$TARGET" ]; then
  MSG="[universe] under mål etter kjede: $CNT/$TARGET"
  [ -x ./alerts/trade_to_tg.sh ] && ./alerts/trade_to_tg.sh "$MSG" || echo "$MSG"
fi