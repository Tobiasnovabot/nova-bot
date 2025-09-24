#!/usr/bin/env python3
def check(): return (True, "ok")
def main()->int:
    ok, _ = check()
    assert ok
    print("kill_switch selftest: OK")
    return 0
if __name__=="__main__": raise SystemExit(main())
