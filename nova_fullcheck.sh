#!/usr/bin/env bash
set -euo pipefail

HDR="== NovaX FULLCHECK =="
echo "$HDR"
echo "Host: $(hostname)  User: $(whoami)  Uptime: $(uptime -p)"

echo -e "\n== systemd =="
for u in novax.service novax-watchdog.timer novax-metrics.timer novax-backup.timer novax-autoupdate.timer; do
  if systemctl is-enabled --quiet "$u" 2>/dev/null; then
    echo "ENABLED: $u"
  else
    echo "DISABLED: $u"
  fi
  systemctl is-active --quiet "$u" && echo "  ACTIVE: $u" || echo "  INACTIVE: $u"
done

echo -e "\n== .env (utdrag) =="
grep -E '^(EXCHANGE|MODE|NOVA_HOME|TG_|WATCHLIST|TOP_N|WATCH_TOP_N|RCLONE_DEST)=' ${NOVA_HOME:-/home/nova/nova-bot}/.env || true

echo -e "\n== venv/pakker =="
source ${NOVA_HOME:-/home/nova/nova-bot}/.venv/bin/activate
python - <<'PY'
mods=[("ccxt","__version__"),("requests","__version__")]
for m,attr in mods:
    try:
        mod=__import__(m)
        v=getattr(mod,attr,"?")
        print(f"PASS: import {m} ({v})")
    except Exception as e:
        print(f"FAIL: import {m}: {e}")
PY

echo -e "\n== Telegram =="
bash -lc 'set -a; source ${NOVA_HOME:-/home/nova/nova-bot}/.env; set +a; \
  if [[ -n "${TG_KEY:-}" ]]; then \
    curl -s "https://api.telegram.org/bot${TG_KEY}/getMe" | grep -q "\"ok\":true" && echo "PASS: TG getMe OK" || echo "WARN: TG getMe feilet"; \
  else echo "WARN: TG_KEY mangler i .env"; fi'

echo -e "\n== Exchange =="
python - <<'PY'
import ccxt
try:
  ex=ccxt.binance()
  t=ex.fetch_ticker('BTC/USDT')
  b,a=t.get('bid'),t.get('ask')
  print(f"PASS: binance fetch_ticker BTC/USDT bid={b} ask={a}")
except Exception as e:
  print("FAIL: binance fetch_ticker:", e)
PY

echo -e "\n== Data/skrivetilgang =="
DATA="${NOVA_HOME:-/home/nova/nova-bot}/data"
echo "DATA_DIR=$DATA"
mkdir -p "$DATA"
python - <<'PY'
import json,pathlib
d=pathlib.Path('${NOVA_HOME:-/home/nova/nova-bot}/data')
(d/'equity.json').write_text('[]',encoding='utf-8')
(d/'state.json').write_text('{"ok":true}',encoding='utf-8')
print("PASS: kan skrive equity.json/state.json")
PY
stat -c "equity.json: %y %sB" "$DATA/equity.json"
stat -c "state.json : %y %sB" "$DATA/state.json"

echo -e "\n== metrics.prom =="
if [[ -f "$DATA/metrics.prom" ]]; then
  head -n 10 "$DATA/metrics.prom"
  echo "PASS: metrics.prom finnes"
else
  echo "WARN: metrics.prom mangler (vent 1 minutt på timeren)"
fi

echo -e "\n== watchdog siste kjøringer =="
journalctl -u novax-watchdog.service --since "-10 min" -n 20 --no-pager || true

echo -e "\n== backup siste kjøring =="
journalctl -u novax-backup.service --since "yesterday" -n 5 --no-pager || true
ls -1t ${NOVA_HOME:-/home/nova/nova-bot}/backups | head -n 3 || true

echo -e "\n== auto-update siste kjøring =="
journalctl -u novax-autoupdate.service --since "yesterday" -n 5 --no-pager || true

echo -e "\n== novax journal (kort) =="
journalctl -u novax.service -n 50 --no-pager | tail -n +1

echo -e "\n== UFW/Fail2ban =="
sudo ufw status verbose || true
sudo systemctl status fail2ban --no-pager | sed -n '1,12p' || true

echo -e "\n== Oppsummering =="
echo "Se etter: timere ACTIVE, TG OK, Binance OK, metrics.prom, backup-fil(e) og novax.service i gang."