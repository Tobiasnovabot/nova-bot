#!/usr/bin/env bash
set -euo pipefail
echo "Prometheus:"
curl -fsS http://127.0.0.1:9090/api/v1/alerts | jq -r '.data.alerts[].labels.alertname // empty'
echo "Alertmanager:"
curl -fsS http://127.0.0.1:9093/api/v2/alerts | jq -r '.[].labels.alertname // empty'