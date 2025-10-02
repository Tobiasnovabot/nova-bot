import os, json, time, urllib.request
WEBHOOK=os.getenv("ALERT_WEBHOOK","").strip()
def send(event:str, payload:dict):
    if not WEBHOOK: return
    try:
        body={"event":event,"ts":time.time(),"data":payload}
        req=urllib.request.Request(WEBHOOK, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
        urllib.request.urlopen(req, timeout=5).read()
    except Exception:
        pass
