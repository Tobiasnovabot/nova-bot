#!/usr/bin/env bash
set -euo pipefail
source ${NOVA_HOME:-/home/nova/nova-bot}/ops/lib.sh
load_env || true
ROOT="${NOVA_HOME:-/home/nova/nova-bot}"
TS=$(date +%Y%m%d-%H%M%S)
DEST_LOCAL="$ROOT/backups/nova-data-${TS}.tar.gz"

# 1) Lokal tarball (roter 7)
tar -C "$ROOT" -czf "$DEST_LOCAL" data
find "$ROOT/backups" -type f -name 'nova-data-*.tar.gz' -printf '%T@ %p\n' | sort -n | awk 'NR<=length-7 {print $2}' | xargs -r rm -f

# 2) Valgfritt: rclone til fjernlager (sett RCLONE_DEST i .env, f.eks. "b2:nova-bot/data")
if [[ -n "${RCLONE_DEST:-}" ]]; then
  if command -v rclone >/dev/null 2>&1; then
    rclone sync "$ROOT/data" "$RCLONE_DEST" ${RCLONE_FLAGS:-} --fast-list --transfers 8 --checkers 8
    tg "✅ *NovaX:* Backup fullført til \`$RCLONE_DEST\`."
  else
    tg "ℹ️ *NovaX:* rclone ikke installert – hopper over remote backup."
  fi
fi