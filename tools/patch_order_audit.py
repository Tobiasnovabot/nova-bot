from nova.io import ndjson
from pathlib import Path, re
p = Path("nova/orders/lifecycle.py")
s = p.read_text()

anchor = "od = ex.create_order"
if anchor in s and "## NOVAX_AUDIT_START" not in s:
    s = s.replace(anchor, anchor + r"""
    ## NOVAX_AUDIT_START
    try:
        import os, json, time, pathlib
        AUD = pathlib.Path(__file__).resolve().parents[2] / "data" / "orders_audit.json"
        MET = pathlib.Path(__file__).resolve().parents[2] / "metrics" / "novax_orders_audit.prom"
        AUD.parent.mkdir(parents=True, exist_ok=True)
        MET.parent.mkdir(parents=True, exist_ok=True)
        now = int(time.time()*1000)

        # safe helpers
        def _g(d,k,default=None):
            try: return d.get(k, default)
            except Exception: return default

        px  = float(_g(od,"price",0) or 0)
        amt = float(_g(od,"amount",0) or 0)
        sym = str(_g(od,"symbol","") or "")
        side= str(_g(od,"side","") or "")
        typ = str(_g(od,"type","") or "")
        notional = px*amt if (px and amt) else float(_g(od,"cost",0) or 0)

        rec = {
            "ts": now,
            "symbol": sym,
            "side": side,
            "type": typ,
            "price": px,
            "amount": amt,
            "notional": notional
        }

        # append compact json line
        with AUD.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, separators=(",",":")) + "\n")

        # minimal prom dump
        with MET.open("w", encoding="utf-8") as f:
            f.write("# HELP novax_last_order_notional_usd Last order notional\n# TYPE novax_last_order_notional_usd gauge\n")
            f.write(f"novax_last_order_notional_usd {notional:.2f} {now}\n")
            f.write("# HELP novax_last_order_info Info labels as 1\n# TYPE novax_last_order_info gauge\n")
            lab = f'symbol="{sym}",side="{side}",type="{typ}"'
            f.write(f"novax_last_order_info{{{lab}}} 1 {now}\n")
    except Exception:
        pass
    ## NOVAX_AUDIT_END
""")
    p.write_text(s)
    print("lifecycle.py: audit injected")
else:
    print("lifecycle.py: already patched or anchor missing")