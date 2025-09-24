#!/usr/bin/env bash
set -euo pipefail
red(){ printf "\033[31m%s\033[0m\n" "$*";}; grn(){ printf "\033[32m%s\033[0m\n" "$*";}; ylw(){ printf "\033[33m%s\033[0m\n" "$*";}

echo "== SJEKK KATALOGER =="
for d in data config nova nova/engine nova/exporters; do [[ -d "$d" ]] && grn "[OK] $d" || { red "[MISS] $d"; exit 1; }; done

echo "== SJEKK NØKKELFILER =="
for f in config/params.json nova/engine/run.py nova/engine/bandit.py nova/exporters/nova_state_exporter.py; do [[ -f "$f" ]] && grn "[OK] $f" || { red "[MISS] $f"; exit 1; }; done

echo "== SERVICE STATUS =="
systemctl is-active --quiet nova-engine && grn "[OK] nova-engine aktiv" || red "[FAIL] nova-engine"
systemctl is-active --quiet novax-state-exporter && grn "[OK] novax-state-exporter aktiv" || ylw "[WARN] exporter ikke aktiv?"

echo "== PROMETHEUS/EXPORTER METRICS =="
curl -fsS 127.0.0.1:9108/metrics | grep -E '^novax_' | head -n 20 || ylw "ingen metrics?"

echo "== STEMMER & MINNE =="
jq -r '.ts, .votes' data/strat_votes.json 2>/dev/null || ylw "mangler data/strat_votes.json"
jq -r '.' data/strategy_memory.json 2>/dev/null || ylw "mangler data/strategy_memory.json"

echo "== TVANG: ÅPNE KJØP (FORCE_BUY_ONE) =="
rm -f FORCE_BUY_ONE; touch FORCE_BUY_ONE
sleep 6
sudo journalctl -u nova-engine -n 60 --no-pager | tail -n 40

echo "== POS/METRICS ETTER TVANG =="
curl -fsS 127.0.0.1:9108/metrics | grep -E '^novax_positions_open|^novax_exposure_frac|^novax_equity_usdt' || true

ts=$(date -u +%Y%m%dT%H%M%SZ)
cp -f data/strat_votes.json "data/strat_votes.${ts}.json" 2>/dev/null || true
cp -f data/strategy_memory.json "data/strategy_memory.${ts}.json" 2>/dev/null || true
grn "Snapshots skrevet med suffix ${ts}"
echo "== KLART =="
