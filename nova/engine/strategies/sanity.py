_n = 0
def signal(symbol, price, broker):
    global _n
    _n += 1
    return 1 if _n % 2 else -1
