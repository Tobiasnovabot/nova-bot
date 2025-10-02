#!/usr/bin/env python3
from nova.hedge_engine.hedge import hedge_size
def main()->int:
    h=hedge_size(beta=0.7, exposure_usd=1000, cap_frac=0.5)
    assert 300<=h<=400
    print("hedge_engine selftest: OK"); return 0
if __name__=="__main__": raise SystemExit(main())
