#!/usr/bin/env python3
import yaml, ccxt, pathlib
cfg = yaml.safe_load(open(pathlib.Path.home()/".config/novax/keys.yml"))
def test(name, entry):
    print(f"\n== {name} ==")
    ex = getattr(ccxt, name)({
        "apiKey": entry.get("apiKey"),
        "secret": entry.get("secret"),
        "password": entry.get("password"),
        "enableRateLimit": True, "timeout": 20000,
    })
    ex.load_markets()
    ex.fetch_ticker("ETH/USDT")              # public
    try:
        ex.fetch_balance()                    # private
        print("  ✅ private OK (fetch_balance)")
    except Exception as e:
        print("  ❌ private FAIL ->", e)
for k in ("binance","okx"):
    if k in cfg: test(k, cfg[k])
print("\nDone.")
