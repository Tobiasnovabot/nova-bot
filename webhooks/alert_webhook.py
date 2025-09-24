from fastapi import FastAPI, Request
import asyncio, json, subprocess, time

app = FastAPI()

# map AM label job -> systemd unit
JOB_TO_UNIT = {
    "novax-okx-feed": "novax-okx-feed-exporter",
    "novax-file-age": "novax-file-age-exporter",
    "novax-equity": "novax-equity-exporter",
}

COOLDOWN_S = 90
_last = {}  # job -> ts

def unit_state(unit:str)->dict:
    out = subprocess.run(
        ["/usr/bin/systemctl","show",unit,"-p","ActiveState","-p","SubState","-p","UnitFileState"],
        capture_output=True, text=True
    ).stdout
    kv = dict(line.split("=",1) for line in out.strip().splitlines() if "=" in line)
    return kv

async def restart_unit(unit:str):
    st = unit_state(unit)
    if st.get("SubState") == "stop-sigterm" or st.get("ActiveState") == "deactivating":
        return  # unngå race mot pågående stop-jobb
    subprocess.run(["/usr/bin/sudo","/usr/bin/systemctl","restart",unit], check=False)

@app.post("/am")
async def am_webhook(req: Request):
    data = await req.json()
    alerts = data.get("alerts") or []
    now = time.time()
    todo = set()
    for a in alerts:
        if a.get("status")!="firing": continue
        if a.get("labels",{}).get("alertname") not in {"NOVAX_Engine_Down","NOVAX_OKX_Feed_Down"}: continue
        job = a.get("labels",{}).get("job")
        unit = JOB_TO_UNIT.get(job)
        if not unit:  # fall-back: restart begge eksportere en og en
            for u in JOB_TO_UNIT.values(): todo.add(u)
            continue
        todo.add(unit)
    for unit in todo:
        if now - _last.get(unit, 0) < COOLDOWN_S:  # debounce
            continue
        _last[unit] = now
        asyncio.create_task(restart_unit(unit))
    return {"ok": True, "scheduled": list(todo)}


from fastapi import FastAPI
try:
    app
except NameError:
    app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}
