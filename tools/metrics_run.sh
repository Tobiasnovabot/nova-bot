#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./tools/metrics_equity.sh || true
./.venv/bin/python ./tools/metrics_full.py || python ./tools/metrics_full.py || true