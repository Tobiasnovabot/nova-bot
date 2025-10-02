import json, time
from pathlib import Path

STORE = Path("runtime/strategy_overrides.json")

def load_overrides():
    try: return json.loads(STORE.read_text())
    except Exception: return {"disabled":[], "ts":0}

def save_overrides(data):
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(data, indent=2))

def set_enabled(name:str, enabled:bool):
    data = load_overrides()
    d=set(data.get("disabled",[]))
    if enabled: d.discard(name)
    else: d.add(name)
    data["disabled"]=sorted(d); data["ts"]=time.time()
    save_overrides(data)

def is_enabled(name:str)->bool:
    return name not in set(load_overrides().get("disabled",[]))
