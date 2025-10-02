#!/usr/bin/env python3
from nova.confirm_gate.confirm import request, confirm
def main()->int:
    t=request("risk_set", {"level":20})
    ok,item=confirm(t)
    assert ok and item["payload"]["level"]==20
    ok2,_=confirm(t)
    assert not ok2
    print("confirm_gate selftest: OK"); return 0
if __name__=="__main__": raise SystemExit(main())
