#!/usr/bin/env python3
import os, json
from nova.audit_log.audit import audit, LOG
def main()->int:
    r=audit("test_event", {"k":1})
    assert os.path.exists(LOG)
    with open(LOG,"r", encoding="utf-8") as f:
        last=json.loads(f.readlines()[-1])
    assert last["event"]=="test_event" and last["data"]["k"]==1
    print("audit_log selftest: OK"); return 0
if __name__=="__main__": raise SystemExit(main())
