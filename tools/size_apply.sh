#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

JSON="data/sizing.json"
ENVF="data/size_override.env"
APPLIED="data/size_applied.txt"
LOG="data/size_apply.log"
THRESH_PCT="${SIZING_RESTART_THRESH_PCT:-20}"   # restart hvis endring > 20%
THRESH_USD="${SIZING_RESTART_THRESH_USD:-25}"   # eller > 25 USD
COOLDOWN_S="${SIZING_RESTART_COOLDOWN_S:-900}"  # 15 min

ts() { date -Is; }

[ -f "$JSON" ] || { echo "$(ts) no sizing.json" >>"$LOG"; exit 0; }
NEW=$(jq -r '.size_usd // 0' "$JSON" 2>/dev/null || echo 0)
[ -n "$NEW" ] && [ "$NEW" != "0" ] || { echo "$(ts) no size_usd" >>"$LOG"; exit 0; }

mkdir -p data
printf "BASE_USDT=%.2f\n" "$NEW" > "$ENVF"

OLD=0
[ -f "$APPLIED" ] && OLD=$(cat "$APPLIED" 2>/dev/null || echo 0)
DELTA_ABS=$(python - <<PY
n=$NEW;o=$OLD
print(abs(n-o))
PY
)
DELTA_PCT=$(python - <<PY
n=$NEW;o=$OLD
print(0 if o==0 else abs(n-o)/o*100.0)
PY
)

# Cooldown
NOW=$(date +%s); LAST=0
[ -f "$APPLIED" ] && LAST=$(stat -c %Y "$APPLIED" 2>/dev/null || echo 0)
ELAPSED=$((NOW-LAST))
if [ "$ELAPSED" -lt "$COOLDOWN_S" ]; then
  echo "$(ts) cooldown $ELAPSED<$COOLDOWN_S; applied=$OLD new=$NEW" >>"$LOG"
  exit 0
fi

# Vurder restart
NEED=0
awk -v a="$DELTA_ABS" -v p="$DELTA_PCT" -v ta="$THRESH_USD" -v tp="$THRESH_PCT" 'BEGIN{exit ! (a>ta || p>tp)}' && NEED=1 || NEED=0
if [ "$NEED" = "1" ]; then
  echo "$NEW" > "$APPLIED"
  if systemctl is-active --quiet novax.service; then
    if sudo -n systemctl restart novax.service; then
      echo "$(ts) restart_ok old=$OLD new=$NEW d_abs=$DELTA_ABS d_pct=$DELTA_PCT" >>"$LOG"
    else
      echo "$(ts) restart_failed old=$OLD new=$NEW" >>"$LOG"
    fi
  else
    echo "$NEW" > "$APPLIED"
    echo "$(ts) engine_inactive; applied_no_restart new=$NEW" >>"$LOG"
  fi
else
  echo "$NEW" > "$APPLIED"
  echo "$(ts) no_restart old=$OLD new=$NEW d_abs=$DELTA_ABS d_pct=$DELTA_PCT" >>"$LOG"
fi
exit 0