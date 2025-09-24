#!/usr/bin/env bash
set -euo pipefail
ROOT="$HOME/nova-bot"
cd "$ROOT"

echo "[1/8] Lage mappe-struktur"
mkdir -p nova/telegram

echo "[2/8] Krav (python-telegram-bot v13)"
. .venv/bin/activate
pip install --quiet "python-telegram-bot==13.15"

echo "[3/8] __init__.py"
cat > nova/telegram/__init__.py <<'PY'
# telegram controller package
PY

echo "[4/8] tg_utils.py"
cat > nova/telegram/tg_utils.py <<'PY'
import os, json, pathlib, subprocess, logging
log = logging.getLogger("nova.telegram.utils")

ENV_PATH = pathlib.Path(".env")
NOVA_HOME = pathlib.Path(os.getenv("NOVA_HOME", "data"))
STATE_PATH = NOVA_HOME / "state.json"

def load_env():
    env = {}
    if ENV_PATH.exists():
        for ln in ENV_PATH.read_text().splitlines():
            if not ln.strip() or ln.strip().startswith("#") or "=" not in ln: continue
            k, v = ln.split("=", 1)
            env[k.strip()] = v.strip()
    return env

def load_state():
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        s = json.loads(STATE_PATH.read_text() or "{}")
    except Exception:
        s = {}
    s.setdefault("mode","paper")
    s.setdefault("bot_enabled", True)
    s.setdefault("risk_level", 5)
    s.setdefault("equity_usd", 10000.0)
    s.setdefault("positions", {})
    uc = s.setdefault("universe_cache", {})
    uc.setdefault("symbols", [])
    return s

def save_state(s):
    STATE_PATH.write_text(json.dumps(s, separators=(",",":")))

def sysd(cmd: str) -> str:
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
        return out.strip()
    except subprocess.CalledProcessError as e:
        return f"ERR: {e.output.strip()}"

def guard_chat(update, env):
    allowed_id = env.get("TELEGRAM_CHAT_ID") or env.get("TG_CHAT")
    if not allowed_id:
        return True
    try:
        return str(update.effective_chat.id) == str(allowed_id)
    except Exception:
        return False
PY

echo "[5/8] tg_commands.py"
cat > nova/telegram/tg_commands.py <<'PY'
import os, logging, textwrap
from .tg_utils import load_state, save_state, sysd
log = logging.getLogger("nova.telegram.commands")

HELP = textwrap.dedent("""
Kommandoliste:
/help – denne hjelpen
/status – systemstatus
/pnl – PnL-oversikt (enkel)
/pos – åpne posisjoner
/risk show|set <1-30> – vis/sett risk-level
/equity show|set <USD> – vis/sett tilgjengelig equity
/on – slå PÅ trading (bot_enabled=True)
/off – slå AV trading (bot_enabled=False)
/mode paper|live|shadow – bytt modus (lagres i state.json)
/start_live – sett live + PÅ + restart engine
/start_paper – sett paper + PÅ + restart engine
/engine start|stop|restart – styr systemd for engine
/watch list|add SYM|rm SYM|clear – styr watch-list
/heartbeat_on <min> – slå på HB melding hver N min (dummy flagg)
/heartbeat_off – slå av HB
""").strip()

def reply(update, text): update.message.reply_text(text)

def cmd_help(update, context):
    reply(update, HELP)

def cmd_status(update, context):
    s = load_state()
    txt = (
        f"mode={s.get('mode')}  bot_enabled={s.get('bot_enabled')}\n"
        f"risk_level={s.get('risk_level')}  equity_usd={s.get('equity_usd'):.2f}\n"
        f"positions={len(s.get('positions',{}))}  universe={len(s.get('universe_cache',{}).get('symbols',[]))}"
    )
    reply(update, txt)

def cmd_pnl(update, context):
    s = load_state()
    reply(update, f"pnl_day={s.get('pnl_day',0.0):.2f}  equity_usd={s.get('equity_usd',0.0):.2f}")

def cmd_pos(update, context):
    s = load_state(); pos = s.get("positions",{})
    if not pos:
        reply(update, "Ingen åpne posisjoner.")
        return
    lines = []
    for sym,p in pos.items():
        lines.append(f"{sym} qty={p.get('qty',0)} avg={p.get('avg',0)} t0={p.get('ts',0)}")
    reply(update, "\n".join(lines))

def cmd_on(update, context):
    s = load_state(); s["bot_enabled"]=True; save_state(s)
    reply(update, "✅ Bot PÅ (bot_enabled=True)")

def cmd_off(update, context):
    s = load_state(); s["bot_enabled"]=False; save_state(s)
    reply(update, "⛔ Bot AV (bot_enabled=False)")

def cmd_mode(update, context):
    if not context.args:
        reply(update, "Bruk: /mode paper|live|shadow"); return
    v = context.args[0].lower()
    if v not in {"paper","live","shadow"}:
        reply(update, "Ugyldig. Bruk: paper|live|shadow"); return
    s = load_state(); s["mode"]=v; save_state(s)
    reply(update, f"🔁 Mode satt: {v}")

def _start_mode(update, mode):
    s = load_state(); s["mode"]=mode; s["bot_enabled"]=True; save_state(s)
    out = sysd("sudo systemctl restart novax.service || true")
    reply(update, f"{'🚀' if mode=='live' else '📑'} {mode} aktivert + restart engine\n{out}")

def cmd_start_live(update, context): _start_mode(update, "live")
def cmd_start_paper(update, context): _start_mode(update, "paper")

