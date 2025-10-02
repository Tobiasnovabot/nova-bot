#!/usr/bin/env bash
set -euo pipefail

echo "== NovaX ALERTS HEALTHCHECK =="
systemctl --quiet is-active novax.service && echo "PASS: novax.service aktiv" || echo "FAIL: novax.service"
systemctl --quiet is-active novax-alerts.timer && echo "PASS: alerts.timer aktiv" || echo "FAIL: alerts.timer"
systemctl --quiet is-active novax-alerts.service >/dev/null 2>&1 || echo "INFO: alerts.service kjører kun ved triggere (timer)"

# Tving en kjøring nå:
echo
echo "-- Kjør alerts manuelt --"
sudo -n systemctl start novax-alerts.service
sleep 1
journalctl -u novax-alerts.service -n 20 --no-pager || true

# Sjekk at state-fil finnes
STATE="${NOVA_HOME:-/home/nova/nova-bot}/data/alerts/alerts_state.json"
test -f "$STATE" && echo "PASS: state-fil finnes ($STATE)" || echo "WARN: mangler $STATE"