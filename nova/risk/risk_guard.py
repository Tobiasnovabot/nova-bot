import os
from nova import paths as NPATH
#!/usr/bin/env python3
import os, time, json, pathlib, logging
from nova.paths import ensure_dirs as _np_ensure_dirs; _np_ensure_dirs()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s guard: %(message)s")
log = logging.getLogger("guard")

NOVA_HOME = pathlib.Path(os.getenv("NOVA_HOME", "/home/nova/nova-bot/data"))
STATE_JSON = NOVA_HOME / NPATH.STATE.as_posix()
GUARD_STATE = NOVA_HOME / "config" / "risk_guard_state.json"
GUARD_STATE.parent.mkdir(parents=True, exist_ok=True)

def _as_dict(x):
    if isinstance(x, dict): return x
    if isinstance(x, str):
        try: return json.loads(x or "{}")
        except Exception: return {}
    return {}

def _load_json(path: pathlib.Path, default=None):
    try:
        txt = path.read_text() if path.exists() else ""
        obj = json.loads(txt or "{}")
        return _as_dict(obj)
    except Exception:
        return default if default is not None else {}

def _save_json(path: pathlib.Path, obj):
    try: path.write_text(json.dumps(obj, separators=(",",":")))
    except Exception as e: log.warning("could not write %s: %s", path, e)

def _num(x, d=0.0):
    try: return float(x)
    except Exception: return float(d)

def main():
    st = _load_json(GUARD_STATE, {"trips":[], "last_ok": 0})
    _save_json(GUARD_STATE, st)

    interval = int(os.getenv("RISK_GUARD_INTERVAL_S", "30"))
    dd_cap_pct = _num(os.getenv("RISK_GUARD_MAX_DD_DAY_PCT", ""))  # ex: 3.0

    while True:
        try:
            s = _load_json(STATE_JSON, {})
            equity = _num(s.get("equity_usd", 0.0))
            dd_day = _num(s.get("dd_day_usd", 0.0))

            trips = _load_json(GUARD_STATE, {"trips":[]})
            trips = _as_dict(trips); trips.setdefault("trips", [])
            trips["last_ok"] = int(time.time())

            if dd_cap_pct > 0 and equity > 0:
                dd_pct = (dd_day / equity) * 100.0
                if dd_pct <= -abs(dd_cap_pct):
                    if not trips["trips"] or int(time.time()) - int(trips["trips"][-1].get("ts",0)) > 3600:
                        trips["trips"].append({"ts": int(time.time()), "reason": f"DD {dd_pct:.2f}% <= -{abs(dd_cap_pct):.2f}%"})
                    ctrl = _as_dict(s.get("ctrl", {}))
                    ctrl["safe_mode"] = True
                    s["ctrl"] = ctrl
                    try: STATE_JSON.write_text(json.dumps(s, separators=(",",":")))
                    except Exception as e: log.warning("persist safe_mode failed: %s", e)

            _save_json(GUARD_STATE, trips)

        except Exception as e:
            log.error("error: %s", e)

        time.sleep(max(5, interval))

if __name__ == "__main__":
    main()