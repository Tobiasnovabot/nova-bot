# fs_safety.py
import os, pathlib, shutil, time, hashlib, json, tempfile

BACKUPS = pathlib.Path("/opt/guardian/backups")
LOGS = pathlib.Path("/opt/guardian/logs")
for p in (BACKUPS, LOGS): p.mkdir(parents=True, exist_ok=True)

def file_hash(path:str)->str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""): h.update(chunk)
    return h.hexdigest()

def backup(path:str)->str|None:
    p = pathlib.Path(path)
    if not p.exists(): return None
    ts = time.strftime("%Y%m%d-%H%M%S")
    b = BACKUPS / f"{p.name}.{ts}.bak"
    shutil.copy2(p, b)
    return str(b)

def atomic_write_text(path:str, content:str, encoding="utf-8")->None:
    tmp = pathlib.Path(path + ".tmp")
    tmp.write_text(content, encoding=encoding)
    os.replace(tmp, path)

def atomic_write_bytes(path:str, data:bytes)->None:
    tmp = pathlib.Path(path + ".tmp")
    with open(tmp, "wb") as f: f.write(data)
    os.replace(tmp, path)

def selftest()->bool:
    root = pathlib.Path("/opt/guardian/_selftest"); root.mkdir(parents=True, exist_ok=True)
    f = root / "t.txt"
    atomic_write_text(str(f), "a")
    assert f.read_text()=="a"
    h1 = file_hash(str(f))
    backup(str(f))
    atomic_write_text(str(f), "b")
    assert f.read_text()=="b" and file_hash(str(f))!=h1
    return True

if __name__=="__main__":
    ok = selftest()
    print("fs_safety selftest:", ok)
