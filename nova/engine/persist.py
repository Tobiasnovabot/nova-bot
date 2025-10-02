import json, os, tempfile, time, shutil
from typing import Any

def atomic_write_json(path: str, data: Any) -> None:
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=d, delete=False) as tmp:
        json.dump(data, tmp, separators=(",",":"))
        tmp.flush(); os.fsync(tmp.fileno())
        tmp_path = tmp.name
    os.replace(tmp_path, path)

def rotate(path: str, keep: int = 10) -> None:
    if not os.path.exists(path): return
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup = f"{path}.{ts}.bak"
    shutil.copy2(path, backup)
    # prune
    base = os.path.basename(path)
    dirn = os.path.dirname(path) or "."
    snaps = sorted([f for f in os.listdir(dirn) if f.startswith(base) and f.endswith(".bak")])
    for f in snaps[:-keep]:
        try: os.remove(os.path.join(dirn,f))
        except: pass

def load_json(path: str, default: Any) -> Any:
    try:
        with open(path,"r") as f: return json.load(f)
    except: return default
