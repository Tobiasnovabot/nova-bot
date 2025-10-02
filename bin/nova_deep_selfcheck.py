#!/usr/bin/env python3
import os, sys, traceback, importlib, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]      # ~/nova-bot
if str(ROOT) not in sys.path:                   # <<< FIX: sørg for at 'nova' er importbar
    sys.path.insert(0, str(ROOT))

NOVA = ROOT / "nova"
SKIP_DIRS = {"__pycache__", "logs", "data", "backups", "log", "logrotate_cfg"}
os.environ.setdefault("NOVA_SAFE_IMPORT","1")

def modname_from_path(p: Path) -> str:
    rel = p.relative_to(ROOT).with_suffix("")
    return ".".join(rel.parts)

def safe_import_by_name(name: str):
    try:
        m = importlib.import_module(name)
        return ("pass","import ok", m)
    except Exception as e:
        tb = traceback.format_exception_only(type(e), e)[-1].strip()
        return ("fail", tb, None)

def safe_import_file(pyfile: Path):
    try:
        name = modname_from_path(pyfile)
        spec = importlib.util.spec_from_file_location(name, str(pyfile))
        m = importlib.util.module_from_spec(spec); sys.modules[name]=m
        assert spec and spec.loader
        spec.loader.exec_module(m)
        return (name, "pass", "import ok", m)
    except Exception as e:
        tb = traceback.format_exception_only(type(e), e)[-1].strip()
        return (str(pyfile), "fail", tb, None)

def run_selfcheck(mod):
    try:
        sc = getattr(mod, "selfcheck", None)
        if sc is None:
            try:
                sc = importlib.import_module(mod.__name__ + ".selfcheck")
            except Exception:
                return ("pass","no selfcheck (import ok)")
        if hasattr(sc, "run"):
            res = sc.run() or {}
            status = str(res.get("status","pass")).lower()
            notes = res.get("notes") or []
            return (status, "; ".join(map(str,notes)) or "selfcheck.run()")
        return ("pass","selfcheck module present, no run()")
    except Exception as e:
        tb = traceback.format_exception_only(type(e), e)[-1].strip()
        return ("fail","selfcheck error: "+tb)

def main():
    total_dirs=total_py=0
    results=[]
    for dirpath, dirnames, filenames in os.walk(NOVA):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        dpath = Path(dirpath); total_dirs += 1
        pyfiles = [f for f in filenames if f.endswith(".py")]

        if (dpath/"__init__.py").exists():  # package
            name = modname_from_path(dpath)
            status, note, mod = safe_import_by_name(name)
            results.append((name, status, note))
            if status=="pass" and mod:
                sc_status, sc_note = run_selfcheck(mod)
                if sc_note != "no selfcheck (import ok)":
                    results.append((name+":selfcheck", sc_status, sc_note))
        else:  # loose modules
            for f in sorted(pyfiles):
                mpath = dpath/f; total_py += 1
                name, status, note, mod = safe_import_file(mpath)
                results.append((name, status, note))
                if status=="pass" and mod:
                    sc_status, sc_note = run_selfcheck(mod)
                    if sc_note != "no selfcheck (import ok)":
                        results.append((name+":selfcheck", sc_status, sc_note))

    p=w=f=0
    for name, status, note in results:
        if   status=="pass": p+=1
        elif status=="warn": w+=1
        else: f+=1
        print(f"{name:60s} {status.upper():4s} {note}")
    print(f"\nDEEP SELF-CHECK SUMMARY: PASS={p} WARN={w} FAIL={f}  (dirs_scanned={total_dirs}, loose_py={total_py})")
    sys.exit(1 if f>0 else 0)

if __name__ == "__main__":
    main()
