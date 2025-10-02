#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, time, subprocess, fnmatch
from pathlib import Path

def discover_selftests() -> list[str]:
    """
    Finn alle moduler under 'nova' som har en selftest.py,
    uten å være avhengig av pkg.__file__ (fungerer også for namespace-pakker).
    """
    base = Path(__file__).resolve().parents[1]  # peker på .../nova
    mods = []
    for p in base.rglob("selftest.py"):
        # bygg modulnavn som 'nova.x.y.selftest'
        rel = p.relative_to(base).with_suffix("")  # eks: microstructure/selftest
        parts = ("nova",) + rel.parts              # ('nova','microstructure','selftest')
        mod = ".".join(parts)
        mods.append(mod)
    # unik & sortert
    return sorted(set(mods))

def should_skip(mod: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(mod, pat.strip()) for pat in patterns if pat.strip())

def main() -> int:
    skip_env = os.getenv("NOVA_SKIP", "")
    skip_patterns = [s for s in skip_env.split(",") if s.strip()]

    mods = discover_selftests()
    print("Oppdaget selftests:", len(mods))
    if skip_patterns:
        print("Skipper mønstre:", skip_patterns)
    else:
        print("Tips: bruk NOVA_SKIP for å hoppe over tunge/nettverks-tester, f.eks.:")
        print("     NOVA_SKIP=nova.exchange.selftest,nova.universe.selftest,nova.engine.selftest,nova.devops.selftest")

    ok = fail = skipc = 0
    results: list[tuple[str,str,float]] = []
    t0_all = time.time()

    for mod in mods:
        if should_skip(mod, skip_patterns):
            results.append((mod, "SKIP", 0.0)); skipc += 1
            continue
        print(f">> {mod}")
        t0 = time.time()
        r = subprocess.run([sys.executable, "-m", mod])
        dt = time.time() - t0
        if r.returncode == 0:
            results.append((mod, "OK", dt)); ok += 1
        else:
            results.append((mod, "FAIL", dt)); fail += 1

    dt_all = time.time() - t0_all
    print("\n=== SAMMENDRAG ===")
    for mod, status, dt in results:
        print(f"{status:4}  {mod:45s} {dt:6.2f}s")
    print(f"\nTotalt: {len(mods)}  OK: {ok}  FAIL: {fail}  SKIP: {skipc}  Tid: {dt_all:.1f}s")
    return 0 if fail == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
