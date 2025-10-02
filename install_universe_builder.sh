#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}

mkdir -p nova/universe data/config

# 1) Konfig (kan justeres i .env også)
cat > data/config/universe.json <<'JSON'
{
  "exchange": "binance",
  "quote": "USDT",
  "market_type": "spot",
  "top_n": 300,
  "min_quote_volume_usd": 100000,
  "refresh_minutes": 15
}
JSON

# 2) Universe Builder
cat > nova/universe/universe_builder.py <<'PY'
import os, json, time
from pathlib import Path

NOVA_HOME = Path(os.getenv("NOVA_HOME", "data"))
STATE = NOVA_HOME / "state.json"
CONF = NOVA_HOME / "config" / "universe.json"

def _load(p, d):
    try: return json.loads(p.read_text() or "")
    except Exception: return d

def _save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, separators=(",",":")))

def _env(name, default=None):
    v = os.getenv(name)
    return v if v is not None else default

def pick_symbols():
    import ccxt
    cfg = _load(CONF, {})
    exch_name = _env("EXCHANGE", cfg.get("exchange","binance"))
    quote = cfg.get("quote","USDT")
    top_n = int(_env("TOP_N", str(cfg.get("top_n", 300))))
    min_qv = float(cfg.get("min_quote_volume_usd", 100_000))
    market_type = cfg.get("market_type", "spot")  # "spot" | "swap"

    ex = getattr(ccxt, exch_name)()
    markets = ex.load_markets()
    syms = []
    for m in markets.values():
        if not m.get("active"): continue
        if m.get("quote") != quote: continue
        if market_type and m.get("type") != market_type: continue
        syms.append(m["symbol"])

    if not syms:
        return []

    # Hent tickers i batch der det er mulig
    tickers = {}
    try:
        # Noen børser krever None for alle tickers
        tickers = ex.fetch_tickers(syms)
    except Exception:
        # fallback: per-symbol (langsomt, men robust)
        for s in syms:
            try: tickers[s] = ex.fetch_ticker(s)
            except Exception: pass

    # ranger på quoteVolume hvis finnes, ellers 0
    ranked = sorted(
        (s for s in syms if s in tickers),
        key=lambda s: -(tickers.get(s,{}).get("quoteVolume") or 0.0)
    )
    ranked = [s for s in ranked if (tickers.get(s,{}).get("quoteVolume") or 0.0) >= min_qv] or ranked
    return ranked[:top_n]

def write_universe(symbols):
    st = _load(STATE, {})
    uc = st.setdefault("universe_cache", {"ts":0,"symbols":[]})
    uc["symbols"] = symbols
    uc["ts"] = int(time.time())
    _save(STATE, st)

def notify(msg):
    key = os.getenv("TG_KEY"); chat = os.getenv("TG_CHAT")
    if not key or not chat: 
        print(msg); return
    try:
        import requests
        requests.post(f"https://api.telegram.org/bot{key}/sendMessage",
                      data={"chat_id": chat, "text": msg}, timeout=5)
    except Exception:
        pass
    print(msg)

def main():
    try:
        syms = pick_symbols()
        write_universe(syms)
        notify(f"UniverseBuilder: AUTO_USDT oppdatert: {len(syms)} symbols (TOP_N)")
    except Exception as e:
        notify(f"UniverseBuilder: FEIL: {e}")

if __name__ == "__main__":
    main()
PY

# 3) systemd timer som oppdaterer automatisk
sudo tee /etc/systemd/system/novax-universe-builder.service >/dev/null <<'UNIT'
[Unit]
Description=NovaX Universe Builder (AUTO_USDT)
After=network-online.target novax.service
Wants=novax.service

[Service]
User=nova
WorkingDirectory=${NOVA_HOME:-/home/nova/nova-bot}
EnvironmentFile=${NOVA_HOME:-/home/nova/nova-bot}/.env
ExecStart=${NOVA_HOME:-/home/nova/nova-bot}/.venv/bin/python -u nova/universe/universe_builder.py
Nice=10
NoNewPrivileges=true
ProtectSystem=full
UNIT

sudo tee /etc/systemd/system/novax-universe-builder.timer >/dev/null <<'UNIT'
[Unit]
Description=Run Universe Builder periodically

[Timer]
OnBootSec=1min
OnUnitActiveSec=15min
Unit=novax-universe-builder.service
AccuracySec=30s
Persistent=true

[Install]
WantedBy=timers.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now novax-universe-builder.timer

# 4) Manuell første kjøring
sudo systemctl start novax-universe-builder.service

# 5) liten healthcheck
cat > ~/nova-bot/universe_health.sh <<'HS'
#!/usr/bin/env bash
set -euo pipefail
echo "== Universe Builder Health =="
systemctl status novax-universe-builder.timer --no-pager | sed -n '1,8p'
echo
systemctl status novax-universe-builder.service --no-pager | sed -n '1,12p'
echo
echo "-- Siste 50 linjer --"
sudo journalctl -u novax-universe-builder.service -n 50 --no-pager
echo
echo "-- Nåværende universe_cache --"
python3 - <<'PY'
import json, pathlib
p=pathlib.Path('data/state.json')
s=json.loads(p.read_text() or "{}")
u=s.get('universe_cache',{})
print("ts:", u.get("ts"))
print("count:", len(u.get("symbols",[])))
print("first 20:", ", ".join((u.get("symbols") or [])[:20]))
PY
HS
chmod +x ~/nova-bot/universe_health.sh

echo "== DONE =="
echo "Bruk: ~/nova-bot/universe_health.sh"