def cmd_engine(update, context):
    if not context.args:
        reply(update,"Bruk: /engine start|stop|restart"); return
    action = context.args[0].lower()
    if action not in {"start","stop","restart"}:
        reply(update,"Bruk: /engine start|stop|restart"); return
    out = sysd(f"sudo systemctl {action} novax.service || true")
    reply(update, f"engine {action}: {out}")

def cmd_risk(update, context):
    s = load_state()
    if not context.args or context.args[0] == "show":
        reply(update, f"risk_level={s.get('risk_level')}")
        return
    if context.args[0] == "set":
        if len(context.args)<2: reply(update,"Bruk: /risk set <1-30>"); return
        try: lvl = int(context.args[1])
        except Exception as e:
reply(update,"Må være heltall 1-30"); return
        lvl = max(1, min(30, lvl))
        s["risk_level"]=lvl; save_state(s)
        reply(update, f"✅ risk_level={lvl}")
        return
    reply(update,"Bruk: /risk show|set <1-30>")

def cmd_equity(update, context):
    s = load_state()
    if not context.args or context.args[0]=="show":
        reply(update, f"equity_usd={s.get('equity_usd',0.0):.2f}")
        return
    if context.args[0]=="set":
        if len(context.args)<2: reply(update,"Bruk: /equity set <USD>"); return
        try: usd = float(context.args[1])
        except Exception as e:
reply(update,"Ugyldig tall"); return
        usd = max(0.0, usd); s["equity_usd"]=usd; save_state(s)
        reply(update, f"💰 equity_usd satt: {usd:.2f}")
        return
    reply(update,"Bruk: /equity show|set <USD>")

def cmd_watch(update, context):
    s = load_state()
    w = s.setdefault("watch", [])
    if not context.args or context.args[0]=="list":
        reply(update, "watch: " + (",".join(w) if w else "(tom)"))
        return
    op = context.args[0]
    if op=="add" and len(context.args)>=2:
        for sym in context.args[1].split(","):
            sym=sym.strip().upper()
            if sym and sym not in w: w.append(sym)
        save_state(s); reply(update,"✅ lagt til")
        return
    if op=="rm" and len(context.args)>=2:
        sym=context.args[1].strip().upper()
        w[:] = [x for x in w if x!=sym]; save_state(s); reply(update,"✅ fjernet")
        return
    if op=="clear":
        s["watch"]=[]; save_state(s); reply(update,"🧹 watch tømt")
        return
    reply(update,"Bruk: /watch list|add SYM1,SYM2|rm SYM|clear")

def cmd_heartbeat_on(update, context):
    s = load_state(); s["hb_every_min"] = int(context.args[0]) if context.args else 15; save_state(s)
    reply(update, f"💓 heartbeat ON hver {s['hb_every_min']} min")

def cmd_heartbeat_off(update, context):
    s = load_state(); s["hb_every_min"] = 0; save_state(s)
    reply(update, "💤 heartbeat OFF")
PY

echo "[6/8] tg_bot.py"
cat > nova/telegram/tg_bot.py <<'PY'
import logging, os
from telegram.ext import Updater, CommandHandler
from .tg_utils import load_env, guard_chat
from . import tg_commands as C

logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL","INFO").upper()),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("nova.telegram.bot")

def main():
    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN") or env.get("TG_KEY")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN mangler i .env")

    updater = Updater(token, use_context=True)
    dp = updater.dispatcher

    # chat guard wrapper
    def wrap(fn):
        def _inner(update, context):
            if not guard_chat(update, env):
                update.message.reply_text("⛔ Ikke autorisert chat.")
                return
            return fn(update, context)
        return _inner

    dp.add_handler(CommandHandler("help", wrap(C.cmd_help)))
    dp.add_handler(CommandHandler("status", wrap(C.cmd_status)))
    dp.add_handler(CommandHandler("pnl", wrap(C.cmd_pnl)))
    dp.add_handler(CommandHandler("pos", wrap(C.cmd_pos)))

    dp.add_handler(CommandHandler("on", wrap(C.cmd_on)))
    dp.add_handler(CommandHandler("off", wrap(C.cmd_off)))
    dp.add_handler(CommandHandler("mode", wrap(C.cmd_mode)))
    dp.add_handler(CommandHandler("start_live", wrap(C.cmd_start_live)))
    dp.add_handler(CommandHandler("start_paper", wrap(C.cmd_start_paper)))
    dp.add_handler(CommandHandler("engine", wrap(C.cmd_engine)))

    dp.add_handler(CommandHandler("risk", wrap(C.cmd_risk)))
    dp.add_handler(CommandHandler("equity", wrap(C.cmd_equity)))
    dp.add_handler(CommandHandler("watch", wrap(C.cmd_watch)))
    dp.add_handler(CommandHandler("heartbeat_on", wrap(C.cmd_heartbeat_on)))
    dp.add_handler(CommandHandler("heartbeat_off", wrap(C.cmd_heartbeat_off)))

    log.info("Telegram-kontroller startet.")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
PY

echo "[7/8] systemd-enhet for TG"
sudo bash -c 'cat > /etc/systemd/system/novatg.service <<UNIT
[Unit]
Description=Nova Telegram Controller
After=network-online.target

[Service]
WorkingDirectory='"$ROOT"'
Environment="PYTHONUNBUFFERED=1"
ExecStart='"$ROOT"'/.venv/bin/python -u -m nova.telegram.tg_bot
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT'

echo "[8/8] Enable & restart TG"
sudo systemctl daemon-reload
sudo systemctl enable novatg.service --now
systemctl --no-pager status novatg.service | sed -n '1,12p'
echo "Done."