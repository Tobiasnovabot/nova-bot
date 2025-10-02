def schedule(qty0: float, steps: int, add_frac: float):
    out=[]; q=qty0
    for i in range(steps):
        out.append(q if i==0 else (q:=q*add_frac))
    return out
