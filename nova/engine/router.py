import os, importlib, hashlib

def parse_strat_set(default="momentum,meanrev"):
    raw = os.getenv('STRAT_SET', default)
    raw = raw.split('#',1)[0]
    return [x.strip() for x in raw.split(',') if x.strip()]

def load_modules(names):
    print('[router] loading modules...', flush=True)
    out={}
    for n in names:
        tried = [
            f"nova.engine.strategies.{n}",
            f"nova.engine.strategy_{n}",
        ]
        for path in tried:
            try:
                mod = importlib.import_module(path)
                out[n]=mod
                break
            except Exception:
                continue
        if n not in out:
            print(f"[router] failed to load {n}", flush=True)
    return out

def _hash_pair_to_index(pair:str, m:int)->int:
    h=hashlib.sha256(pair.encode()).digest()
    return int.from_bytes(h[:4],'big') % max(m,1)

def pick_strategies(mode:str, names:list, pair:str):
    mode = (mode or "hash").lower()
    if not names: return []
    if mode == "all":
        return names
    if mode == "alternate":
        i = _hash_pair_to_index(pair, len(names))
        return [names[i]]
    # default: hash (samme som alternate her)
    i = _hash_pair_to_index(pair, len(names))
    return [names[i]]

def _save_loaded(names):
    Path('runtime').mkdir(exist_ok=True, parents=True)
    Path('runtime/strategies.json').write_text(json.dumps({'loaded':sorted(names),'ts':time.time()}, indent=2))

# ROUTER_PATCH_LOG
