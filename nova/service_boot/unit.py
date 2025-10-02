#!/usr/bin/env python3
TEMPLATE="""[Unit]
Description=Nova trading engine
After=network-online.target
[Service]
User=nova
WorkingDirectory=/home/nova/nova-bot
Environment=ENGINE_ONCE=0 ENGINE_LOOP_SEC=30 EXCHANGE=binance MODE=paper
ExecStart=/home/nova/nova-bot/.venv/bin/python -m nova.engine.run
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
"""
def write_sample(path="nova/service_boot/nova.service.sample"):
    import os
    os.makedirs("nova/service_boot", exist_ok=True)
    with open(path,"w") as f: f.write(TEMPLATE)
    return path
if __name__=="__main__":
    p=write_sample(); print("wrote", p)
