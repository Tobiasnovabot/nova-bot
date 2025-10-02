#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -U -r requirements.txt
mkdir -p runtime logs metrics
systemctl --user daemon-reload
systemctl --user enable --now nova-engine-ultra.service
systemctl --user status nova-engine-ultra.service --no-pager || true
