#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
LOG="data/arm_switch.log"
MODE="${1:-}"   # "paper" | "live"

die(){ echo "$1" | tee -a "$LOG"; exit 1; }

test -n "$MODE" || die "bruk: tools/arm_switch.sh [paper|live]"

# 0) posisjoner må være flate for live
if [ "$MODE" = "live" ]; then
  pc=$(jq -r '.positions|length? // 0' data/state.json 2>/dev/null || echo 0)
  [ "$pc" -eq 0 ] || die "posisjoner ikke flate ($pc)"
fi

# 1) oppdater .env (PAPER_TRADING=0/1)
ENVF=".env"
touch "$ENVF"
if [ "$MODE" = "live" ]; then
  sed -i 's/^PAPER_TRADING=.*/PAPER_TRADING=0/' "$ENVF" || true
  grep -q '^PAPER_TRADING=' "$ENVF" || echo 'PAPER_TRADING=0' >> "$ENVF"
else
  sed -i 's/^PAPER_TRADING=.*/PAPER_TRADING=1/' "$ENVF" || true
  grep -q '^PAPER_TRADING=' "$ENVF" || echo 'PAPER_TRADING=1' >> "$ENVF"
fi

# 2) enkel balanse-sjekk hvis ccxt finnes
if python -c "import ccxt" 2>/dev/null; then
  python - <<'PY' || true
import os, json, pathlib
exname=os.getenv("TRADING_EXCHANGE", os.getenv("EXCHANGE","binance")).lower()
try:
  import ccxt
  ex=getattr(ccxt, exname)()
  bal=ex.fetch_balance()
  free=bal.get("free",{}).get("USDT") or 0
  print(f"[arm] free_usdt={free}")
except Exception as e:
  print("[arm] balance_check_error:", e)
PY
fi

# 3) restart motor
sudo -n systemctl restart novax.service || true
echo "$(date -Is) mode=$MODE" | tee -a "$LOG"

# 4) varsle
if [ -x ./alerts/trade_to_tg.sh ]; then ./alerts/trade_to_tg.sh "[ARM] mode=$MODE applied" || true; fi