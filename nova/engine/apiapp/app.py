from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pathlib import Path
from ..strategy_toggle import load_overrides, set_enabled, is_enabled
from ..backtest import run_backtest
import json

app = FastAPI(title="Nova Ultra API")

def read_json(path, default=None):
    p = Path(path)
    if not p.exists(): return default
    try: return json.loads(p.read_text())
    except Exception: return default

@app.get("/status")
def status():
    data = {
        "runtime/ultra_metrics_port": Path("runtime/ultra_metrics_port").read_text().strip() if Path("runtime/ultra_metrics_port").exists() else None,
        "runtime/universe_size": read_json("runtime/status.json",{}).get("universe_size"),
        "runtime/equity.json": read_json("runtime/equity.json"),
    }
    return JSONResponse({"ok": True, "data": data})

@app.get("/pairs")
def pairs():
    s = read_json("runtime/status.json", {})
    return JSONResponse({"ok": True, "data": s})

@app.get("/strategies")
def strategies():
    # metrics eksponeres i Prometheus; her viser vi bare at endpoint finnes
    return JSONResponse({"ok": True, "data": {"source": "prometheus metrics"}})

@app.get("/positions")
def positions():
    pos = read_json("runtime/positions.json", {"positions":{}, "realized_pnl":0.0})
    return JSONResponse({"ok": True, "data": pos})


def _read_strategies():
    try:
        mods = []
        f=Path('runtime/strategies.json')
        if f.exists(): mods = list((__import__('json').loads(f.read_text()) or {}).get('loaded',[]))
        return mods
    except Exception:
        return []

@app.get('/strategies')
def strategies():
    mods=_read_strategies()
    return JSONResponse({'ok':True,'data':[{'name':m,'enabled':is_enabled(m)} for m in mods]})

@app.post('/strategy/{name}/{action}')
def strategy_toggle(name:str, action:str):
    if action not in ('enable','disable'):
        return JSONResponse({'ok':False,'error':'action must be enable|disable'}, status_code=400)
    set_enabled(name, action=='enable')
    return JSONResponse({'ok':True,'name':name,'enabled': action=='enable'})


@app.post('/backtest/run')
def backtest_run(symbol:str="BTC/USDT", exchange:str="binance", timeframe:str="1h", days:int=30, strategy:str="momentum"):
    try:
        res = run_backtest(symbol=symbol, exchange=exchange, timeframe=timeframe, days=days, strategy=strategy,
                           equity0=1000.0, risk_frac=0.003)
        return JSONResponse({'ok':True,'data':res})
    except Exception as e:
        return JSONResponse({'ok':False,'error':str(e)}, status_code=500)

@app.get('/backtest/last')
def backtest_last():
    d = Path('runtime/backtests')
    items = []
    if d.exists():
        for p in sorted(d.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
            items.append({'file':str(p), 'summary': __import__('json').loads(p.read_text())})
    return JSONResponse({'ok':True,'data':items})

@app.post('/control/kill')
def kill():
    from pathlib import Path, json
    f = Path("runtime/control.json")
    d = json.loads(f.read_text()) if f.exists() else {}
    d["kill"] = True
    f.write_text(json.dumps(d))
    return {"ok": True, "kill": True}

@app.post('/control/mode/{mode}')
def set_mode(mode: str):
    from pathlib import Path, json
    f = Path("runtime/control.json")
    d = json.loads(f.read_text()) if f.exists() else {}
    d["mode"] = mode
    f.write_text(json.dumps(d))
    return {"ok": True, "mode": mode}
