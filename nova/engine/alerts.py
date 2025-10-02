import os, json, urllib.request

def send(text:str):
    url=os.getenv('ALERT_WEBHOOK','').strip()
    if not url: return
    try:
        data=json.dumps({"text":text}).encode()
        req=urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
        urllib.request.urlopen(req, timeout=5).read()
    except Exception: pass
