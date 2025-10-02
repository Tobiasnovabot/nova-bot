#!/usr/bin/env python3
import os, sys
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

os.environ.setdefault("TRADING_MODE", os.getenv("TRADING_MODE","paper"))
os.environ["TELEGRAM_DISABLED"] = "1"

from nova.paths import ensure_dirs
ensure_dirs()

from nova.engine.run import main as engine_main
if __name__ == "__main__":
    sys.exit(engine_main())
