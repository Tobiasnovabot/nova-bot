#!/usr/bin/env bash
set -euo pipefail

echo "== NovaX METRICS HEALTHCHECK =="
echo
echo "== Services =="
systemctl --no-pager --quiet is-active novax.service && echo "PASS: novax.service aktiv" || echo "FAIL: novax.service"
systemctl --no-pager --quiet is-active novax-metrics.service && echo "PASS: novax-metrics aktiv" || echo "FAIL: novax-metrics"
systemctl --no-pager --quiet is-active prometheus && echo "PASS: prometheus aktiv" || echo "FAIL: prometheus"
systemctl --no-pager --quiet is-active grafana-server && echo "PASS: grafana aktiv" || echo "FAIL: grafana"

echo
echo "== Exporter =="
curl -s http://127.0.0.1:9108/metrics | grep -E '^novax_equity_usd' >/dev/null && \
  echo "PASS: /metrics leverer novax_*" || echo "FAIL: /metrics mangler novax_*"

echo
echo "== Prometheus =="
curl -s localhost:9090/-/ready | grep -q "Prometheus Server is Ready" && \
  echo "PASS: Prometheus ready" || echo "WARN: Prometheus ikke ready"
echo "- Targets:"
curl -s "http://localhost:9090/api/v1/targets" | grep -E '"health":"up"|novax' || true

echo
echo "== Grafana =="
curl -s http://localhost:3000/api/health | grep -q '"database":"ok"' && \
  echo "PASS: Grafana ok" || echo "WARN: Grafana API ikke ok (login kan kreves)"
echo "Dashboard fil: /var/lib/grafana/dashboards/novax-overview.json"