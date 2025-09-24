#!/usr/bin/env bash
set -euo pipefail
log(){ printf "[%s] %s\n" "$(date '+%F %T')" "$*"; }
require(){ command -v "$1" >/dev/null 2>&1 || { echo "Mangler: $1"; exit 2; }; }