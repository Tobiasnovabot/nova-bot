import os, pathlib, time, gzip, shutil, csv

DATA = pathlib.Path(os.getenv("NOVA_HOME","data"))
LOG  = DATA/"log"
LOG.mkdir(parents=True, exist_ok=True)

CSV      = LOG/"trades.csv"
TMP      = LOG/"trades.tmp"
MAX_MB   = float(os.getenv("TRADES_CSV_MAX_MB","10"))   # ruller hvis >10MB
KEEP_DAYS= int(os.getenv("TRADES_CSV_KEEP_DAYS","30"))  # slett eldre .gz

def _today_stamp():
    return time.strftime("%Y%m%d")

def _roll_if_needed():
    if not CSV.exists():
        return False, None
    size_mb = CSV.stat().st_size/1024/1024
    mday = time.strftime("%Y%m%d", time.localtime(CSV.stat().st_mtime))
    today = _today_stamp()
    need = (mday != today) or (size_mb > MAX_MB)
    if not need:
        return False, None
    dst = LOG/f"trades-{mday}.csv"
    i=0
    while dst.exists():
        i+=1; dst = LOG/f"trades-{mday}.{i}.csv"
    shutil.move(str(CSV), str(dst))
    # skriv tom CSV med header
    with CSV.open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["ts","sym","side","qty","price","pnl","status","order_id","exchange","strategy"])
    return True, dst

def _gzip(p: pathlib.Path):
    gz = pathlib.Path(str(p)+".gz")
    with p.open("rb") as fin, gzip.open(gz, "wb", compresslevel=6) as fou:
        shutil.copyfileobj(fin, fou)
    p.unlink(missing_ok=True)
    return gz

def _cleanup_old():
    now = time.time()
    for f in LOG.glob("trades-*.csv.gz"):
        age_days = (now - f.stat().st_mtime)/86400
        if age_days > KEEP_DAYS:
            f.unlink(missing_ok=True)

def main():
    rolled, path = _roll_if_needed()
    if rolled and path:
        gz = _gzip(path)
        print("rotated ->", gz.name)
    else:
        print("no-rotate")
    _cleanup_old()

if __name__=="__main__":
    main()
