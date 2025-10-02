from nova import paths as NPATH
import os, json, pathlib, time, gzip, shutil

DATA = pathlib.Path(os.getenv("NOVA_HOME","data"))
EQJ  = DATA/NPATH.EQUITY.as_posix()
BAK  = DATA/"backups"
BAK.mkdir(parents=True, exist_ok=True)
KEEP = int(os.getenv("EQUITY_KEEP_POINTS","5000"))

def main():
    if not EQJ.exists():
        print("no-equity"); return
    try:
        arr = json.loads(EQJ.read_text() or "[]")
        if isinstance(arr, dict):
            arr = arr.get("series", [])
    except Exception as e:
        print("bad-json:", e); return
    n = len(arr)
    if n <= KEEP:
        print(f"no-trim (n={n})"); return
    # backup før trimming
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bak = BAK/f"equity-{stamp}.json"
    EQJ.replace(bak)
    with (str(bak)+".gz") as _:
        pass
    with open(bak, "rb") as fin, gzip.open(str(bak)+".gz","wb", compresslevel=6) as fou:
        shutil.copyfileobj(fin, fou)
    bak.unlink(missing_ok=True)
    # skriv trimmed
    trimmed = arr[-KEEP:]
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA/NPATH.EQUITY.as_posix()).write_text(json.dumps(trimmed, separators=(",",":")))
    print(f"trimmed {n-KEEP} -> keep {KEEP}")
if __name__=="__main__":
    main()
