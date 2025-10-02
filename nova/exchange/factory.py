from __future__ import annotations
import os, ccxt

def _env(name:str, default:str=""):
    v=os.getenv(name, default)
    return v if v is not None else default

def _keys_for(exchange:str):
    x=exchange.lower()
    if x=="binance":
        return {
            "apiKey": _env("BINANCE_API_KEY"),
            "secret": _env("BINANCE_API_SECRET"),
        }
    if x=="okx":
        return {
            "apiKey": _env("OKX_API_KEY"),
            "secret": _env("OKX_API_SECRET"),
            "password": _env("OKX_API_PASSWORD"),
        }
    raise ValueError(f"unsupported exchange: {exchange}")

def build_exchange(exchange:str|None=None, mode:str|None=None):
    """Returnerer ccxt-klient konfigurert fra .env. Bruk samme for paper/live."""
    x=(exchange or os.getenv("EXCHANGE","binance")).lower()
    m=(mode or os.getenv("TRADING_MODE","paper")).lower()
    klass = getattr(ccxt, x)

    # Basis config
    cfg = {
        "enableRateLimit": True,
        "timeout": 15000,
        "options": {}
    }
    # Nøkler
    cfg.update(_keys_for(x))

    # Spesifikke toggles
    if x=="binance":
        # Spot. Bruk testnet hvis ønsket. Prod-testnet krever egne nøkler.
        use_test = (m=="paper") and bool(int(os.getenv("BINANCE_TESTNET", "0")))
        if use_test:
            cfg["options"]["defaultType"] = "spot"
            klass = getattr(ccxt, "binance")  # ccxt håndterer testnet via .urls
        ex = klass(cfg)
        if use_test:
            ex.set_sandbox_mode(True)
        return ex

    if x=="okx":
        ex = klass(cfg)
        # OKX har ikke eget testnet via ccxt; bruk små størrelser i paper.
        return ex

    return klass(cfg)
