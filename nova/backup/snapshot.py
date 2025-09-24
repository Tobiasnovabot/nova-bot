#!/usr/bin/env python3
import os, tarfile, time
def snapshot(dst_dir="backups"):
    os.makedirs(dst_dir, exist_ok=True)
    ts=time.strftime("%Y%m%d_%H%M%S")
    out=os.path.join(dst_dir, f"nova-bot_{ts}.tar.gz")
    with tarfile.open(out,"w:gz") as tar:
        for p in ("nova",".env","requirements.txt"):
            if os.path.exists(p): tar.add(p)
    return out
if __name__=="__main__":
    p=snapshot(); print("snapshot:", p)
