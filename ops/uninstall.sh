#!/usr/bin/env bash
set -euo pipefail
PURGE="${1:-}"

echo "Stopping/Disabling timers & services…"
sudo systemctl disable --now novax-watchdog.timer novax-metrics.timer novax-backup.timer novax-autoupdate.timer 2>/dev/null || true
sudo systemctl stop novax-watchdog.service novax-metrics.service novax-backup.service novax-autoupdate.service 2>/dev/null || true

echo "Removing unit files…"
sudo rm -f /etc/systemd/system/novax-{watchdog,metrics,backup,autoupdate}.service
sudo rm -f /etc/systemd/system/novax-{watchdog,metrics,backup,autoupdate}.timer
sudo systemctl daemon-reload

echo "Keeping repo & data by default."
if [[ "$PURGE" == "--purge" ]]; then
  echo "PURGE mode: fjerner ops-skript og backups (data/ beholdes IKKE)."
  rm -rf ${NOVA_HOME:-/home/nova/nova-bot}/ops ${NOVA_HOME:-/home/nova/nova-bot}/backups
  rm -rf ${NOVA_HOME:-/home/nova/nova-bot}/data
  echo "Done PURGE."
else
  echo "Hvis du vil slette alt inkl. data/: kjør:  ops/uninstall.sh --purge"
fi