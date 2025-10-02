#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}
echo "== Risk Healthcheck =="
echo "NOVA_HOME=${NOVA_HOME:-$(grep -E '^NOVA_HOME=' .env 2>/dev/null | cut -d= -f2)}"
test -f data/config/risk.json && echo "PASS: risk.json finnes" || { echo "FAIL: mangler data/config/risk.json"; exit 1; }
python3 - <<'PY'
from nova.risk.risk_rules import compute_position_size
print("PASS: import risk_rules OK")
out = compute_position_size(price=100.0, stop_frac=0.01, override_equity=10000)
print("PASS: compute_position_size OK ->", {k:out[k] for k in ("qty","dd_multiplier","daily_guard_triggered")})
PY
echo "PASS: risk_status.json:"; test -f data/config/risk_status.json && tail -n1 data/config/risk_status.json || echo "(skrives første gang du kjører selfcheck)"