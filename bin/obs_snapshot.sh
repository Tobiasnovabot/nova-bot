#!/usr/bin/env bash
set -euo pipefail
DST=~/nova-bot/ops/observability
mkdir -p "$DST"
sudo cp -a /etc/prometheus/prometheus.yml "$DST"/
sudo cp -a /etc/prometheus/rules.d "$DST"/
sudo cp -a /etc/alertmanager/alertmanager.yml "$DST"/
sudo chown -R "$(id -un)":"$(id -gn)" "$DST"
cd ~/nova-bot
git add ops/observability || true
git commit -m "obs snapshot $(date -u +%F:%T)" || true
echo "Snapshot committed."