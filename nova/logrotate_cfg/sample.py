#!/usr/bin/env python3
CFG="""/home/nova/nova-bot/logs/*.log {
  weekly
  rotate 8
  compress
  missingok
  copytruncate
}
"""
def write_sample(path="/home/nova/nova-bot/logrotate.sample"):
    with open(path,"w") as f: f.write(CFG); return path
if __name__=="__main__":
    p=write_sample(); print("wrote", p)
