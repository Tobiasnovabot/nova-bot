import time
_last = 0

def signal(symbol, price, broker):
    global _last
    now = int(time.time())
    # Ett signal hvert 60. sekund, alterner kjøp/selg
    if now // 60 != _last:
        _last = now // 60
        return 1 if _last % 2 == 0 else -1
    return 0
