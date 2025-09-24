#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Selftest for lockguard:
- Prosess A tar lås og starter B.
- B skal feile med RuntimeError -> returncode 2.
"""
import os, sys, subprocess
from pathlib import Path

try:
    from .lockguard import single_instance
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.lockguard.lockguard import single_instance

LOCKNAME = "nova.lock"

def _child() -> int:
    try:
        with single_instance(LOCKNAME):
            # feil: barn fikk lås
            return 0
    except RuntimeError:
        return 2

def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "child":
        raise SystemExit(_child())

    with single_instance(LOCKNAME):
        p = subprocess.run(
            [sys.executable, "-m", "nova.lockguard.selftest", "child"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        assert p.returncode == 2, f"Barn returnerte {p.returncode}\nSTDERR:\n{p.stderr.decode()}"
    with single_instance(LOCKNAME):
        pass
    print("lockguard selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
