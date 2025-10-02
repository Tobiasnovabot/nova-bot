#!/usr/bin/env python3
import yaml, ccxt, pathlib
cfg = yaml.safe_load(open(str(pathlib.Path.home() / ".config/novax/keys.yml")))
def test(name, entry):
    print(f"\n== {name} ==")
    kw = dict(apiKey=entry.get("apiKey"), secret=entry.get("secret"))
    if entry.get("password"): kw["password"] = entry["password"]
    ex = getattr(ccxt, name)({**kw, "enableRateLimit": True, "timeout": 20000})
    ex.load_markets()
    ex.fetch_ticker("ETH/USDT")
    try:
        bal = ex.fetch_balance()
        print("  ✅ private OK (fetch_balance).")
    except Exception as e:
        print("  ⚠️  public OK, private FAIL ->", e)
for k in ("binance","okx"):
    if k in cfg: test(k, cfg[k])
print("\nDone.")
