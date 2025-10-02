import os, json
from fastapi import FastAPI

app=FastAPI()

@app.get("/status")
def status():
    d={}
    for fn in ("runtime/ultra_metrics_port","runtime/universe_size","runtime/equity.json"):
        try:
            if fn.endswith(".json"): d[fn]=json.load(open(fn))
            else: d[fn]=open(fn).read().strip()
        except Exception: d[fn]=None
    return {"ok":True, "data":d}

@app.get("/")
def root(): return {"ok":True}
