#!/usr/bin/env python3
from __future__ import annotations
import os, json, time
LOG=os.getenv("AUDIT_LOG","logs/audit.jsonl")
os.makedirs(os.path.dirname(LOG), exist_ok=True)
def audit(event: str, data: dict):
    rec={"ts": time.time(), "event": event, "data": data}
    with open(LOG,"a", encoding="utf-8") as f:
        f.write(json.dumps(rec)+"\n")
    return rec