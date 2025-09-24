#!/usr/bin/env bash
set -euo pipefail
echo "Prometheus readiness:" && curl -fsS http://127.0.0.1:9090/-/ready || true
echo "Alertmanager readiness:" && curl -fsS http://127.0.0.1:9093/-/ready || true
echo "Targets:" && curl -fsS http://127.0.0.1:9090/api/v1/targets | jq -r '.data.activeTargets[].labels.job' || true
echo "Rules:" && curl -fsS http://127.0.0.1:9090/api/v1/rules | jq -r '.data.groups[].name' || true
command -v promtool >/dev/null && promtool check config /etc/prometheus/prometheus.yml || true
command -v promtool >/dev/null && promtool check rules /etc/prometheus/rules.d/*.yml || true