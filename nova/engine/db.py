import sqlite3, pathlib, time, json

def connect():
    pathlib.Path('runtime').mkdir(exist_ok=True, parents=True)
    conn=sqlite3.connect('runtime/nova.db'); conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""CREATE TABLE IF NOT EXISTS trades(
        ts REAL, symbol TEXT, side TEXT, qty REAL, price REAL, meta TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS decisions(
        ts REAL, symbol TEXT, strat TEXT, side TEXT, px REAL, meta TEXT)""")
    return conn

def log_trade(conn, ts, symbol, side, qty, price, meta:dict=None):
    conn.execute("INSERT INTO trades VALUES (?,?,?,?,?,?)",
        (ts, symbol, side, qty, price, json.dumps(meta or {}))); conn.commit()

def log_decision(conn, ts, symbol, strat, side, px, meta:dict=None):
    conn.execute("INSERT INTO decisions VALUES (?,?,?,?,?,?)",
        (ts, symbol, strat, side, px, json.dumps(meta or {}))); conn.commit()
