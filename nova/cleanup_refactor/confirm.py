#!/usr/bin/env python3
from __future__ import annotations
# -*- coding: utf-8 -*-
import time
from typing import Callable, Any, Dict

class ConfirmError(RuntimeError):
    pass

def want_confirm(big_change: bool, *, ttl_sec: int = 60) -> Dict[str, Any]:
    """
    Returnér et confirm-token som må sendes inn igjen innen ttl.
    Bruk: send token til operatør (TG) og kall funksjonen på nytt med token.
    """
    return {
        "confirm": True,
        "token": f"conf-{int(time.time())}",
        "expires_at": time.time() + ttl_sec,
        "ttl": ttl_sec,
        "big_change": bool(big_change),
    }

def confirm_required(fn: Callable) -> Callable:
    """
    Dekoratør for farlige endringer. Forventer kwargs:
      confirm_token: str|None
      confirm_info: dict fra want_confirm() (cache i state/TG-ctx)
    Flyt:
      1) Kall uten gyldig token -> kaster ConfirmError m/ want_confirm payload.
      2) Kall med gyldig token før utløp -> kjører.
    """
    def _wrap(*args, **kwargs):
        info = kwargs.pop("confirm_info", None)
        token = kwargs.pop("confirm_token", None)
        if not info or not isinstance(info, dict):
            raise ConfirmError(want_confirm(big_change=True))
        if not token or token != info.get("token"):
            raise ConfirmError(want_confirm(big_change=True))
        if time.time() > float(info.get("expires_at", 0)):
            raise ConfirmError(want_confirm(big_change=True))
        return fn(*args, **kwargs)
    return _wrap