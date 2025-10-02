import importlib, os, pkgutil, sys, traceback
from pathlib import Path

def iter_top_packages():
    nova_dir = Path(__file__).resolve().parents[1]  # ~/nova-bot/nova
    for m in pkgutil.iter_modules([str(nova_dir)]):
        if m.ispkg:
            yield m.name

SKIP = {"logs","data","backups","__pycache__"}

def run_one(pkg: str):
    os.environ.setdefault("NOVA_SAFE_IMPORT","1")
    try:
        # Dedikert modul-sjekk hvis finnes
        try:
            sc = importlib.import_module(f"nova.{pkg}.selfcheck")
            if hasattr(sc, "run"):
                res = sc.run() or {}
                status = str(res.get("status","pass")).lower()
                notes = res.get("notes") or []
                return (pkg, status, notes)
        except ModuleNotFoundError:
            pass
        # Fallback: kan vi importere pakken?
        importlib.import_module(f"nova.{pkg}")
        return (pkg, "pass", ["import ok"])
    except Exception as e:
        tb = traceback.format_exception_only(type(e), e)[-1].strip()
        return (pkg, "fail", [tb])

def run_all():
    out = []
    for pkg in sorted(set(iter_top_packages()) - SKIP):
        out.append(run_one(pkg))
    return out

def run_cli():
    res = run_all()
    p=w=f=0
    for name, status, notes in res:
        if status=="pass": p+=1
        elif status=="warn": w+=1
        else: f+=1
        msg = "; ".join(notes) if notes else ""
        print(f"{name:28s} {status.upper():4s} {msg}")
    print(f"SELF-CHECK SUMMARY: PASS={p} WARN={w} FAIL={f}")
    sys.exit(1 if f>0 else 0)

if __name__ == "__main__":
    run_cli()
