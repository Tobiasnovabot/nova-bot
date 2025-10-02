#!/usr/bin/env bash
set -euo pipefail
BASE="${NOVA_HOME:-/home/nova/nova-bot}"; DATA="$BASE/data"; BACK="$BASE/backups"
ENVF="$BASE/.env"; [ -f "$ENVF" ] && set -a && source "$ENVF" && set +a
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
mkdir -p "$BACK"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${BACK}/nova-data-${STAMP}.tar.gz"

# Samle filer som finnes
to_add=()
for f in state.json equity.json trades.json; do [ -f "$DATA/$f" ] && to_add+=("$f"); done
[ -d "$DATA/logs" ] && to_add+=("logs")
tar -C "$DATA" -czf "$OUT" "${to_add[@]}" 2>/dev/null || true
echo "SNAPSHOT: $OUT"

find "$BACK" -type f -name 'nova-data-*.tar.gz' -mtime +$KEEP_DAYS -print -delete | sed 's/^/PRUNE: /' || true
tar -tzf "$OUT" >/dev/null && echo "VERIFY: OK" || { echo "VERIFY: FAIL"; exit 1; }