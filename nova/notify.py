from pathlib import Path
from datetime import datetime, timezone, timezone
LOG = Path("logs/notify.log")
def send(msg: str):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    return True
