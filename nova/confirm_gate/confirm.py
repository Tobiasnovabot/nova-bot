#!/usr/bin/env python3
from __future__ import annotations
import uuid
_PENDING={}
def request(action: str, payload: dict) -> str:
    t=str(uuid.uuid4())
    _PENDING[t]={"action":action,"payload":payload}
    return t
def confirm(token: str) -> tuple[bool,dict]:
    item=_PENDING.pop(token, None)
    return (item is not None, item or {})