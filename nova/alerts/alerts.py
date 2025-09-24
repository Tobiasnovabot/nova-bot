from __future__ import annotations
from nova.notify import send as tg_send
def info(msg: str): tg_send("ℹ️ " + msg)
def warn(msg: str): tg_send("🟠 " + msg)
def crit(msg: str): tg_send("🔴 " + msg)