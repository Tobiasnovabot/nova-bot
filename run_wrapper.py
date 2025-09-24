import os
import time, subprocess, sys, os

BASE = os.getenv("NOVA_HOME","/home/nova/nova-bot")
CMD  = [os.path.join(BASE, ".venv/bin/python"), os.path.join(BASE, "bot_main.py"), "run"]

while True:
    rc = subprocess.call(CMD)
    print(f"[wrapper] bot_main exited rc={rc}", flush=True)
    time.sleep(2)