from nova import paths as NPATH
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Selftest for core_boot.
"""
import os, sys, time
from pathlib import Path

try:
    from .core_boot import (
        NOVA_HOME, ensure_nova_home, write_json_atomic, read_json_atomic,
        rotate_backups, now_oslo
    )
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.core_boot.core_boot import (
        NOVA_HOME, ensure_nova_home, write_json_atomic, read_json_atomic,
        rotate_backups, now_oslo
    )

def main() -> int:
    test_home = Path(f"/tmp/nova_home/core_boot_test-{os.getpid()}").resolve()
    os.environ["NOVA_HOME"] = str(test_home)
    test_home.mkdir(parents=True, exist_ok=True)
    (test_home / "logs").mkdir(exist_ok=True)
    (test_home / "data").mkdir(exist_ok=True)

    t = now_oslo()
    assert t.tzinfo is not None

    state_path = test_home / "data" / NPATH.STATE.as_posix()
    sample = {"ok": True, "n": 1}
    write_json_atomic(state_path, sample, backup=False)
    got = read_json_atomic(state_path, default=None)
    assert got == sample

    for i in range(10):
        sample["n"] = i + 2
        write_json_atomic(state_path, sample, backup=True)
        time.sleep(0.005)
    deleted = rotate_backups(state_path, keep=5)
    assert deleted >= 1

    ensure_nova_home()
    assert (test_home / "logs").exists()
    assert (test_home / "data").exists()

    print("core_boot selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
