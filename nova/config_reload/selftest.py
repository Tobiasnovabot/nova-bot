#!/usr/bin/env python3
import time, os
from nova.config_reload.reload import touch_reload_flag, should_reload
def main()->int:
    last=0.0
    assert not should_reload(last)
    f=touch_reload_flag()
    time.sleep(0.01)
    assert should_reload(last)
    os.remove(f)
    print("config_reload selftest: OK"); return 0
if __name__=="__main__": raise SystemExit(main())
