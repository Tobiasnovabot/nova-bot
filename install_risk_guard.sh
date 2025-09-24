#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}

mkdir -p nova/risk data/config

# 1) utvid risk-config med guard-terskler (beholder eksisterende verdier)
cat > data/config/risk.json <<'JSON'
{
  "base_risk_bps": 50,
  "max_notional_bps": 2000,
  "stop_frac_default": 0.010,
  "daily_loss_limit_bps": 200,
  "max_concurrent_positions": 5,
  "drawdown_tiers": [
    {"dd": 0.05, "mult": 1.00},
    {"dd": 0.10, "mult": 0.70},
    {"dd": 0.20, "mult": 0.50},
    {"dd": 9.99, "mult": 0.30}
  ],
  "guard": {
    "max_daily_loss_bps": 200,     // stans ved -2.00% på dagen
    "max_drawdown_bps": 2000,      // stans ved -20.00% fra peak
    "cooldown_minutes": 120        // hvor lenge bot_enabled holdes av etter stopp
  }
}
JSON

# 2) risk_guard daemon
cat > nova/risk/risk_guard.py <<'PY'
import json, time, os
from pathlib import Path
from datetime import datetime, timedelta

NOVA_HOME = Path(os.getenv("NOVA_HOME", "data"))
STATE = NOVA_HOME / "state.json"
EQUITY = NOVA_HOME / "equity.json"
CFG = NOVA_HOME / "config" / "risk.json"
GUARD_STATE = NOVA_HOME / "config" / "risk_guard_state.json"

def _load(p, default):
    try: return json.loads(p.read_text())
    except Exception: return default

def _save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, separators=(",",":")))

def _now(): return int(time.time())

def _equity_stats():
    eq = _load(EQUITY, [])
    if not eq: return (10_000.0, 10_000.0, 10_000.0, _now())
    eq = sorted(eq, key=lambda x: x.get("ts", 0))
    now = float(eq[-1].get("equity", 10_000.0))
    tnow = int(eq[-1].get("ts", _now()))
    peak = max(float(x.get("equity", 0.0)) for x in eq)
    day_cut = tnow - 86400
    last24 = [x for x in eq if x.get("ts", tnow) >= day_cut] or [eq[0]]
    day_start = float(last24[0].get("equity", now))
    return (now, day_start, peak, tnow)

def _tg_notify(msg: str):
    key = os.getenv("TG_KEY")
    chat = os.getenv("TG_CHAT")
    if not key or not chat: return
    try:
        import requests
        requests.post(f"https://api.telegram.org/bot{key}/sendMessage",
                      data={"chat_id": chat, "text": msg})
    except Exception:
        pass

def main():
    cfg = _load(CFG, {})
    guard = cfg.get("guard", {})
    max_daily_bps = float(guard.get("max_daily_loss_bps", 200))
    max_dd_bps = float(guard.get("max_drawdown_bps", 2000))
    cooldown_min = int(guard.get("cooldown_minutes", 120))

    last_mtime = 0
    while True:
        try:
            # poll kun ved filendring for lav CPU
            mtime = EQUITY.stat().st_mtime if EQUITY.exists() else 0
            if mtime == last_mtime:
                time.sleep(5); continue
            last_mtime = mtime

            eq_now, eq_day, eq_peak, tnow = _equity_stats()
            daily_pl = (eq_now - eq_day) / max(eq_day, 1e-9)
            dd = (eq_peak - eq_now) / max(eq_peak, 1e-9)

            st = _load(STATE, {})
            g = _load(GUARD_STATE, {})
            cooling_until = g.get("cooling_until", 0)

            reason = None
            if daily_pl <= -(max_daily_bps/10_000.0):
                reason = f"Daily loss {daily_pl*100:.2f}% >= limit {-(max_daily_bps/100):.2f}%"
            elif dd >= (max_dd_bps/10_000.0):
                reason = f"Drawdown {dd*100:.2f}% >= limit {(max_dd_bps/100):.2f}%"

            if reason:
                # slå av bot_enabled + sett cooldown
                st["bot_enabled"] = False
                until_ts = int(time.time()+cooldown_min*60)
                g = {
                    "cooling_until": until_ts,
                    "tripped_at": tnow,
                    "reason": reason,
                    "eq_now": eq_now, "eq_day": eq_day, "eq_peak": eq_peak
                }
                _save(STATE, st)
                _save(GUARD_STATE, g)
                _tg_notify(f"NovaX GUARD: STOPPER NYE TRADES\n{reason}\nCooldown {cooldown_min} min\nEquity now ${eq_now:,.2f}")
                print(f"[guard] TRIP: {reason} cooldown_until={until_ts}")
            else:
                # hvis cooldown er over – arm igjen
                if cooling_until and time.time() >= cooling_until:
                    if not st.get("bot_enabled", True):
                        st["bot_enabled"] = True
                        _save(STATE, st)
                        _save(GUARD_STATE, {"cooling_until": 0})
                        _tg_notify("NovaX GUARD: Bot re-ARMED etter cooldown")
                        print("[guard] RE-ARM bot_enabled=True")

        except Exception as e:
            print("[guard] error:", e)
        time.sleep(5)

if __name__ == "__main__":
    main()
PY

# 3) systemd service for guard
sudo tee /etc/systemd/system/novax-risk-guard.service >/dev/null <<'UNIT'
[Unit]
Description=NovaX Risk Guard
After=network-online.target novax.service
Wants=novax.service

[Service]
User=nova
WorkingDirectory=${NOVA_HOME:-/home/nova/nova-bot}
EnvironmentFile=${NOVA_HOME:-/home/nova/nova-bot}/.env
ExecStart=${NOVA_HOME:-/home/nova/nova-bot}/.venv/bin/python -u nova/risk/risk_guard.py
Restart=always
RestartSec=5
NoNewPrivileges=true
ProtectSystem=full

[Install]
WantedBy=multi-user.target
UNIT

# 4) enable + start
sudo systemctl daemon-reload
sudo systemctl enable --now novax-risk-guard.service

# 5) healthcheck
cat > ~/nova-bot/risk_guard_health.sh <<'HS'
#!/usr/bin/env bash
set -euo pipefail
echo "== Risk Guard Health =="
systemctl --no-pager --user=false status novax-risk-guard.service | sed -n '1,8p'
echo
echo "-- Last 40 lines --"
sudo journalctl -u novax-risk-guard.service -n 40 --no-pager
echo
echo "-- Guard state --"
test -f ${NOVA_HOME:-/home/nova/nova-bot}/data/config/risk_guard_state.json && cat ${NOVA_HOME:-/home/nova/nova-bot}/data/config/risk_guard_state.json || echo "(no trips)"
HS
chmod +x ~/nova-bot/risk_guard_health.sh

echo "== DONE =="
echo "Tips: Kjør ~/nova-bot/risk_guard_health.sh for status."