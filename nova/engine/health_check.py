import os, sys
from dotenv import load_dotenv
import ccxt

def main():
    load_dotenv()
    ex_name = os.getenv("EXCHANGE","binance").lower()
    cls = getattr(ccxt, ex_name)
    ex = cls({"enableRateLimit": True, "options": {"defaultType": "spot"}})
    m = ex.load_markets()
    print(f"OK: {ex_name} markets={len(m)}")

if __name__ == "__main__":
    main()
