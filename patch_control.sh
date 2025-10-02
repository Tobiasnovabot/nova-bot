#!/usr/bin/env bash
set -euo pipefail

# === 1) runtime/control.json default ===
mkdir -p runtime
cat >runtime/control.json <<'JSON'
{
  "kill": false,
  "mode": "paper"
}
JSON

# === 2) Patch ultra_runner.py (kill-switch + mode) ===
UR="nova/engine/ultra_runner.py"
if ! grep -q "kill-switch aktivert" "$UR"; then
  sed -i '/while True:/a\
        try:\
            import json\
            from pathlib import Path\
            ctl = json.loads(Path("runtime/control.json").read_text())\
            if ctl.get("kill"):\
                print("[ultra] kill-switch aktivert – stopper loop", flush=True)\
                break\
            mode = ctl.get("mode", "paper")\
        except Exception:\
            pass' "$UR"
  echo "[OK] ultra_runner patched"
fi

# === 3) Patch apiapp/app.py (API endpoints) ===
APP="nova/engine/apiapp/app.py"
if ! grep -q "@app.post('/control/kill')" "$APP"; then
  cat >>"$APP" <<'PY'

@app.post('/control/kill')
def kill():
    from pathlib import Path, json
    f = Path("runtime/control.json")
    d = json.loads(f.read_text()) if f.exists() else {}
    d["kill"] = True
    f.write_text(json.dumps(d))
    return {"ok": True, "kill": True}

@app.post('/control/mode/{mode}')
def set_mode(mode: str):
    from pathlib import Path, json
    f = Path("runtime/control.json")
    d = json.loads(f.read_text()) if f.exists() else {}
    d["mode"] = mode
    f.write_text(json.dumps(d))
    return {"ok": True, "mode": mode}
PY
  echo "[OK] apiapp patched"
fi

echo "=== Patch ferdig ==="
