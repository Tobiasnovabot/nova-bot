import os, json, time, subprocess, pathlib
from nova.telemetry.notify_tg import send_alert

DATA = pathlib.Path(os.getenv("NOVA_HOME", "data"))
STATE = DATA / "state.json"
MIN = int(os.getenv("ALERT_MIN_UNIVERSE","200"))
NOW = time.time()

def mtime_ok(path, max_age=600):
    try:
        return NOW - path.stat().st_mtime <= max_age
    except FileNotFoundError:
        return False

def last_heartbeat_ok():
    try:
        out = subprocess.check_output(["journalctl","-u","novax.service","-n","100","--no-pager","-o","cat"], timeout=5).decode()
        # se etter "engine heartbeat" siste 10 min
        return ("engine heartbeat" in out)
    except Exception:
        return False

problems = []

# 1) state.json rører seg?
if not mtime_ok(STATE, 600):
    problems.append("state.json ikke oppdatert siste 10 min")

# 2) universe størrelse
try:
    s = json.loads(STATE.read_text() or "{}")
    uni = s.get("universe_cache",{}).get("symbols",[])
    if len(uni) < MIN:
        problems.append(f"universe={len(uni)} < min={MIN}")
except Exception as e:
    problems.append(f"state.json lesefeil: {e}")

# 3) heartbeat
if not last_heartbeat_ok():
    problems.append("ingen 'engine heartbeat' observert i journal nylig")

if problems:
    send_alert("Watchdog avvik", "\n".join(f"- {p}" for p in problems))
print("OK" if not problems else "ALERT:", "; ".join(problems))
