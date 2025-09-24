#!/usr/bin/env bash
set -euo pipefail
PROM=http://127.0.0.1:19090
curl -fsS "$PROM/-/ready" >/dev/null && echo "READY 19090" || echo "NOT READY"
echo "Targets:"; curl -fsS "$PROM/api/v1/targets?state=active" | jq -r '.data.activeTargets[].labels.job' | sort -u
echo "up:"; curl -fsS "$PROM/api/v1/query" --get --data-urlencode 'query=up' \
  | jq -r '.data.result[]| [.metric.job,.metric.instance,.value[1]]|@tsv'
tail -n 30 /tmp/prom-user.out 2>/dev/null || true