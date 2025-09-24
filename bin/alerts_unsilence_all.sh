#!/usr/bin/env bash
set -euo pipefail
: "${AM_URL:=http://127.0.0.1:9093}"
amtool --alertmanager.url "$AM_URL" silence expire $(amtool --alertmanager.url "$AM_URL" silence query -q || true) 2>/dev/null || true
echo "Alle silences forsøkt utløpt."