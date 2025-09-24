#!/usr/bin/env bash
set -euo pipefail
sudo tee /etc/prometheus/rules.d/novax_test.rules.yml >/dev/null <<'RULES'
groups:
- name: novax_test
  rules:
  - alert: NovaX_Test_Fires
    expr: vector(1)
    for: 0m
    labels: { severity: warning }
    annotations: { summary: "Testalarm fra NovaX/Prometheus" }
RULES
sudo systemctl restart prometheus
echo "Test-alarm aktivert."