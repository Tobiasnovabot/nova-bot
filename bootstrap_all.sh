#!/usr/bin/env bash
set -euo pipefail

ROOT=${NOVA_HOME:-/home/nova/nova-bot}
cd "$ROOT"

mkdir -p bin scripts tools data backups logs

# ──────────────────────────────────────────────────────────────────────────────
# ENV: standard nøkler + defaults
# ──────────────────────────────────────────────────────────────────────────────
grep -q '^NOVA_HOME=' .env || echo 'NOVA_HOME=${NOVA_HOME:-/home/nova/nova-bot}/data' >> .env
grep -q '^MODE=' .env      || echo 'MODE=paper' >> .env
grep -q '^EXCHANGE=' .env  || echo 'EXCHANGE=binance' >> .env
grep -q '^ENGINE_LOOP_SEC=' .env || echo 'ENGINE_LOOP_SEC=10' >> .env
grep -q '^WATCHLIST=' .env || echo 'WATCHLIST=AUTO_USDT' >> .env
grep -q '^TOP_N=' .env     || echo 'TOP_N=300' >> .env
grep -q '^WATCH_TOP_N=' .env || echo 'WATCH_TOP_N=300' >> .env
grep -q '^LOG_LEVEL=' .env || echo 'LOG_LEVEL=DEBUG' >> .env

# Risikogrense defaults (kan justeres i .env)
add_if_missing () { grep -q "^$1=" .env || echo "$1=$2" >> .env; }
add_if_missing MAX_DRAWDOWN_DAY_USD 150.0
add_if_missing MAX_TRADE_RISK_USD   50.0
add_if_missing MAX_POSITIONS        3
add_if_missing MIN_CASH_BUFFER_USD  100.0
add_if_missing DRY_RUN_SECS         300
add_if_missing FAILSAFE_ARM_WINDOW_SECS 120
add_if_missing ALERT_EQUITY_DROP_PCT 5

# ──────────────────────────────────────────────────────────────────────────────
# Del 1: Fail-safe / to-mannsregel (TG-kommando via filsignal)
# ──────────────────────────────────────────────────────────────────────────────
cat > bin/failsafe_guard.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}
source .env
STATE=data/state.json
SIGDIR=data/signals
mkdir -p "$SIGDIR"

# signal-filer:
#   signals/arm_live.request    -> forespørsel om live
#   signals/arm_live.confirm    -> bekreftelse (andre person)
#   signals/arm_live.commit     -> (skrives av dette scriptet etter dry-run)
#   signals/kill_switch         -> global av-knapp (paper tvinges)
touch "$STATE"
now(){ date +%s; }

if [[ -f "$SIGDIR/kill_switch" ]]; then
  jq '."mode"="paper" | ."bot_enabled"=false' "$STATE" 2>/dev/null | tee "$STATE" >/dev/null
  echo "[failsafe] kill_switch aktivert -> MODE=paper, bot_enabled=false"
  exit 0
fi

if [[ -f "$SIGDIR/arm_live.request" ]]; then
  req_ts=$(stat -c %Y "$SIGDIR/arm_live.request" || echo 0)
  age=$(( $(now) - req_ts ))
  if [[ $age -gt ${FAILSAFE_ARM_WINDOW_SECS:-120} ]]; then
    echo "[failsafe] request er for gammel ($age s) -> avviser"
    rm -f "$SIGDIR/arm_live.request"
    exit 0
  fi
  if [[ -f "$SIGDIR/arm_live.confirm" ]]; then
    # dry-run periode før live
    echo "[failsafe] bekreftet -> dry-run i ${DRY_RUN_SECS:-300}s"
    sleep "${DRY_RUN_SECS:-300}"
    jq '."mode"="live" | ."bot_enabled"=true' "$STATE" 2>/dev/null | tee "$STATE" >/dev/null
    echo "[failsafe] LIVE aktivert"
    rm -f "$SIGDIR/arm_live.request" "$SIGDIR/arm_live.confirm"
    date > "$SIGDIR/arm_live.commit"
  else
    echo "[failsafe] venter på bekreftelse (arm_live.confirm)"
  fi
