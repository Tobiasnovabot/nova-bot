#!/usr/bin/env bash
set -euo pipefail
echo "== Universe builder =="
systemctl cat novax-universe-builder.service | sed -n '1,200p' | grep -E 'ExecStartPost|Environment=MIN_QV|MAX_SPREAD|TRADING_EXCHANGE' || true
echo
echo "== Risk Guard =="
systemctl status novax-risk-guard.service --no-pager | sed -n '1,12p'
tail -n 5 data/risk_dd_guard.log 2>/dev/null || true
echo
echo "== Heartbeat Guard =="
systemctl status novax-heartbeat-guard.timer --no-pager | sed -n '1,10p'
tail -n 5 data/heartbeat_guard.log 2>/dev/null || true
echo
echo "== Babysitter =="
systemctl status novax-babysitter.timer --no-pager | sed -n '1,10p'
tail -n 5 data/babysitter.log 2>/dev/null || true