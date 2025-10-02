#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
_TRIPPED=False
_REASON=""

def trip(reason: str):
    global _TRIPPED,_REASON
    _TRIPPED=True; _REASON=reason

def check()->tuple[bool,str]:
    return (not _TRIPPED, _REASON)
