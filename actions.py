import os
# actions.py
import json, yaml, pathlib, shutil, subprocess, os
from fs_safety import backup, atomic_write_text
from validators import in_allow
from patch_py import insert_after_marker   # øverst ved imports

def _ensure_allowed(path:str):
    if not in_allow(path): raise PermissionError(f"blocked path: {path}")

def mkdir(path:str, dry=False):
    _ensure_allowed(path)
    if dry: return {"ok":True,"dry":True}
    pathlib.Path(path).mkdir(parents=True, exist_ok=True); return {"ok":True}

def write(path:str, content:str, dry=False):
    _ensure_allowed(path)
    if dry: return {"ok":True,"dry":True,"preview":content[:2000]}
    backup(path); atomic_write_text(path, content); return {"ok":True}

def patch_json(path:str, ops:list, dry=False):
    _ensure_allowed(path)
    p = pathlib.Path(path); data={}
    if p.exists(): data = json.loads(p.read_text() or "{}")
    before = json.dumps(data, indent=2, ensure_ascii=False)
    for op in ops:
        key = op["set"]; val = op["value"]
        cur = data; parts = key.split(".")
        for k in parts[:-1]: cur = cur.setdefault(k,{})
        cur[parts[-1]]=val
    after = json.dumps(data, indent=2, ensure_ascii=False)
    if dry: return {"ok":True,"dry":True,"diff_from":before,"diff_to":after}
    backup(path); atomic_write_text(path, after); return {"ok":True}

def patch_yaml(path:str, ops:list, dry=False):
    _ensure_allowed(path)
    p = pathlib.Path(path); data={}
    if p.exists(): data = yaml.safe_load(p.read_text()) or {}
    before = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    for op in ops:
        key = op["set"]; val = op["value"]
        cur = data; parts = key.split(".")
        for k in parts[:-1]: cur = cur.setdefault(k,{})
        cur[parts[-1]]=val
    after = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    if dry: return {"ok":True,"dry":True,"diff_from":before,"diff_to":after}
    backup(path); atomic_write_text(path, after); return {"ok":True}

def systemctl(action:str, unit:str, dry=False):
    if dry: return {"ok":True,"dry":True,"action":action,"unit":unit}
    r = subprocess.run(["/bin/systemctl", action, unit], capture_output=True, text=True)
    return {"ok": r.returncode==0, "code": r.returncode, "stdout": r.stdout[-800:], "stderr": r.stderr[-800:]}

def patch_py(path:str, marker:str, snippet:str, dry=False):
    _ensure_allowed(path)
    res = insert_after_marker(path, marker, snippet)
    if dry:
        return {"ok":True,"dry":True,"diff_from":res["old"],"diff_to":res["new"]}
    backup(path); atomic_write_text(path, res["new"]); return {"ok":True}

def selftest()->bool:
    root="/opt/guardian/_selftest_actions"
    mkdir(root)
    f=f"{root}/a.json"
    write(f, "{}")
    patch_json(f, [{"set":"x.y","value":1}])
    assert json.loads(pathlib.Path(f).read_text())["x"]["y"]==1
    return True

if __name__=="__main__":
    print("actions selftest:", selftest())
