#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}
LATEST="$(ls -1t backups/novax-*.tar.gz 2>/dev/null | head -1 || true)"
[[ -n "$LATEST" ]] || { echo "Ingen backup funnet i backups/"; exit 1; }
exec ${NOVA_HOME:-/home/nova/nova-bot}/ops/restore_from.sh "$LATEST"