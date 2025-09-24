#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
TAR="${1:-$(ls -1t backups/*.tar.gz 2>/dev/null | head -n1)}"
[ -n "${TAR:-}" ] || { echo "Ingen backup funnet i backups/"; exit 1; }
echo "Restoring from $TAR"
tar -xzf "$TAR"
echo "Done."