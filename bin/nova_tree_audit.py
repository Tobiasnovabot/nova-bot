#!/usr/bin/env python3
import os, sys, importlib, importlib.util, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
BASE = ROOT/"nova"
REPORT = ROOT/"data"/"audit_report.txt"
SKIP = {"__pycache__","logs","data","backups","log","logrotate_cfg"}
FIX_INIT = os.getenv("FIX_INIT","0")=="1"

def modname_from_path(p: Path) -> str:
    rel = p.relative_to(ROOT).with_suffix("")
    return ".".join(rel.parts)

def import_pkg(name: str):
    try:
        importlib.import_module(name); return ("PASS","import ok")
    except Exception as e:
        tb = traceback.format_exception_only(type(e), e)[-1].strip()
        return ("FAIL", tb)

def import_file(py: Path):
    try:
        name = modname_from_path(py)
        spec = importlib.util.spec_from_file_location(name, str(py))
        m = importlib.util.module_from_spec(spec); assert spec and spec.loader
        sys.modules[name]=m; spec.loader.exec_module(m)
        return (name,"PASS","import ok")
    except Exception as e:
        tb = traceback.format_exception_only(type(e), e)[-1].strip()
        return (str(py),"FAIL",tb)

def main():
    pkgs, files = [], []
    for dp, dns, fns in os.walk(BASE):
        dns[:] = [d for d in dns if d not in SKIP and not d.startswith(".")]
        d = Path(dp)
        if (d/"__init__.py").exists():
            pkgs.append(d)
        else:
            # “pakke”-kandidat uten __init__.py ?
            if any(fn.endswith(".py") for fn in fns):
                if FIX_INIT:
                    try: (d/"__init__.py").write_text("# auto-created\n")
                    except Exception: pass
                pkgs.append(d)
        for fn in fns:
            if fn.endswith(".py"): files.append(d/fn)

    lines = []
    p_ok=p_fail=f_ok=f_fail=0

    # Pakkesjekk
    for p in sorted(pkgs):
        name = modname_from_path(p)
        if not (p/"__init__.py").exists():
            lines.append(f"PKG  {name:40s} FAIL missing __init__.py")
            p_fail += 1
            continue
        st,msg = import_pkg(name)
        if st=="PASS": p_ok+=1
        else: p_fail+=1
        lines.append(f"PKG  {name:40s} {st} {msg}")

    # Løse filer (moduler) – importer de som ikke ligger som __init__.py
    for py in sorted(files):
        if py.name=="__init__.py": continue
        name,st,msg = import_file(py)
        if st=="PASS": f_ok+=1
        else: f_fail+=1
        lines.append(f"FILE {name:40s} {st} {msg}")

    summary = f"SUMMARY: PKG_PASS={p_ok} PKG_FAIL={p_fail} FILE_PASS={f_ok} FILE_FAIL={f_fail} (dirs_scanned={len(pkgs)})"
    lines.append(summary)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines)+"\n")
    print(summary)
    print(f"Report: {REPORT}")
if __name__ == "__main__":
    main()
