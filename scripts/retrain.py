#!/usr/bin/env python3
import json, os, glob, math, time
from collections import defaultdict

BASE="/home/nova/nova-bot"
ARCH=os.path.join(BASE,"archives")
DATA=os.path.join(BASE,"data")
OUTP=os.path.join(BASE,"models","strategy_weights.json")

def load_jsons(patterns):
    out=[]
    for pat in patterns:
        for fn in sorted(glob.glob(pat)):
            try:
                with open(fn,"r") as f: out.append(json.load(f))
            except Exception: pass
    return out

def mean(xs):
    xs=[x for x in xs if isinstance(x,(int,float))]
    return sum(xs)/len(xs) if xs else 0.0

def std(xs):
    xs=[x for x in xs if isinstance(x,(int,float))]
    if len(xs)<2: return 0.0
    m=mean(xs)
    return (sum((x-m)**2 for x in xs)/(len(xs)-1))**0.5

def main():
    trades = load_jsons([os.path.join(DATA,"trades.json"),
                         os.path.join(ARCH,"trades_*.json")])
    PNL=defaultdict(list); N=defaultdict(int); W=defaultdict(int)
    for blob in trades:
        rows = blob.get("trades", blob if isinstance(blob,list) else [])
        for t in rows:
            s=str(t.get("strategy","unknown")); p=float(t.get("pnl",0.0))
            PNL[s].append(p); N[s]+=1; W[s]+= 1 if p>0 else 0
    scores={}
    eps=1e-9
    for s,pnls in PNL.items():
        n=N[s]
        mu=mean(pnls); sd=std(pnls); wr=(W[s]/n) if n>0 else 0
        sharpe_like=(mu/(sd+eps))*(n**0.5)
        scores[s]=0.9*sharpe_like+0.1*(wr*10.0)
    if not scores: scores={"unknown":1.0}
    mn=min(scores.values()); shifted={k:(v-mn+1.0) for k,v in scores.items()}
    tot=sum(shifted.values()) or 1.0
    raw={k: shifted[k]/tot for k in shifted}
    floor,ceil=0.02,0.5
    clipped={k:max(floor,min(ceil,w)) for k,w in raw.items()}
    s=sum(clipped.values()) or 1.0
    weights={k:v/s for k,v in clipped.items()}
    os.makedirs(os.path.dirname(OUTP),exist_ok=True)
    with open(OUTP,"w") as f:
        json.dump({"generated_at":time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "weights":weights,"counts":dict(N)},f,indent=2)
    print("Wrote",OUTP,weights)

if __name__=="__main__": main()
