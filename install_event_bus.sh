#!/usr/bin/env bash
set -euo pipefail
cd ${NOVA_HOME:-/home/nova/nova-bot}

mkdir -p nova/observer data/logs

# 1) Event Tap: leser journalctl for novax.service, parser og skriver JSONL
cat > nova/observer/event_tap.py <<'PY'
import os, re, sys, json, time, subprocess, threading
from pathlib import Path
NOVA_HOME = Path(os.getenv("NOVA_HOME","data"))
LOGDIR = NOVA_HOME/"logs"; LOGDIR.mkdir(parents=True, exist_ok=True)
EVT = LOGDIR/"events.jsonl"
TRD = NOVA_HOME/"trades.json"

TG_KEY = os.getenv("TG_KEY"); TG_CHAT = os.getenv("TG_CHAT")
def tg(msg: str):
    if not TG_KEY or not TG_CHAT: return
    try:
        import requests
        requests.post(f"https://api.telegram.org/bot{TG_KEY}/sendMessage",
                      data={"chat_id": TG_CHAT, "text": msg}, timeout=5)
    except Exception:
        pass

# regex for paper fills & engine info
R_PAPER = re.compile(
    r'\[paper\]\s+(?P<sym>[A-Z0-9/_\-]+)\s+(?P<side>buy|sell)\s+qty=(?P<qty>[0-9.eE+-]+)\s+px=(?P<px>[0-9.eE+-]+)\s+eff=(?P<eff>[0-9.eE+-]+)\s+stop=(?P<stop>[0-9.eE+-]+)'
)
R_ENGINE_WATCH = re.compile(r'\[engine\].*watchN=(?P<n>\d+)')
R_ERROR = re.compile(r'ERROR|Traceback|Exception', re.I)

def append_jsonl(path: Path, obj: dict):
    with path.open("a", buffering=1) as f:
        f.write(json.dumps(obj, separators=(",",":"))+"\n")

def read_trades():
    try: return json.loads(TRD.read_text() or "[]")
    except Exception: return []

def write_trades(arr):
    TRD.parent.mkdir(parents=True, exist_ok=True)
    TRD.write_text(json.dumps(arr, separators=(",",":")))

def handle_line(line: str):
    ts = time.time()
    m = R_PAPER.search(line)
    if m:
        d = {"ts": ts, "type":"paper_fill", **m.groupdict()}
        # cast
        for k in ("qty","px","eff","stop"):
            try: d[k]=float(d[k])
            except Exception as e:
pass
        append_jsonl(EVT, d)
        # også i trades.json (append)
        arr = read_trades()
        arr.append({
            "ts": ts, "sym": d["sym"], "side": d["side"],
            "qty": d.get("qty"), "price": d.get("px"),
            "pnl": None, "status":"filled_paper"
        })
        write_trades(arr)
        tg(f"Paper {d['side'].upper()} {d['sym']} qty={d['qty']} px={d['px']}")
        return

    m = R_ENGINE_WATCH.search(line)
    if m:
        d = {"ts": ts, "type":"engine_watch", "watchN": int(m.group("n"))}
        append_jsonl(EVT, d)
        return

    if R_ERROR.search(line):
        d = {"ts": ts, "type":"error", "msg": line.strip()[:500]}
        append_jsonl(EVT, d)
        tg("NovaX ERROR: " + d["msg"])
        return

def stream():
    # follow only new lines from now
    cmd = ["journalctl","-u","novax.service","-f","-o","cat","-n","0"]
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
        for line in proc.stdout:
            try: handle_line(line)
            except Exception: pass

if __name__ == "__main__":
    # touch files for sanity
    EVT.touch(exist_ok=True)
    if not TRD.exists(): write_trades([])
    stream()
PY

# 2) systemd for Event Tap
sudo tee /etc/systemd/system/novax-event-tap.service >/dev/null <<'UNIT'
[Unit]
Description=NovaX Event Bus (journal tap)
After=novax.service
Requires=novax.service

[Service]
User=nova
WorkingDirectory=${NOVA_HOME:-/home/nova/nova-bot}
EnvironmentFile=${NOVA_HOME:-/home/nova/nova-bot}/.env
ExecStart=${NOVA_HOME:-/home/nova/nova-bot}/.venv/bin/python -u nova/observer/event_tap.py
Restart=always
RestartSec=3
NoNewPrivileges=true
ProtectSystem=full

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now novax-event-tap.service

# 3) Healthcheck
cat > ~/nova-bot/event_bus_health.sh <<'HS'
#!/usr/bin/env bash
set -euo pipefail
echo "== Event Bus Health =="
systemctl status novax-event-tap.service --no-pager | sed -n '1,15p'
echo
echo "-- Siste 40 logglinjer (event tap) --"
sudo journalctl -u novax-event-tap.service -n 40 --no-pager
echo
echo "-- Siste 10 events.jsonl --"
tail -n 10 ${NOVA_HOME:-/home/nova/nova-bot}/data/logs/events.jsonl || true
echo
echo "-- trades.json (antall + siste) --"
python3 - <<'PY'
import json, pathlib
p=pathlib.Path('${NOVA_HOME:-/home/nova/nova-bot}/data/trades.json')
try:
    a=json.loads(p.read_text() or "[]")
    print("trades:", len(a))
    if a:
        last=a[-1]; keep={k:last.get(k) for k in ("ts","sym","side","qty","price","pnl","status")}
        print("last:", keep)
except Exception as e:
    print("trades: (ingen)", e)
PY
HS
chmod +x ~/nova-bot/event_bus_health.sh

echo "== DONE =="
echo "Bruk: ~/nova-bot/event_bus_health.sh"