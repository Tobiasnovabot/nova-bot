#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from collections import defaultdict
_E=defaultdict(lambda:0.0)
_A=defaultdict(lambda:0)

def update(sym: str, eff_px: float, mid_px: float, alpha: float=0.2):
    if mid_px<=0: return
    bps = (abs(eff_px-mid_px)/mid_px)*10_000.0
    _E[sym] = (1-alpha)*_E[sym] + alpha*bps
    _A[sym]+=1

def get(sym: str, default_bps: float=10.0)->float:
    return _E[sym] if _A[sym]>0 else default_bps
