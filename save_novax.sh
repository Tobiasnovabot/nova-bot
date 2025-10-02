#!/bin/bash
NAME="novax_bundle_$(hostname)_$(date +%F_%H%M%S)"
BASE="/tmp/$NAME"
OUT="/tmp/$NAME.tgz"

mkdir -p "$BASE"/{etc,home,logs,systemd,proof}

# 1) Kopier alle relevante konfig-mapper
sudo rsync -a --relative /etc/prometheus "$BASE/etc/" 2>/dev/null || true
sudo rsync -a --relative /etc/grafana "$BASE/etc/" 2>/dev/null || true
sudo rsync -a --relative /etc/nginx "$BASE/etc/" 2>/dev/null || true

# 2) Kopier hele prosjektet (alt i nova-bot, inkl. undermapper)
if [ -d "$HOME/nova-bot" ]; then
  rsync -a "$HOME/nova-bot" "$BASE/home/"
fi

# 3) Kopier user systemd
if [ -d "$HOME/.config/systemd/user" ]; then
  rsync -a "$HOME/.config/systemd/user" "$BASE/systemd/"
fi

# 4) Bevis/diagnostikk
{
  echo "=== VERSJONER ==="
  (prometheus --version || true)
  (grafana-server -v || true)
  (nginx -v 2>&1 || true)

  echo -e "\n=== LYTTERE ==="
  ss -ltnp | egrep ':(9090|3000|9112|9093)\b' || true

  echo -e "\n=== PROMETHEUS SJEKK ==="
  curl -s 'http://127.0.0.1:9090/api/v1/query?query=novax_up' || true
  curl -s 'http://127.0.0.1:9090/api/v1/targets' | jq '.data.activeTargets[].labels.job' || true

  echo -e "\n=== GRAFANA HEALTH ==="
  curl -s 'http://127.0.0.1:3000/api/health' || true

  echo -e "\n=== NGINX TEST ==="
  curl -sI 'http://127.0.0.1/' | head -n1 || true
} > "$BASE/proof/quick_checks.txt"

# 5) Lag arkiv
sudo tar -C /tmp -czf "$OUT" "$(basename "$BASE")"
echo "ARKIV: $OUT"