fi
BASH
chmod +x bin/failsafe_guard.sh

cat > /etc/systemd/system/novax-failsafe.service <<'UNIT'
[Unit]
Description=NovaX Fail-safe arm/kill watcher
After=novax.service
Wants=novax.service

[Service]
Type=oneshot
User=nova
WorkingDirectory=${NOVA_HOME:-/home/nova/nova-bot}
EnvironmentFile=${NOVA_HOME:-/home/nova/nova-bot}/.env
ExecStart=${NOVA_HOME:-/home/nova/nova-bot}/bin/failsafe_guard.sh
UNIT

cat > /etc/systemd/system/novax-failsafe.timer <<'UNIT'
[Unit]
Description=Run failsafe guard every 15s

[Timer]
OnBootSec=20
OnUnitActiveSec=15

[Install]
WantedBy=timers.target
UNIT

# ──────────────────────────────────────────────────────────────────────────────
# Del 2: Hard risikobeskyttelse
# ──────────────────────────────────────────────────────────────────────────────
cat > bin/risk_guard.py <<'PY'
#!/usr/bin/env python3
import os, json, pathlib, time, sys

ENV = {k:v for k,v in os.environ.items()}
DATA = pathlib.Path(ENV.get("NOVA_HOME","${NOVA_HOME:-/home/nova/nova-bot}/data"))
STATE = DATA/"state.json"
EQUITY = DATA/"equity.json"
TRADES = DATA/"trades.json"

MAX_DRAWDOWN_DAY_USD = float(ENV.get("MAX_DRAWDOWN_DAY_USD","150"))
MAX_TRADE_RISK_USD   = float(ENV.get("MAX_TRADE_RISK_USD","50"))
MAX_POSITIONS        = int(ENV.get("MAX_POSITIONS","3"))
MIN_CASH_BUFFER_USD  = float(ENV.get("MIN_CASH_BUFFER_USD","100"))

def _load_json(p, default):
    try:
        return json.loads(p.read_text())
    except Exception as e:
return default

