#!/usr/bin/env python3
from nova.backup.snapshot import snapshot
p=snapshot(); import os; assert os.path.exists(p)
print("backup selftest: OK")
