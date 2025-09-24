from collections import deque
class SMA:
    def __init__(self, n): self.n=n; self.buf=deque(maxlen=n)
    def update(self, x): self.buf.append(float(x)); return sum(self.buf)/len(self.buf)
class EMA:
    def __init__(self, n): self.n=n; self.k=2/(n+1); self.v=None
    def update(self, x):
        x=float(x)
        self.v = x if self.v is None else (x-self.v)*self.k + self.v
        return self.v
