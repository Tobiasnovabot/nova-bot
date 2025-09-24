#!/usr/bin/env python3
import os
import sys, time, importlib.util, pathlib

ROOT = pathlib.Path(os.getenv("NOVA_HOME",os.getenv("NOVA_HOME","/home/nova/nova-bot")))
sys.path.insert(0, str(ROOT))

router_path = ROOT / "nova/engine/router.py"
spec = importlib.util.spec_from_file_location("router", str(router_path))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
strategies = getattr(m, "REGISTERED", [])

print(f"[engine] loaded {len(strategies)} strategies: {[getattr(s,'NAME',type(s).__name__) for s in strategies]}")
# TODO: bytt ut med ekte loop. Nå bare heartbeat.
while True:
    time.sleep(10)