#!/usr/bin/env python3
from nova.redundancy.ha import decide_role
def main()->int:
    assert decide_role(0.0, 100.0, 30.0)=="primary"
    assert decide_role(90.0, 100.0, 30.0)=="standby"
    print("redundancy selftest: OK"); return 0
if __name__=="__main__": raise SystemExit(main())
