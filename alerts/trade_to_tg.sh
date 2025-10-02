#!/usr/bin/env bash
set -Eeuo pipefail
source ${NOVA_HOME:-/home/nova/nova-bot}/.env
: "${TOKEN:?}"; : "${CHAT_ID:?}"

LAST=/tmp/novax_last_pos
LASTID=/tmp/novax_last_jid
touch "$LAST" "$LASTID"

while true; do
  # hent siste 100 linjer, stabilt
  JOUT="$(journalctl -n100 -u novax.service -o cat --since '1 min ago' || true)"
  POS="$(awk -F'pos=' '/tick OK/ {print $2}' <<<"$JOUT" | awk '{print $1}' | tr -d ',' | tail -n1 || true)"
  JID="$(journalctl --cursor-file="$LASTID" -u novax.service -o cat -n0 -q; echo $RANDOM)" # dummy touch

  if [[ -n "${POS:-}" ]]; then
    PREV="$(cat "$LAST" 2>/dev/null || true)"
    if [[ "$POS" != "${PREV:-}" ]]; then
      echo "$POS" >"$LAST"
      curl -s "https://api.telegram.org/bot$TOKEN/sendMessage" \
        -d chat_id="$CHAT_ID" -d text="🔔 Position count changed: ${PREV:-∅} → ${POS}" >/dev/null || true
    fi
  fi
  sleep 5
done