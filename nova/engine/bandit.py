import json, random
from pathlib import Path
STORE = Path("data/bandit.json")
ARMS = []

def init(arms):
    global ARMS
    ARMS = list(arms)
    STORE.parent.mkdir(exist_ok=True)
    st = _load()
    for a in ARMS:
        st.setdefault(a, {"alpha":1.0, "beta":1.0})
    _save(st)

def _load():
    try:
        return json.loads(STORE.read_text())
    except Exception:
        return {}

def _save(st):
    STORE.write_text(json.dumps(st, indent=2))

def get_weights(arms, key=None):
    st=_load()
    w={}
    for a in arms:
        d=st.get(a, {"alpha":1.0,"beta":1.0})
        # Thompson sampling: trekk fra Beta(alpha,beta), bruk som vekt
        sa=random.betavariate(max(1e-6,d["alpha"]), max(1e-6,d["beta"]))
        w[a]=sa
    return w

def update_from_trade(symbol, used_strats, pnl):
    st=_load()
    win = 1 if pnl>0 else 0
    for a in (used_strats or []):
        d=st.setdefault(a, {"alpha":1.0,"beta":1.0})
        if win: d["alpha"] += 1.0
        else:   d["beta"]  += 1.0
    _save(st)

def snapshot():
    st=_load()
    # Returner {arm: (alpha,beta)} for exporter
    return {a: (st.get(a,{"alpha":1.0,"beta":1.0})["alpha"],
                st.get(a,{"alpha":1.0,"beta":1.0})["beta"]) for a in (ARMS or st.keys())}

def weight(name, sig, basew):
    # Hvis en strategi returnerer ("buy"/"sell"/"hold", meta), gi +1/-1/0 som signal
    # Her antar vi at caller allerede oversetter til votes, så bare returnér basew
    return basew


def update_from_partial(symbol, used_strats, pnl, w=0.25):
    st=_load()
    win = 1 if pnl>0 else 0
    for a in (used_strats or []):
        d=st.setdefault(a, {"alpha":1.0,"beta":1.0})
        if win: d["alpha"] += float(w)
        else:   d["beta"]  += float(w)
    _save(st)
