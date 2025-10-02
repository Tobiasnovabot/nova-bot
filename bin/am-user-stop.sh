#!/usr/bin/env bash
set -euo pipefail
pkill -f 'alertmanager .*--web.listen-address=127\.0\.0\.1:9097' 2>/dev/null || true