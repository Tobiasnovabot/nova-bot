import json, pathlib

OUT = pathlib.Path("p/stairs_sanity.out")
OUT.parent.mkdir(parents=True, exist_ok=True)

cfg = {
    "start_cash": 10000.0,
    "base_size":  100.0,
    "max_lots":   6,
    "take_step":  0.012,
    "buy_step":   0.010,
    "reentry_gap":0.018,
}

p0 = 100.0
series = []
for i in range(10): series.append(p0*(1 + 0.0005*i))
x = series[-1]
for i in range(1,9):   x *= (1 - cfg["buy_step"]);  series.append(x)
for i in range(1,10):  x *= (1 + cfg["take_step"]); series.append(x)
for i in range(1,8):   x *= (1 - cfg["reentry_gap"]/3); series.append(x)
for i in range(1,8):   x *= (1 + cfg["take_step"]); series.append(x)

cash = cfg["start_cash"]; pos = 0.0; avg = None; peak_exit_px = None
buys=sells=ladder_in=ladder_out=reentries=0
last_px = series[0]

def buy(px, usd):
    global cash,pos,avg,ladder_in,buys
    size = usd/max(px,1e-9)
    new_pos = pos + size
    new_avg = (pos*avg + size*px)/new_pos if pos>0 and avg is not None else px
    cash -= usd
    pos,avg = new_pos,new_avg
    ladder_in += 1; buys += 1

def sell(px, size_units):
    global cash,pos,avg,ladder_out,sells,peak_exit_px
    size_units = min(size_units, pos)
    cash += size_units*px
    pos  -= size_units
    if pos <= 1e-9:
        pos = 0.0
        peak_exit_px = px
        avg = None
    ladder_out += 1; sells += 1

for px in series:
    drop = (last_px - px)/last_px if last_px else 0.0
    if pos < cfg["max_lots"] and drop >= cfg["buy_step"]*0.999:
        buy(px, cfg["base_size"]); last_px = px
    if pos > 0 and avg is not None:
        up = (px - avg)/avg if avg else 0.0
        if up >= cfg["take_step"]*0.999:
            sell(px, cfg["base_size"]/max(px,1e-9))
            if pos>0: avg = avg*(1 + cfg["take_step"]/2)
    if pos == 0 and peak_exit_px:
        dd = (peak_exit_px - px)/peak_exit_px
        if dd >= cfg["reentry_gap"]*0.999:
            buy(px, cfg["base_size"]*2)
            reentries += 1
            peak_exit_px = None
            last_px = px

equity = cash + pos*series[-1]

ok = True; reasons = []
if ladder_in < 2:  ok=False; reasons.append("for få ladder buys")
if ladder_out < 1: ok=False; reasons.append("ingen ladder sells")
if reentries < 1:  ok=False; reasons.append("ingen re-entry")
if cash < -1e-6:   ok=False; reasons.append("negativ cash")
if pos  < -1e-9:   ok=False; reasons.append("negativ pos")

report = {
    "buys": buys, "sells": sells,
    "ladder_in": ladder_in, "ladder_out": ladder_out,
    "reentries": reentries,
    "end_equity": round(equity,2),
    "end_pos": round(pos,6),
    "ok": ok, "reasons": reasons,
}
OUT.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
