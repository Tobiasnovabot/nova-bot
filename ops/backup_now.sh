#!/usr/bin/env bash
set -euo pipefail
source ${NOVA_HOME:-/home/nova/nova-bot}/ops/lib.sh
require tar
cd ${NOVA_HOME:-/home/nova/nova-bot}

TS="$(date '+%Y%m%d-%H%M%S')"
OUT="backups/novax-${TS}.tar.gz"

log "Lager backup: ${OUT}"
tar -czf "${OUT}" \
  --exclude='data/logs/*' \
  --exclude='.venv/*' \
  .env data config nova/engine/run.py /etc/systemd/system/novax.service 2>/dev/null || true

# roter: behold 14 siste
ls -1t backups/novax-*.tar.gz 2>/dev/null | tail -n +15 | xargs -r rm -f
log "OK: $(ls -lh ${OUT})"