#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}
source .venv/bin/activate
python -m nova.monitor.exposure_guard