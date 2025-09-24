#!/usr/bin/env bash
set -euo pipefail
curl -fsS http://127.0.0.1:9097/-/healthy && echo "AM READY" || echo "AM NOT READY"
curl -fsS http://127.0.0.1:9097/api/v2/status | jq -r '.versionInfo.version'