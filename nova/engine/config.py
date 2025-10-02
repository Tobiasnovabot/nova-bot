from __future__ import annotations
import os
from pathlib import Path
def load_env():
    p=Path("/home/nova/nova-bot/.env")
    if p.exists():
        for line in p.read_text().splitlines():
            line=line.strip()
            if not line or line.startswith("#") or "=" not in line: continue
            k,v=line.split("=",1); os.environ.setdefault(k.strip(), v.strip())