def tg(msg:str):
    key = ENV.get("TG_KEY",""); chat = ENV.get("TG_CHAT","")
    if not key or not chat: return
    import urllib.request, urllib.parse
    data = urllib.parse.urlencode({"chat_id":chat,"text":msg}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{key}/sendMessage", data=data, timeout=5)
    except Exception:
        pass

def fail(reason:str):
    s = _load_json(STATE, {})
    s["mode"]="paper"
    s["bot_enabled"]=False
    STATE.write_text(json.dumps(s, separators=(",",":")))
    tg(f"⚠️ NovaX KILL-SWITCH: {reason} → MODE=paper, bot_disabled")
    print("[risk_guard]", reason)
    # valgfritt: stopp engine
    os.system("sudo systemctl stop novax.service >/dev/null 2>&1")

def check_limits():
    eq = _load_json(EQUITY, [])
    if eq:
        today = eq[-1]
        dd = float(today.get("drawdown_day_usd", 0.0))
        cash = float(today.get("cash_usd", today.get("equity_usd",0.0)))
        if dd <= -abs(MAX_DRAWDOWN_DAY_USD):
            fail(f"Daglig max-tap nådd ({dd} USD <= -{MAX_DRAWDOWN_DAY_USD})")
            return
        if cash < MIN_CASH_BUFFER_USD:
            fail(f"Kontantbuffer < {MIN_CASH_BUFFER_USD} USD (cash={cash})")
            return
    tr = _load_json(TRADES, [])
    # per-trade tap (åpne eller nylig lukkede med stor negativ PnL)
    for t in tr[-50:]:
        pnl = float(t.get("pnl", 0.0))
        if pnl <= -abs(MAX_TRADE_RISK_USD):
            fail(f"Per-trade tap over grense (pnl={pnl} <= -{MAX_TRADE_RISK_USD})")
            return
    # max posisjoner
    s = _load_json(STATE, {})
    pos = s.get("positions", {})
    if len(pos) > MAX_POSITIONS:
        fail(f"For mange posisjoner ({len(pos)} > {MAX_POSITIONS})")
        return
    print("[risk_guard] OK")

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        print("SELFTEST risk_guard: kjører sjekk én gang …")
        check_limits()
        sys.exit(0)
    check_limits()
PY
chmod +x bin/risk_guard.py

cat > /etc/systemd/system/novax-riskguard.service <<'UNIT'
[Unit]
Description=NovaX Risk Guard
After=novax.service
Wants=novax.service

[Service]
Type=oneshot
User=nova
WorkingDirectory=${NOVA_HOME:-/home/nova/nova-bot}
EnvironmentFile=${NOVA_HOME:-/home/nova/nova-bot}/.env
ExecStart=${NOVA_HOME:-/home/nova/nova-bot}/bin/risk_guard.py
UNIT

cat > /etc/systemd/system/novax-riskguard.timer <<'UNIT'
[Unit]
Description=Run risk guard every 30s

[Timer]
OnBootSec=25
OnUnitActiveSec=30

[Install]
WantedBy=timers.target
UNIT

# ──────────────────────────────────────────────────────────────────────────────
# Del 3: Migrer JSON → SQLite (+ health-sjekk)
# ──────────────────────────────────────────────────────────────────────────────
cat > tools/migrate_to_sqlite.py <<'PY'
#!/usr/bin/env python3
import json, sqlite3, pathlib, time, os

DATA = pathlib.Path(os.getenv("NOVA_HOME","${NOVA_HOME:-/home/nova/nova-bot}/data"))
DB = DATA/"trades.sqlite"
TRADES = DATA/"trades.json"
EQUITY = DATA/"equity.json"

con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL, sym TEXT, side TEXT, qty REAL, price REAL, pnl REAL, status TEXT, raw TEXT
)""")
cur.execute("""CREATE TABLE IF NOT EXISTS equity (
  ts REAL, equity_usd REAL, drawdown_day_usd REAL, cash_usd REAL
)""")

def safe_load(p):
  try: return json.loads(pathlib.Path(p).read_text() or "[]")
  except Exception as e:
return []

tr = safe_load(TRADES)
for t in tr:
  cur.execute("INSERT INTO trades (ts,sym,side,qty,price,pnl,status,raw) VALUES (?,?,?,?,?,?,?,?)",
    (t.get("ts"), t.get("sym"), t.get("side"), t.get("qty"), t.get("price"), t.get("pnl"), t.get("status"), json.dumps(t)))
eq = safe_load(EQUITY)
for e in eq:
  cur.execute("INSERT INTO equity (ts,equity_usd,drawdown_day_usd,cash_usd) VALUES (?,?,?,?)",
    (e.get("ts"), e.get("equity_usd"), e.get("drawdown_day_usd"), e.get("cash_usd", e.get("equity_usd"))))
con.commit()

c_tr = cur.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
c_eq = cur.execute("SELECT COUNT(*) FROM equity").fetchone()[0]
print(f"[migrate] trades={c_tr} equity={c_eq} -> {DB}")
PY
chmod +x tools/migrate_to_sqlite.py

# ──────────────────────────────────────────────────────────────────────────────
# Del 4: logrotate (journal er egen; vi roterer app-logs og data/metrics)
# ──────────────────────────────────────────────────────────────────────────────
cat > /etc/logrotate.d/novax <<'ROT'
${NOVA_HOME:-/home/nova/nova-bot}/logs/*.log {
  daily
  rotate 14
  compress
  missingok
  copytruncate
}
ROT

# ──────────────────────────────────────────────────────────────────────────────
# Del 5: Backup (+ timer) og enkel restore-mal
# ──────────────────────────────────────────────────────────────────────────────
cat > bin/backup_now.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}
ts=$(date +%Y%m%d-%H%M%S)
tar czf backups/novax-backup-$ts.tgz data .env /etc/systemd/system/novax*.service /etc/systemd/system/novax*.timer || true
echo "[backup] backups/novax-backup-$ts.tgz"
BASH
chmod +x bin/backup_now.sh

cat > /etc/systemd/system/novax-backup.service <<'UNIT'
[Unit]
Description=NovaX backup

[Service]
Type=oneshot
User=nova
WorkingDirectory=${NOVA_HOME:-/home/nova/nova-bot}
ExecStart=${NOVA_HOME:-/home/nova/nova-bot}/bin/backup_now.sh
UNIT

cat > /etc/systemd/system/novax-backup.timer <<'UNIT'
[Unit]
Description=NovaX daily backup 02:15

[Timer]
OnCalendar=*-*-* 02:15:00
Persistent=true

[Install]
WantedBy=timers.target
UNIT

# ──────────────────────────────────────────────────────────────────────────────
# Del 6: Watchdog / auto-heal (inkl. TG 409 fix)
# ──────────────────────────────────────────────────────────────────────────────
cat > bin/watchdog.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}
source .env || true

# 1) Sjekk service status
if ! systemctl is-active --quiet novax.service; then
  systemctl restart novax.service
  [[ -n "${TG_KEY:-}" && -n "${TG_CHAT:-}" ]] && \
    curl -s "https://api.telegram.org/bot${TG_KEY}/sendMessage" -d chat_id="${TG_CHAT}" -d text="🩺 NovaX: Engine var nede → restart" >/dev/null
fi

# 2) Sjekk TG 409 i siste logglinjer
if journalctl -u novax.service -n 50 --no-pager | grep -q ' 409 Client Error: Conflict .*getUpdates'; then
  echo "[watchdog] TG 409 oppdaget → deleteWebhook + restart"
  if [[ -n "${TG_KEY:-}" ]]; then
    curl -s "https://api.telegram.org/bot${TG_KEY}/deleteWebhook?drop_pending_updates=true" >/dev/null
  fi
  systemctl restart novax.service
fi

# 3) Sjekk at equity/state oppdateres (ikke eldre enn 15 min)
ok=1
for f in data/equity.json data/state.json; do
  if [[ -f "$f" ]]; then
    age=$(( $(date +%s) - $(stat -c %Y "$f") ))
    if [[ $age -gt 900 ]]; then ok=0; fi
  fi
done
if [[ $ok -eq 0 ]]; then
  systemctl restart novax.service
  [[ -n "${TG_KEY:-}" && -n "${TG_CHAT:-}" ]] && \
    curl -s "https://api.telegram.org/bot${TG_KEY}/sendMessage" -d chat_id="${TG_CHAT}" -d text="🩺 NovaX: Filer stagnerte → restart" >/dev/null
fi
BASH
chmod +x bin/watchdog.sh

cat > /etc/systemd/system/novax-watchdog.service <<'UNIT'
[Unit]
Description=NovaX watchdog
After=novax.service

[Service]
Type=oneshot
User=nova
WorkingDirectory=${NOVA_HOME:-/home/nova/nova-bot}
ExecStart=${NOVA_HOME:-/home/nova/nova-bot}/bin/watchdog.sh
UNIT

cat > /etc/systemd/system/novax-watchdog.timer <<'UNIT'
[Unit]
Description=Run NovaX watchdog every minute

[Timer]
OnBootSec=30
OnUnitActiveSec=60

[Install]
WantedBy=timers.target
UNIT

# ──────────────────────────────────────────────────────────────────────────────
# Del 7: Telemetry (enkle Prometheus-metrics i data/metrics.prom)
# ──────────────────────────────────────────────────────────────────────────────
cat > bin/metrics_exporter.py <<'PY'
#!/usr/bin/env python3
import os, json, pathlib, time
DATA = pathlib.Path(os.getenv("NOVA_HOME","${NOVA_HOME:-/home/nova/nova-bot}/data"))
EQUITY = DATA/"equity.json"
STATE  = DATA/"state.json"
OUT    = DATA/"metrics.prom"

def load(p, d): 
    try: return json.loads(p.read_text())
    except Exception as e:
return d

e = load(EQUITY, [])
s = load(STATE, {})
eq = (e[-1].get("equity_usd") if e else 0) or 0
draw = (e[-1].get("drawdown_day_usd") if e else 0) or 0
posn = len(s.get("positions", {}))
bot  = 1 if s.get("bot_enabled") else 0
mode = s.get("mode","paper")

lines = []
lines.append(f'novax_equity_usd {eq}')
lines.append(f'novax_drawdown_day_usd {draw}')
lines.append(f'novax_positions {posn}')
lines.append(f'novax_bot_enabled {bot}')
lines.append(f'novax_mode{{mode="{mode}"}} 1')

OUT.write_text("\n".join(lines)+"\n")
print("[metrics] wrote", OUT)
PY
chmod +x bin/metrics_exporter.py

cat > /etc/systemd/system/novax-metrics.service <<'UNIT'
[Unit]
Description=NovaX metrics exporter

[Service]
Type=oneshot
User=nova
WorkingDirectory=${NOVA_HOME:-/home/nova/nova-bot}
ExecStart=${NOVA_HOME:-/home/nova/nova-bot}/bin/metrics_exporter.py
UNIT

cat > /etc/systemd/system/novax-metrics.timer <<'UNIT'
[Unit]
Description=Write NovaX metrics every 30s

[Timer]
OnBootSec=25
OnUnitActiveSec=30

[Install]
WantedBy=timers.target
UNIT

# ──────────────────────────────────────────────────────────────────────────────
# Del 8: Alerts/regler (equity drop / ingen tick / TG 409)
# ──────────────────────────────────────────────────────────────────────────────
cat > bin/alerts.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}
source .env || true

alert () {
  local msg="$1"
  [[ -n "${TG_KEY:-}" && -n "${TG_CHAT:-}" ]] && \
    curl -s "https://api.telegram.org/bot${TG_KEY}/sendMessage" -d chat_id="${TG_CHAT}" -d text="$msg" >/dev/null
  echo "[alert] $msg"
}

# equity drop %
if [[ -f data/equity.json ]]; then
  last_eq=$(jq -r '.[-1].equity_usd // 0' data/equity.json 2>/dev/null || echo 0)
  eq5=$(jq -r '.[-5].equity_usd // 0' data/equity.json 2>/dev/null || echo "$last_eq")
  if [[ "$eq5" != "0" ]]; then
    drop=$(python3 - <<PY
a=$last_eq; b=$eq5
print(round(100*(a-b)/b,2))
PY
)
    thresh=${ALERT_EQUITY_DROP_PCT:-5}
    if (( $(echo "$drop < -$thresh" | bc -l) )); then
      alert "⚠️ Equity falt ${drop}% siste 5 punkter (grense ${thresh}%)"
    fi
  fi
fi

# ingen tick (state.json eldre enn 10 min)
if [[ -f data/state.json ]]; then
  age=$(( $(date +%s) - $(stat -c %Y data/state.json) ))
  if [[ $age -gt 600 ]]; then
    alert "⚠️ Ingen tick oppdatert på $age sek → sjekk engine"
  fi
fi

# TG 409 nylig?
if journalctl -u novax.service -n 80 --no-pager | grep -q ' 409 Client Error: Conflict '; then
  alert "⚠️ TG 409 oppdaget (getUpdates). Watchdog prøver å auto-heal."
fi
BASH
chmod +x bin/alerts.sh

cat > /etc/systemd/system/novax-alerts.service <<'UNIT'
[Unit]
Description=NovaX alerts

[Service]
Type=oneshot
User=nova
WorkingDirectory=${NOVA_HOME:-/home/nova/nova-bot}
ExecStart=${NOVA_HOME:-/home/nova/nova-bot}/bin/alerts.sh
UNIT

cat > /etc/systemd/system/novax-alerts.timer <<'UNIT'
[Unit]
Description=NovaX alerts every 2 minutes

[Timer]
OnBootSec=40
OnUnitActiveSec=120

[Install]
WantedBy=timers.target
UNIT

# ──────────────────────────────────────────────────────────────────────────────
# Del 9: Univers-bygger (AUTO_USDT spot top-N m/ fallback) + health
# ──────────────────────────────────────────────────────────────────────────────
cat > tools/build_universe.py <<'PY'
#!/usr/bin/env python3
import os, time, json, pathlib, sys
N = int(os.getenv("TOP_N","300"))
DATA = pathlib.Path(os.getenv("NOVA_HOME","${NOVA_HOME:-/home/nova/nova-bot}/data"))
STATE = DATA/"state.json"
UNI   = DATA/"universe_auto_usdt.json"

def write_state(symbols):
    s = {}
    try: s = json.loads(STATE.read_text() or "{}")
    except Exception as e:
s = {}
    s.setdefault("universe_cache", {"ts":0,"symbols":[]})
    s["universe_cache"]["ts"] = int(time.time())
    s["universe_cache"]["symbols"] = symbols
    STATE.write_text(json.dumps(s, separators=(",",":")))

def via_ccxt():
    import ccxt
    ex = ccxt.binance()
    mk = ex.load_markets()
    spot_usdt = [m["symbol"] for m in mk.values() if m.get("quote")=="USDT" and m.get("spot")]
    tick = ex.fetch_tickers(spot_usdt[:400])  # bulk i batches i ccxt
    ranked = sorted([k for k in tick if tick[k]], key=lambda k: -(tick[k].get("quoteVolume") or 0))
    return ranked[:N]

def fallback_minimum():
    return ["BTC/USDT","ETH/USDT","BNB/USDT","SOL/USDT","XRP/USDT","ADA/USDT","DOGE/USDT","AVAX/USDT","TON/USDT","LINK/USDT"][:N]

syms = []
try:
    syms = via_ccxt()
except Exception as e:
    syms = fallback_minimum()

UNI.write_text(json.dumps({"ts":int(time.time()),"symbols":syms}, separators=(",",":")))
write_state(syms)
print(f"[universe] symbols={len(syms)}  first={', '.join(syms[:10])}")
PY
chmod +x tools/build_universe.py

cat > /etc/systemd/system/novax-universe.service <<'UNIT'
[Unit]
Description=NovaX universe builder (AUTO_USDT)

[Service]
Type=oneshot
User=nova
WorkingDirectory=${NOVA_HOME:-/home/nova/nova-bot}
EnvironmentFile=${NOVA_HOME:-/home/nova/nova-bot}/.env
ExecStart=${NOVA_HOME:-/home/nova/nova-bot}/tools/build_universe.py
UNIT

cat > /etc/systemd/system/novax-universe.timer <<'UNIT'
[Unit]
Description=Rebuild trading universe hourly

[Timer]
OnBootSec=1min
OnUnitActiveSec=1h

[Install]
WantedBy=timers.target
UNIT

# ──────────────────────────────────────────────────────────────────────────────
# Del 10: Graceful shutdown-hook
# ──────────────────────────────────────────────────────────────────────────────
cat > bin/graceful_stop.py <<'PY'
#!/usr/bin/env python3
import json, pathlib, time, os
DATA = pathlib.Path(os.getenv("NOVA_HOME","${NOVA_HOME:-/home/nova/nova-bot}/data"))
STATE = DATA/"state.json"
s = {}
try: s = json.loads(STATE.read_text() or "{}")
except Exception as e:
s = {}
s["bot_enabled"]=False
s["last_shutdown_ts"]=time.time()
STATE.write_text(json.dumps(s, separators=(",",":")))
print("[graceful] bot_enabled=false skrevet")
PY
chmod +x bin/graceful_stop.py

# legg til ExecStop i novax.service dersom ikke finnes
if ! grep -q '^ExecStop=' /etc/systemd/system/novax.service; then
  sudo sed -i '/^\[Service\]/a ExecStop=${NOVA_HOME:-/home/nova/nova-bot}/bin/graceful_stop.py' /etc/systemd/system/novax.service
fi

# ──────────────────────────────────────────────────────────────────────────────
# Del 11: Utvidet healthcheck
# ──────────────────────────────────────────────────────────────────────────────
cat > bin/nova_healthcheck.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}

echo "== NovaX HEALTHCHECK (utvidet) =="
echo "Host: $(hostname)  User: $(whoami)  Uptime: $(uptime -p)"

echo -e "\n== systemd =="
systemctl is-active --quiet novax.service && echo "PASS: novax.service aktiv" || (echo "FAIL: novax.service nede"; exit 1)

echo -e "\n== .env =="
grep -E '^(NOVA_HOME|EXCHANGE|MODE|WATCHLIST|TOP_N|WATCH_TOP_N|LOG_LEVEL)=' ./.env || true

echo -e "\n== prosess/ENV =="
PID=$(pgrep -f 'nova.engine.run' | head -1 || echo "")
if [[ -n "$PID" ]]; then
  sudo tr '\0' '\n' </proc/$PID/environ | grep -E '^(NOVA_HOME|EXCHANGE|MODE)=' || true
else
  echo "WARN: fant ikke engine-prosess"
fi

echo -e "\n== Data/skrivetilgang =="
DATA_DIR=$(grep -E '^NOVA_HOME=' .env | tail -1 | cut -d= -f2-)
[[ -d "$DATA_DIR" ]] && echo "PASS: katalog $DATA_DIR" || echo "FAIL: mangler $DATA_DIR"
for f in equity.json state.json; do
  test -f "$DATA_DIR/$f" && stat -c "$f %y %sB" "$DATA_DIR/$f" || echo "WARN: $f mangler"
done

echo -e "\n== Universe-cache =="
python3 - <<'PY'
import json, pathlib, os
p=pathlib.Path('data/state.json')
try:
  s=json.loads(p.read_text() or "{}")
  u=s.get("universe_cache",{}).get("symbols",[])
  print("symbols:", len(u), " first10:", ", ".join(u[:10]))
except Exception as e:
  print("ERR:", e)
PY

echo -e "\n== Risk guard selftest =="
${NOVA_HOME:-/home/nova/nova-bot}/bin/risk_guard.py --selftest || true

echo -e "\n== Watchdog sanity =="
${NOVA_HOME:-/home/nova/nova-bot}/bin/watchdog.sh || true

echo -e "\n== Metrics snapshot =="
${NOVA_HOME:-/home/nova/nova-bot}/bin/metrics_exporter.py || true
tail -n +1 data/metrics.prom 2>/dev/null || true

echo -e "\n== Alerts dry-run =="
${NOVA_HOME:-/home/nova/nova-bot}/bin/alerts.sh || true

echo -e "\n== Universe build test =="
${NOVA_HOME:-/home/nova/nova-bot}/tools/build_universe.py || true

echo -e "\n== SQLite migrasjonstest =="
${NOVA_HOME:-/home/nova/nova-bot}/tools/migrate_to_sqlite.py || true

echo -e "\n== Oppsummering =="
echo "Hvis alt over viser PASS/OK og ingen kritiske FAIL: systemet ser bra ut."
BASH
chmod +x bin/nova_healthcheck.sh

# ──────────────────────────────────────────────────────────────────────────────
# Aktiver timere + reload services
# ──────────────────────────────────────────────────────────────────────────────
systemctl daemon-reload
systemctl enable --now novax-failsafe.timer novax-riskguard.timer novax-watchdog.timer novax-metrics.timer novax-backup.timer novax-universe.timer novax-alerts.timer >/dev/null

# Første kjøringer (engangs)
systemctl start novax-failsafe.service novax-riskguard.service novax-watchdog.service novax-metrics.service novax-universe.service novax-alerts.service >/dev/null 2>&1 || true

echo "==> Bootstrap ferdig."
echo "==> Kjør healthcheck: ${NOVA_HOME:-/home/nova/nova-bot}/bin/nova_healthcheck.sh"