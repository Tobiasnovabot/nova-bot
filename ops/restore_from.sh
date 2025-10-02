#!/usr/bin/env bash
set -euo pipefail
source ${NOVA_HOME:-/home/nova/nova-bot}/ops/lib.sh
require tar
cd ${NOVA_HOME:-/home/nova/nova-bot}

ARCH="${1:-}"
[[ -f "$ARCH" ]] || { echo "Bruk: ops/restore_from.sh backups/novax-<timestamp>.tar.gz"; exit 1; }

log "Stopper tjeneste…"
sudo systemctl stop novax.service || true

log "Pakk ut ${ARCH}…"
tar -xzf "$ARCH" -C ${NOVA_HOME:-/home/nova/nova-bot}

log "Riktige eiere/rettigheter…"
chown -R nova:nova ${NOVA_HOME:-/home/nova/nova-bot}
chmod 600 ${NOVA_HOME:-/home/nova/nova-bot}/.env 2>/dev/null || true

log "systemd reload/start…"
sudo systemctl daemon-reload
sudo systemctl start novax.service

sleep 2
log "Status:"
systemctl --no-pager --full status novax.service | sed -n '1,15p'