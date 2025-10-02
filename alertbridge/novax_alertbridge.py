#!/usr/bin/env python3
import os, json, html, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
import urllib.request

TG_KEY  = os.getenv("TG_KEY","")
TG_CHAT = os.getenv("TG_CHAT","")
PORT    = int(os.getenv("NOVAX_ALERT_PORT","9124"))

def send_tg(text):
    if not TG_KEY or not TG_CHAT:
        return False, "TG_KEY/TG_CHAT missing"
    data = urllib.parse.urlencode({
        "chat_id": TG_CHAT,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=10) as r:
            return True, r.read()
    except Exception as e:
        return False, str(e)

def fmt_alert(a):
    lab = a.get("labels",{})
    ann = a.get("annotations",{})
    name = lab.get("alertname","(alert)")
    sev  = lab.get("severity","info")
    desc = ann.get("description", ann.get("summary",""))
    inst = lab.get("instance", lab.get("job",""))
    status = a.get("status","firing")
    # Escape
    def esc(s): return html.escape(str(s or ""))
    lines = [
        f"🚨 <b>{esc(name)}</b>  <i>{esc(status)}</i>",
        f"sev: <b>{esc(sev)}</b>   src: <code>{esc(inst)}</code>",
    ]
    if desc: lines.append(esc(desc))
    return "\n".join(lines)

class H(BaseHTTPRequestHandler):
    def log_message(self, *args, **kwargs): pass

    def do_POST(self):
        if self.path not in ("/alert","/"):
            self.send_response(404); self.end_headers(); return
        length = int(self.headers.get("Content-Length","0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode() or "{}")
        except Exception:
            payload = {"raw": raw.decode(errors="replace")}
        alerts = payload.get("alerts") or []
        if not alerts:
            ok, msg = send_tg("ℹ️ Alert webhook ping")
        else:
            ok=True; msg=""
            for a in alerts:
                t = fmt_alert(a)
                ok_i, msg_i = send_tg(t)
                ok = ok and ok_i
        self.send_response(200 if ok else 500)
        self.end_headers()
        self.wfile.write(b"ok" if ok else b"fail")

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok"); return
        self.send_response(404); self.end_headers()

if __name__ == "__main__":
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
