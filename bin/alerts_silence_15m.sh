#!/usr/bin/env bash
set -euo pipefail
: "${AM_URL:=http://127.0.0.1:9093}"
: "${MATCHERS:=alertname=~\".*\"}"
: "${DUR:=15m}"
amtool --alertmanager.url "$AM_URL" silence add --duration "$DUR" "$MATCHERS"
echo "Silence opprettet for $DUR på matcher: $MATCHERS"