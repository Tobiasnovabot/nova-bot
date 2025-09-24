#!/usr/bin/env bash
set -euo pipefail
ENV="${NOVA_HOME:-/home/nova/nova-bot}/.env"; [ -f "$ENV" ] && set -a && source "$ENV" && set +a
DATA="${NOVA_HOME:-${NOVA_HOME:-/home/nova/nova-bot}/data}/state.json"
CNT=$(python3 - <<'PY'
import json, os, pathlib
p=pathlib.Path(os.getenv("NOVA_HOME","${NOVA_HOME:-/home/nova/nova-bot}/data"))/"state.json"
s=json.loads(p.read_text() or "{}") if p.exists() else {}
print(len((s.get("universe_cache",{}).get("symbols") or [])))
PY
)
if [[ -n "${TG_KEY:-}" && -n "${TG_CHAT:-}" ]]; then
  curl -s -X POST "https://api.telegram.org/bot${TG_KEY}/sendMessage" \
    -d chat_id="${TG_CHAT}" -d parse_mode=Markdown \
    --data-urlencode text="✅ NovaX: Universe refresh OK — ${CNT} symbols" >/dev/null || true
fi