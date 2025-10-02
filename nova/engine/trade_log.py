from .persist import load_json, atomic_write_json, rotate
from time import time
def append_trade(path: str, ev: dict, rotate_every: int = 200):
    log = load_json(path, [])
    log.append({"t": int(time()), **ev})
    if len(log) % rotate_every == 0: rotate(path, keep=20)
    atomic_write_json(path, log)
