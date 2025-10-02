#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
mkdir -p logs
python3 -m nova.engine.run >> logs/engine.out 2>&1 &
echo $! > nova-engine.pid
echo "started pid $(cat nova-engine.pid)"
