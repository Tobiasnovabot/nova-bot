#!/usr/bin/env python3
from nova.logrotate_cfg.sample import write_sample
p=write_sample(); import os; assert os.path.exists(p)
print("logrotate_cfg selftest: OK")
