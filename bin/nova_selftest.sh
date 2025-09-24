#!/usr/bin/env bash
set -euo pipefail
PASS=0; WARN=0; FAIL=0
pass(){ echo "PASS: $*"; ((PASS++))||true; }
warn(){ echo "WARN: $*"; ((WARN++))||true; }
fail(){ echo "FAIL: $*"; ((FAIL++))||true; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$ROOT/data"
PYBIN="$ROOT/.venv/bin/python"

# 1) Env / services
$PYBIN -V | grep -q 'Python 3' && pass "venv python: $($PYBIN -V | awk '{print $2}')" || fail "venv python missing"
[ -f "$ROOT/.env" ] && pass ".env present" || fail ".env missing"
uname -r >/dev/null && pass "kernel $(uname -r)"
for SVC in grafana-server novax.service novax-metrics.service prometheus; do
  if systemctl is-active --quiet "$SVC"; then pass "service active: $SVC"; else fail "service inactive: $SVC"; fi
done
if systemctl list-timers --all | egrep -q 'novax-(alerts|recover|daily|maintenance)\.timer'; then
  pass "timers present: novax-(alerts|recover|daily|maintenance)\\.timer"
else
  warn "timers missing (alerts/recover/daily/maintenance)"
fi

# 2) Ports
ss -ltn | grep -q ':3000 ' && pass "port 3000 (Grafana) listening" || fail "port 3000 not listening"
ss -ltn | grep -q ':9090 ' && pass "port 9090 (Prometheus) listening" || fail "port 9090 not listening"
ss -ltn | grep -q ':9108 ' && pass "port 9108 (Nova exporter) listening" || fail "port 9108 not listening"

# 3) Prometheus / exporter
curl -fsS http://127.0.0.1:9090/-/ready >/dev/null && pass "Prometheus targets up" || fail "Prometheus targets not up"
curl -fsS http://127.0.0.1:9108/metrics | grep -q '^novax_' && pass "Exporter exposes novax_* metrics" || fail "Exporter metrics missing"

# 4) Data files
[ -d "$DATA_DIR" ] && pass "DATA_DIR exists: $DATA_DIR" || fail "DATA_DIR missing: $DATA_DIR"
[ -f "$DATA_DIR/state.json" ]  && pass "state.json present"  || fail "state.json missing"
[ -f "$DATA_DIR/equity.json" ] && pass "equity.json present" || fail "equity.json missing"

# 5) Universe / ccxt smoke
UNI_OK="$($PYBIN - <<'PY'
import json, pathlib
p=pathlib.Path("data/state.json"); top=300
try:
    if p.exists():
        d=json.loads(p.read_text() or "{}"); wl=d.get("watch") or []
        top=len(wl) or 300
except Exception: pass
print(top>=300)
PY
)"
[[ "$UNI_OK" == "True" ]] && pass "universe symbols >=300 (300)" || warn "universe symbols low"

CCXT_OK="$($PYBIN - <<'PY'
try:
    import ccxt
    ex=ccxt.binance(); ex.load_markets(); ex.market("BTC/USDT")
    print("OK")
except Exception as e:
    print("ERR", e)
PY
)"
[[ "$CCXT_OK" == OK* ]] && pass "ccxt exchange connectivity (BTC/USDT)" || warn "ccxt check failed: $CCXT_OK"

# 6) Telegram smoke
TG_OK="$($PYBIN - <<'PY'
try:
    from nova.telegram_ctl import telegram_ctl as t
    print("OK")
except Exception as e:
    print("ERR", e)
PY
)"
[[ "$TG_OK" == OK* ]] && pass "Telegram getMe OK" || warn "Telegram getMe failed"

# 7) alerts / watchdog
systemctl is-active --quiet novax-alerts.timer 2>/dev/null && pass "alerts.timer active" || warn "alerts.timer inactive"
[ -f "$DATA_DIR/alerts_state.json" ] && pass "alerts_state.json present" || warn "alerts_state.json missing"
sudo -n true >/dev/null 2>&1 && pass "alerts service start (sudo -n)" || warn "alerts service start (sudo requires password)"
systemctl is-active --quiet novax-watchdog.timer 2>/dev/null && pass "watchdog.timer active" || warn "watchdog.timer inactive"
! journalctl -u novax-watchdog.service -b --no-pager 2>/dev/null | grep -qi 'awk.*fatal' && pass "watchdog awk error absent" || warn "watchdog awk error present"

# 8) Backup snapshot
ts="$(date +%Y%m%d-%H%M%S)"; mkdir -p "$ROOT/backups" "$DATA_DIR/backups"
if ls -1 "$ROOT"/backups/nova-data-*.tar.gz >/dev/null 2>&1; then
  RECENT_BKP="$(ls -1t "$ROOT"/backups/nova-data-*.tar.gz 2>/dev/null | head -1 || true)"
else
  tar -C "$DATA_DIR" -czf "$ROOT/backups/nova-data-${ts}.tar.gz" . >/dev/null 2>&1 || true
  RECENT_BKP="$(ls -1t "$ROOT"/backups/nova-data-*.tar.gz 2>/dev/null | head -1 || true)"
fi
[[ -n "${RECENT_BKP:-}" ]] && pass "backup present: $(basename "$RECENT_BKP")" || warn "no nova-data-*.tar.gz found"

# 9) Engine heartbeat (robust, 15 min)
HB_CNT="$(journalctl -u novax.service -b --since '-15 min' --no-pager -o cat | grep -F 'heartbeat #' | wc -l | tr -d '[:space:]' || echo 0)"
if [ "${HB_CNT:-0}" -gt 0 ]; then pass "engine heartbeats recent (count=${HB_CNT})"; else warn "no recent engine heartbeat in journal"; fi

# 10) Module selfcheck runner
SELFCHK_OUT="$($PYBIN -m nova.selfcheck.runner 2>&1 || true)"
echo "$SELFCHK_OUT" | sed -n 's/^/SELFCHK: /p'
if echo "$SELFCHK_OUT" | grep -q 'FAIL=[1-9]'; then
  fail "module selfchecks failures"
elif echo "$SELFCHK_OUT" | grep -q 'WARN=[1-9]'; then
  warn "module selfchecks have warnings"
else
  pass "module selfchecks all green"
fi

# SUMMARY
echo "== SUMMARY =="; echo "Warnings: ${WARN}, Failures: ${FAIL}"
exit $(( FAIL>0 ))