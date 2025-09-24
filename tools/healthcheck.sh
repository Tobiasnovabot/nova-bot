#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

bad=0
check() {
  local u="$1"
  if ! systemctl is-active "$u" >/dev/null; then
    echo "BAD: $u inactive"
    bad=1
  fi
  systemctl is-enabled "$u" >/dev/null 2>&1 || echo "WARN: $u not enabled"
}

for u in \
  novax.service \
  novax-risk-guard.service \
  novax-metrics.timer \
  novax-babysitter.timer \
  novax-heartbeat-guard.timer \
  novax-liquidity-gate.timer \
  novax-pos-spread.timer \
  novax-trades-agg.timer \
  novax-healthcheck.timer \
  novax-backup.timer \
  novax-daily-report.timer
do
  check "$u"
done

mkdir -p metrics
ts_ms=$(( $(date +%s) * 1000 ))
ok=$(( bad==0 ? 1 : 0 ))
cat > metrics/novax_health.prom <<EOF
# HELP novax_health_ok 1 if all services healthy
# TYPE novax_health_ok gauge
novax_health_ok $ok $ts_ms
EOF

if [ $bad -eq 0 ]; then
  echo "healthcheck: OK"
else
  msg="NovaX healthcheck: FAILURE on $(hostname). See journalctl -u novax-healthcheck.service"
  echo "$msg"
  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
    curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d chat_id="$TELEGRAM_CHAT_ID" -d text="$msg" >/dev/null || true
  fi
  exit 1
fi