import time, collections
_W = collections.deque(maxlen=32)

def ok(window_s: int = 120, max_errors: int = 5) -> bool:
    now = time.time()
    cutoff = now - window_s
    return sum(1 for t in _W if t > cutoff) < max_errors

def hit():
    _W.append(time.time())
