#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time, math, os, sys
from pathlib import Path

try:
    from .scaling_dist import map_distributed
except Exception:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from nova.scaling_dist.scaling_dist import map_distributed

# CPU-bound, deterministisk jobb
def _job(seed: int) -> int:
    x = int(seed) & 0x7fffffff
    for _ in range(40_000):                 # ca. noen ms per jobb
        x = (1103515245 * x + 12345) & 0x7fffffff
    return x

def _bench(n_jobs: int, workers: int) -> float:
    items = list(range(n_jobs))
    t0 = time.perf_counter()
    _ = map_distributed(_job, items, workers=workers)
    dt = time.perf_counter() - t0
    return dt

def main() -> int:
    n = 600  # total jobber
    t1 = _bench(n, workers=1)
    t4 = _bench(n, workers=4)

    thr1 = n / t1
    thr4 = n / t4
    # krav: 4 workers skal gi >= 2.5x throughput vs 1 worker (toleranse for miljø)
    speedup = thr4 / thr1 if thr1 > 0 else 0.0
    assert speedup >= 2.5, f"For lav skalering: speedup={speedup:.2f}x (t1={t1:.3f}s, t4={t4:.3f}s)"

    # grunnsjekk: resultatrekkefølge korrekt og deterministisk
    res1 = map_distributed(_job, range(32), workers=3)
    res2 = map_distributed(_job, range(32), workers=2)
    assert res1 == res2, "Resultater må være deterministiske og i original rekkefølge"

    print("scaling_dist selftest: OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
