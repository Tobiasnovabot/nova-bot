#!/usr/bin/env bash
set -euo pipefail
BASE="${NOVA_HOME:-/home/nova/nova-bot}"
ENV="${BASE}/.env"
DATA="${BASE}/data"
UNIT="novax.service"
LOG_TAG="[watchdog]"

[ -f "$ENV" ] && set -a && source "$ENV" && set +a

# --- parametre (kan overrides i .env) ---
HEARTBEAT_GRACE_SEC="${HEARTBEAT_GRACE_SEC:-180}"   # hvor lenge uten heartbeat før restart
MAX_MEM_MB="${WATCHDOG_MAX_MEM_MB:-800}"            # restart hvis prosess > dette
EQUITY_STALE_HRS="${EQUITY_STALE_HRS:-24}"          # advarsel hvis equity/state eldre enn dette

ts_now="$(date +%s)"
ok=true
msg=()

# 0) Beskytt mot Telegram 409 (ingen andre long-polls)
bad=$(pgrep -af 'getUpdates|nova\.telegram_ctl\.run' | grep -v $$ || true)
if [[ -n "$bad" ]]; then
  echo "$LOG_TAG kill stray TG pollers:"
  echo "$bad" | sed 's/^/  /'
  pkill -f 'getUpdates|nova\.telegram_ctl\.run' || true
  msg+=("🔧 Stoppet fremmed Telegram-poller (409-beskyttelse).")
fi

# 1) Finn pid og minnebruk
pid="$(pgrep -f 'python -u -m nova\.engine\.run' | head -1 || true)"
if [[ -z "${pid}" ]]; then
  ok=false
  msg+=("❌ Fant ikke engine-prosess – prøver restart.")
else
  mem_kb=$(awk '/VmRSS/{print $2}' /proc/"$pid"/status 2>/dev/null || echo 0)
  mem_mb=$(( mem_kb/1024 ))
  if (( mem_mb > MAX_MEM_MB )); then
    ok=false
    msg+=("⚠️ Minne høyt (${mem_mb}MB > ${MAX_MEM_MB}MB) – restart.")
  fi
fi

# 2) Sjekk heartbeat fra journal
# Ser etter siste linje som inneholder "engine heartbeat"
hb_line="$(journalctl -u ${UNIT} -n 200 --no-pager | grep -F 'engine heartbeat' | tail -1 || true)"
if [[ -z "$hb_line" ]]; then
  ok=false
  msg+=("❌ Fant ingen heartbeat i journal – restart.")
else
  # journalctl default: "Sep 02 21:13:26 host proc[pid]: LINE..."
  # Parse tidsstempel med 'date -d'
  hb_ts="$(echo "$hb_line" | awk '{print $1" "$2" "$3}')"
  hb_epoch="$(date -d "$hb_ts" +%s 2>/dev/null || echo 0)"
  age=$(( ts_now - hb_epoch ))
  if (( age > HEARTBEAT_GRACE_SEC )); then
    ok=false
    msg+=("⏳ Heartbeat gammelt (${age}s > ${HEARTBEAT_GRACE_SEC}s) – restart.")
  fi
fi

# 3) Sjekk ferskhet på equity/state
warn_files=()
for f in "${DATA}/equity.json" "${DATA}/state.json"; do
  [[ -f "$f" ]] || continue
  mt=$(stat -c %Y "$f" 2>/dev/null || echo 0)
  age_s=$(( ts_now - mt ))
  if (( age_s > EQUITY_STALE_HRS*3600 )); then
    warn_files+=("$(basename "$f") ~ $((age_s/3600))h")
  end
done
if (( ${#warn_files[@]} > 0 )); then
  msg+=("🟡 Filer ikke oppdatert nylig: ${warn_files[*]}")
fi

# 4) Tiltak
if [[ "$ok" = false ]]; then
  systemctl restart "${UNIT}"
  act="🔁 Restartet ${UNIT}"
else
  act="✅ OK"
fi

# 5) Telegram-rapport (hvis satt)
if [[ -n "${TG_KEY:-}" && -n "${TG_CHAT:-}" ]]; then
  text="${act}. $(printf '%s ' "${msg[@]}")"
  curl -s "https://api.telegram.org/bot${TG_KEY}/sendMessage" \
    -d chat_id="${TG_CHAT}" \
    -d disable_web_page_preview=true \
    -d text="$text" >/dev/null || true
fi

# 6) Konsoll-rapport (self-check)
echo "$LOG_TAG $act"
for m in "${msg[@]}"; do echo "$LOG_TAG $m"; done

exit 0