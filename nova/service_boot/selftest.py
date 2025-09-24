#!/usr/bin/env python3
from nova.service_boot.unit import write_sample
p=write_sample(); 
import os; assert os.path.exists(p)
print("service_boot selftest: OK")
