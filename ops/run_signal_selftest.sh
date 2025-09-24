#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}
source ./.env 2>/dev/null || true
source ./ops/lib.sh 2>/dev/null || true
${NOVA_HOME:-/home/nova/nova-bot}/.venv/bin/python ops/signal_selftest.py