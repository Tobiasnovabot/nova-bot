#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="${ROOT:-$HOME/nova-bot}"
cd "$ROOT"

REQ=( "bot_main.py" "bot_main_dummy.py" "boost_learning.sh" "config/params.json" )
for f in "${REQ[@]}"; do
  [[ -f "$f" ]] && echo "OK: $f" || echo "WARN: mangler $f"
done

grep -RniE 'stair|ladder|boost.?learn|scale(out|in)|dca' nova config bin 2>/dev/null | head -n 50 || true

python3 p/stairs_sanity.py

# PASS hvis JSON har "ok": true
if grep -q '"ok": *true' p/stairs_sanity.out 2>/dev/null; then
  echo "PASS stairs_sanity"
  exit 0
else
  echo "FAIL stairs_sanity"
  exit 1
fi