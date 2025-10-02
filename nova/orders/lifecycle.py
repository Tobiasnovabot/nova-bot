from __future__ import annotations
from nova.io import ndjson
import time
from typing import Optional
import os
from tools.liquidity_gate_lib import is_blocked
from tools.sizing_lib import compute_amount, read_size_usd
import math
def place_and_confirm(ex, symbol:str, side:str, type_:str, amount:float,
                      price=None, timeout_s:float=12.0, poll_s:float=0.5, params=None):
    import time, os
    params = params or {}
    # presisjon på amount hvis tilgjengelig
    try:
        amount = float(ex.amount_to_precision(symbol, amount))
    except Exception:
        amount = float(amount)

    # plasser ordre
    od = ex.create_order(symbol, type_, side, amount, price, params)
    if not isinstance(od, dict):
        return {'id': None, 'status': 'no_order'}

    oid = od.get('id')
    if not oid:
        return od if isinstance(od, dict) else {'id': None, 'status': 'no_order'}

    # bekreftelses-loop
    t0 = time.time()
    try:
        _timeout_s = float(os.getenv('ORDER_CONFIRM_TIMEOUT_S', str(timeout_s)) or 12.0)
    except Exception:
        _timeout_s = timeout_s
    try:
        _poll_s = float(os.getenv('ORDER_CONFIRM_POLL_S', str(poll_s)) or 0.5)
    except Exception:
        _poll_s = poll_s

    while True:
        try:
            cur = ex.fetch_order(oid, symbol) or {}
            st = (cur.get('status') or '').lower()
        except Exception:
            st = ''
        if st in ('closed','canceled','expired'):
            return {'id': oid, 'status': st}
        if time.time() - t0 > _timeout_s:
            try:
                ex.cancel_order(oid, symbol)
            except Exception:
                pass
            return {'id': oid, 'status': 'timeout_canceled'}
        time.sleep(_poll_s)
    def _log_prom(action, symbol, extra=""):
        ts = int(time.time()*1000)
        with open(_prom, "a") as fh:
            fh.write(f'novax_order_guard_total{{action="{action}"}} {ts} {ts}\n')
            if extra:
                fh.write(f'novax_order_guard_last_action{{action="{action}"}} 1 {ts}\n')
        with open(_log, "a") as fh:
            fh.write(f'{time.strftime("%Y-%m-%dT%H:%M:%S%z")} action={action} symbol={symbol} {extra}\n')

    # 1) liquidity gate file
    try:
        if _gate.exists():
            g = json.loads(_gate.read_text() or "{}")
            if symbol in set(g.get("blocked", []) or []):
                _log_prom("liquidity_block", symbol, "reason=blocked_list")
                return None
    except Exception:
        pass

    # 2) spread guard – try metrics first, else live via ccxt
    max_bp = float(os.getenv("MAX_ENTRY_SPREAD_BP", os.getenv("MAX_SLIPPAGE_BPS","20")) or 20.0)
    spread_bp = None
    try:
        mp = (_root/"metrics"/"novax_pos_spread.prom")
        if mp.exists():
            pat = re.compile(rf'novax_pos_spread_bps{{symbol="{re.escape(symbol)}"}}\s+([\d\.]+)')
            for line in mp.read_text().splitlines()[::-1]:
                m = pat.search(line)
                if m:
                    spread_bp = float(m.group(1))
                    break
    except Exception:
        spread_bp = None

    if spread_bp is None:
        try:
            import ccxt
            ex_name = os.getenv("TRADING_EXCHANGE", os.getenv("EXCHANGE","binance")).lower()
            ex = getattr(ccxt, ex_name)()
            ob = ex.fetch_order_book(symbol)
            bid = ob['bids'][0][0] if ob.get('bids') else None
            ask = ob['asks'][0][0] if ob.get('asks') else None
            if bid and ask and ask>0:
                spread_bp = ( (ask - bid) / ((ask+bid)/2.0) ) * 10000.0
        except Exception:
            spread_bp = None

    if spread_bp is not None and spread_bp > max_bp:
        _log_prom("spread_block", symbol, f"spread_bp={spread_bp:.4f} max_bp={max_bp:.2f}")
        return None
    
    od = ex.create_order
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


    # === CONFIRM_LOOP_BEGIN ===
    _od_local = locals().get('od') if 'od' in locals() else None
    if isinstance(_od_local, dict) and _od_local.get('id'):
        oid = _od_local['id']
        _timeout_s = float(os.getenv('ORDER_CONFIRM_TIMEOUT_S', str(timeout_s)) or 12.0)
        _poll_s = float(os.getenv('ORDER_CONFIRM_POLL_S', str(poll_s)) or 0.5)
        t0 = time.time()
        while True:
            try:
                _od = ex.fetch_order(oid, symbol) or {}
                st = (_od.get('status') or '').lower()
            except Exception:
                st = ''
            if st in ('closed','canceled','expired'):
                return {'id': oid, 'status': st}
            if time.time() - t0 > _timeout_s:
                try:
                    ex.cancel_order(oid, symbol)
                except Exception:
                    pass
                return {'id': oid, 'status': 'timeout_canceled'}
            time.sleep(_poll_s)
    return _od_local if isinstance(_od_local, dict) else {'id': None, 'status': 'no_order'}
    # === CONFIRM_LOOP_END ===
    # === CONFIRM_LOOP_BEGIN ===
    def _extract_order(_l):
        # foretrekk 'od', ellers siste dict med 'id' + 'status'
        cand = []
        for k,v in list(_l.items()):
            if isinstance(v, dict) and 'id' in v:
                cand.append((k,v))
        # prioriter 'od'
        for k,v in cand:
            if k == 'od':
                return v
        return cand[-1][1] if cand else None

    _od_local = _extract_order(locals())
    if isinstance(_od_local, dict) and _od_local.get('id'):
        oid = _od_local.get('id')
        _timeout_s = float(os.getenv("ORDER_CONFIRM_TIMEOUT_S", str(timeout_s if 'timeout_s' in locals() else 12.0)) or 12.0)
        _poll_s = float(os.getenv("ORDER_CONFIRM_POLL_S", str(poll_s if 'poll_s' in locals() else 0.5)) or 0.5)
        t0 = time.time()
        while True:
            try:
                _od = ex.fetch_order(oid, symbol) or {}
                st = ( _od.get("status") or "" ).lower()
            except Exception:
                st = ""
            if st in ("closed","canceled","expired"):
                return {"id": oid, "status": st}
            if time.time() - t0 > _timeout_s:
                try: ex.cancel_order(oid, symbol)
                except Exception: pass
                return {"id": oid, "status": "timeout_canceled"}
            time.sleep(_poll_s)
    # STRAY_ELSE_REMOVED
        # Ingen identifiserbar ordre-objekt. Returner best mulig svar.
        return {"id": None, "status": "no_order"}
        # STRAY_ELSE_REMOVED
        return od if isinstance(od, dict) else {'id': None, 'status': 'no_order'}
# === CONFIRM_LOOP_END ===