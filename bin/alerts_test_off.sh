#!/usr/bin/env bash
set -euo pipefail
sudo rm -f /etc/prometheus/rules.d/novax_test.rules.yml
sudo systemctl restart prometheus
echo "Test-alarm fjernet."