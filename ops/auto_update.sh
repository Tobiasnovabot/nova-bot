#!/usr/bin/env bash
set -euo pipefail
source ${NOVA_HOME:-/home/nova/nova-bot}/ops/lib.sh
cd ${NOVA_HOME:-/home/nova/nova-bot}

if [[ -n "$(git status --porcelain)" ]]; then
  tg "ℹ️ *NovaX:* Lokale endringer funnet – auto-update hopper over (clean repo anbefales)."
  exit 0
fi

CURR=$(git rev-parse HEAD)
echo "$CURR" > .last_head
set +e
git fetch --all --quiet
git pull --rebase --autostash --quiet
RC=$?
set -e
if [[ $RC -ne 0 ]]; then
  git reset --hard "$CURR"
  tg "❌ *NovaX:* Oppdatering feilet – rollback utført."
  exit 1
fi

sudo systemctl restart novax.service
tg "✅ *NovaX:* Oppdatert til $(git rev-parse --short HEAD) og restartet."