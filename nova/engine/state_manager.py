import json, time, threading
from pathlib import Path
STATE_DIR = Path("/home/nova/nova-bot/state"); STATE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = Path("/home/nova/nova-bot/logs"); LOG_DIR.mkdir(parents=True, exist_ok=True)
FILES = {
  "trades": STATE_DIR/"trades.json",
  "equity": STATE_DIR/"equity.json",
  "signals": STATE_DIR/"signals.json",
  "positions": STATE_DIR/"positions.json",
  "runtime": STATE_DIR/"runtime.json",
}
_lock = threading.Lock()
def _safe_load(path, default):
    try:
        if path.exists(): return json.loads(path.read_text())
    except Exception:
        with (LOG_DIR/"state_errors.log").open("a") as f: f.write(f"{time.time()}: bad json in {path}\n")
    return default
def read_all():
    with _lock:
        return {
            "trades": _safe_load(FILES["trades"], []),
            "equity": _safe_load(FILES["equity"], {"timestamp": 0, "equity": 0.0, "pnl_total": 0.0}),
            "signals": _safe_load(FILES["signals"], {}),
            "positions": _safe_load(FILES["positions"], {}),
            "runtime": _safe_load(FILES["runtime"], {}),
        }
def write(name, data):
    with _lock:
        tmp = FILES[name].with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",",":")))
        tmp.replace(FILES[name])
def append_trade(trade):
    with _lock:
        trades = _safe_load(FILES["trades"], [])
        trades.append(trade)
        FILES["trades"].write_text(json.dumps(trades, separators=(",",":")))
