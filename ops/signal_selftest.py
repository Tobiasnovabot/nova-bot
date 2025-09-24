from nova.exchange import build_exchange
import os, json, time, math, statistics, pathlib
from datetime import datetime, timezone, timezone
try:
    import ccxt
except Exception as e:
    print("FAIL: ccxt ikke tilgjengelig i venv:", e); raise SystemExit(2)

DATA = pathlib.Path("data")
STATE = DATA / "state.json"
ok=True
def p(msg): print(msg, flush=True)

# 1) Les univers (watch eller universe_cache)
watch=[]
try:
    s=json.loads(STATE.read_text() or "{}")
    watch = s.get("watch") or s.get("universe_cache",{}).get("symbols",[]) or []
except Exception as e:
    p(f"WARN: kunne ikke lese state.json: {e}")
if not watch:
    watch = ["BTC/USDT","ETH/USDT","BNB/USDT","SOL/USDT","XRP/USDT"]

p(f"[selftest] symbols={len(watch)} (viser inntil 10)")

# 2) Hent OHLCV for 5m de siste ~100 stegene for inntil 10 symbols
ex = build_exchange()
def sma(a,n): 
    if len(a) < n: return None
    return sum(a[-n:])/n
def rsi(closes, n=14):
    if len(closes) < n+1: return None
    gains=[]; losses=[]
    for i in range(-n,0):
        ch = closes[i]-closes[i-1]
        gains.append(max(ch,0)); losses.append(max(-ch,0))
    avg_gain=sum(gains)/n; avg_loss=sum(losses)/n
    if avg_loss==0: return 100.0
    rs=avg_gain/avg_loss
    return 100 - (100/(1+rs))

tested=0; hits=0
report=[]
for sym in watch[:10]:
    try:
        ohlcv = ex.fetch_ohlcv(sym, timeframe='5m', limit=120)
        closes=[c[4] for c in ohlcv]
        s5 = sma(closes,5); s20=sma(closes,20); r = rsi(closes,14)
        sig="hold"
        if s5 and s20 and r:
            if s5 > s20 and r>55: sig="bull"
            elif s5 < s20 and r<45: sig="bear"
            hits+=1
        report.append((sym, closes[-1] if closes else None, round(s5,4) if s5 else None, round(s20,4) if s20 else None, round(r,2) if r else None, sig))
        tested+=1
    except Exception as e:
        report.append((sym, None, None, None, None, f"ERR:{str(e)[:28]}"))

# 3) Resultat
ts = datetime.now(timezone.utc).isoformat()+"Z"
p(f"[selftest] ts={ts} tested={tested} indicators_ok={hits}")
for row in report:
    sym, px, s5, s20, r, sig = row
    p(f"{sym:12} px={px} sma5={s5} sma20={s20} rsi={r} -> {sig}")

# 4) Skriv en liten selftest-artefakt
DATA.mkdir(parents=True, exist_ok=True)
(pathlib.Path("data")/"signal_selftest.json").write_text(json.dumps({
    "ts": ts, "tested": tested, "ok_indicators": hits, "rows": report
}, separators=(",",":")))
p("PASS: signal_selftest.json skrevet.")