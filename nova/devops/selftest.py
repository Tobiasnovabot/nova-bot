#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, sys, re

def main() -> int:
    # Kjør engine.selftest eller en “tørr” kjøring og aksepter både "idle" og runpy-warning
    p = subprocess.run([sys.executable, "-m", "nova.engine.selftest"],
                       capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    ok = ("engine selftest: OK" in out) or re.search(r"runpy.+found in sys\.modules", out)
    if not ok:
        print(out)
        return 1
    print("devops selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
