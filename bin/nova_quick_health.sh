#!/usr/bin/env bash
set -euo pipefail
ok(){ echo "OK   $*"; }
wr(){ echo "WARN $*"; }
er(){ echo "FAIL $*"; }

# Tjenester
systemctl is-active --quiet novax.service && ok "novax.service active" || er "novax.service inactive"

# Heartbeats (15 min)

# Telegram-kontroller: tell KUN python-barn under systemd-unit
MAINPID="$(systemctl show -p MainPID --value novax-tg.service 2>/dev/null || echo 0)"
TG_CNT="$(ps -o pid=,ppid=,cmd= --ppid "$MAINPID" 2>/dev/null | grep -E "python .* -m nova\.telegram_ctl\.run" | wc -l | tr -d "[:space:]" || echo 0)"
[ ${TG_CNT:-0} -le 1 ] && ok "telegram controller instances <=1 (${TG_CNT:-0})" || wr "multiple TG controllers (${TG_CNT:-0})"

HB_CNT="$(journalctl -u novax.service -b --since '-15 min' --no-pager -o cat \
          | grep -F 'heartbeat #' | wc -l | tr -d '[:space:]' || echo 0)"
[ "${HB_CNT:-0}" -gt 0 ] && ok "heartbeats last 15m ($HB_CNT)" || wr "no heartbeats last 15m"

# Exporter
curl -fsS http://127.0.0.1:9108/metrics | grep -q '^novax_' && ok "exporter metrics present" || wr "exporter missing novax_*"

# Selfcheck
OUT="$(. ./.venv/bin/activate; python -m nova.selfcheck.runner 2>&1 || true)"
echo "$OUT" | tail -n +1 | sed -n 's/^/SELFCHK: /p' >/dev/stderr
echo "$OUT" | grep -q 'FAIL=[1-9]' && er "module selfchecks FAIL>0" || ok "module selfchecks: no FAIL"

# Loggkataloger skrivbare
mkdir -p data/logs nova/logs
touch data/logs/_w nova/logs/_w 2>/dev/null && ok "log dirs writable" || er "log dirs NOT writable"

# Uønskede timere (skal vanligvis være av)
for T in novax-engine-watchdog.timer novax-tg-watchdog.timer; do
  if systemctl is-enabled --quiet "$T" 2>/dev/null; then wr "$T enabled"; else ok "$T disabled"; fi
done