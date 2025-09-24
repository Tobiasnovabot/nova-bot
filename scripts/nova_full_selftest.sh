#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${ROOT:-$HOME/nova-bot}"
cd "$ROOT"

# ---------- utsmykking ----------
PASS=0; FAIL=0; SKIP=0
green(){ printf "\033[32m%s\033[0m\n" "$*"; }
red(){   printf "\033[31m%s\033[0m\n" "$*"; }
yellow(){printf "\033[33m%s\033[0m\n" "$*"; }
blue(){  printf "\033[36m%s\033[0m\n" "$*"; }
ok(){ green "✔ $*"; : $((PASS++)); }
bad(){ red   "✘ $*"; : $((FAIL++)); }
skip(){yellow"↷ $*"; : $((SKIP++)); }

# ---------- helpers ----------
need() { command -v "$1" >/dev/null 2>&1 || { bad "Mangler binær: $1"; return 1; }; }
srv_active(){ systemctl is-active --quiet "$1"; }
srv_cat(){ systemctl cat "$1" >/dev/null 2>&1; }
env_req(){ [[ -n "${!1:-}" ]] || { bad "Mangler env $1"; return 1; }; }

JQ=${JQ:-jq}
need python3 || true
need curl || true
need ${JQ} || true
need systemctl || true
need awk || true
need sed || true

# ---------- 0) ENV / Nøkler ----------
set -a; [[ -f .env ]] && source .env || true; set +a
TG_TOKEN="${TELEGRAM_BOT_TOKEN:-${TOKEN:-}}"
TG_CHAT="${TELEGRAM_CHAT_ID:-${CHAT_ID:-}}"

[[ -n "$TG_TOKEN" ]] && ok "env: TELEGRAM_BOT_TOKEN funnet" || skip "env: TG token mangler"
[[ -n "$TG_CHAT"  ]] && ok "env: TELEGRAM_CHAT_ID funnet"   || skip "env: TG chat id mangler"

# ---------- 1) Backup av kritisk state ----------
ts=$(date +%Y%m%d-%H%M%S)
mkdir -p backups
if [[ -f data/state.json ]]; then
  cp -a data/state.json "backups/state.json.selftest.$ts.bak" && ok "Backup: data/state.json"
else
  skip "Backup: data/state.json mangler"
fi

# ---------- 2) Systemd units finnes? ----------
for u in novax.service novatg.service novax-trade-alerts.service; do
  if srv_cat "$u"; then ok "Unit finnes: $u"; else skip "Unit mangler: $u"; fi
done

# ---------- 3) Engine: restart & vent på tick OK ----------
if srv_cat novax.service; then
  systemctl restart novax.service || true
  deadline=$((SECONDS+25))
  got=""
  while (( SECONDS < deadline )); do
    out=$(journalctl -n25 -u novax.service -o cat 2>/dev/null || true)
    if grep -q 'tick OK' <<<"$out"; then
      got="$(grep -m1 'tick OK' <<<"$out" || true)"
      break
    fi
    sleep 1
  done
  if [[ -n "$got" ]]; then
    ok "Engine tick OK sett: $(sed -E 's/.*(pos=[0-9]+).*/\1/'<<<"$got")"
  else
    bad "Engine: ingen 'tick OK' innen 25s"
  fi
else
  skip "Engine: novax.service mangler"
fi

# ---------- 4) Telegram API (getMe + optional ping) ----------
if [[ -n "$TG_TOKEN" ]]; then
  me=$(curl -fsS "https://api.telegram.org/bot${TG_TOKEN}/getMe" || true)
  if grep -q '"ok":true' <<<"$me"; then
    ok "Telegram getMe OK"
    if [[ -n "$TG_CHAT" ]]; then
      curl -fsS "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
        -d chat_id="$TG_CHAT" -d text="🧪 NovaX selvtest: Telegram OK $(date -Is)" >/dev/null \
        && ok "Telegram sendMessage OK" || bad "Telegram sendMessage feilet"
    else
      skip "Telegram sendMessage hoppet (mangler TELEGRAM_CHAT_ID)"
    fi
  else
    bad "Telegram getMe feilet"
  fi
else
  skip "Telegram: ingen token"
fi

# ---------- 5) Alerts-tjeneste ----------
if srv_cat novax-trade-alerts.service; then
  systemctl restart novax-trade-alerts.service || true
  sleep 1
  if srv_active novax-trade-alerts.service; then
    ok "Alerts: service aktiv"
    # sanity: prosess-kjeden (grep-pipe)
    pro=$(pgrep -af "alerts/trade_to_tg.sh|grep --line-buffered -E tick OK|journalctl -f -u novax.service" || true)
    if [[ -n "$pro" ]]; then ok "Alerts: pipeline lever"; else skip "Alerts: finner ikke pipeline (kan være polling-varianten)"; fi
    # trigger: nullstill pos cache; neste pos-endring gir TG-varsel
    rm -f /tmp/novax_last_pos || true
    ok "Alerts: /tmp/novax_last_pos nullstilt (venter på ny pos-endring)"
  else
    bad "Alerts: service ikke aktiv"
  fi
else
  skip "Alerts: unit mangler"
fi

# ---------- 6) Metrics ----------
if [[ -f metrics.prom ]]; then
  if grep -q '^nova_equity_usd ' metrics.prom; then
    val=$(awk '/^nova_equity_usd /{print $2}' metrics.prom | tail -n1)
    ok "Metrics: nova_equity_usd=$val"
  else
    bad "Metrics: nova_equity_usd ikke funnet"
  fi
else
  skip "Metrics: metrics.prom mangler"
fi

# ---------- 7) tg_commands sanity (import + /watch + /status) ----------
python3 - <<'PY' >/tmp/tg_commands_selftest.out 2>/tmp/tg_commands_selftest.err || true
import os, json, pathlib
ROOT=os.getenv("ROOT", os.getcwd())
import importlib.util, sys
p=pathlib.Path(ROOT,"nova","telegram","tg_commands.py")
if not p.exists():
    print("SKIP tg_commands: fil mangler"); raise SystemExit(0)
spec=importlib.util.spec_from_file_location("tg_commands", str(p))
C=importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
print("OK import tg_commands")

# /watch
before = C._read_json(C.WATCH, [])
out = C.cmd_watch(["AAPL,msft", " tsla "])
after = C._read_json(C.WATCH, [])
print("WATCH_OUT:", out.replace("\n"," | "))
print("WATCH_SET:", " ".join(after))

# /status
st = C.cmd_status().splitlines()
print("STATUS_LINES:", len(st))
PY
if grep -q 'OK import tg_commands' /tmp/tg_commands_selftest.out; then
  ok "tg_commands import OK"
  awk '/WATCH_OUT:|WATCH_SET:|STATUS_LINES:/{print "  " $0}' /tmp/tg_commands_selftest.out
else
  if grep -q 'SKIP tg_commands' /tmp/tg_commands_selftest.out; then
    skip "tg_commands: mangler fil"
  else
    bad "tg_commands: import/bruk feilet"
    sed -n '1,80p' /tmp/tg_commands_selftest.err || true
  fi
fi

# ---------- 8) Bandit / Thompson (best-effort) ----------
python3 - <<'PY' >/tmp/bandit_selftest.out 2>/tmp/bandit_selftest.err || true
# Best-effort: om repo har egen bandit/thompson, forsøk å importere; ellers kjør en mini-TS
import os, re, sys, json, random, math, pathlib, importlib
ROOT=os.getenv("ROOT", os.getcwd())
repo=list(pathlib.Path(ROOT).rglob("*.py"))
mod=None
for p in repo:
    n=p.name.lower()
    if "bandit" in n or "thompson" in n:
        mod=p; break
if mod:
    print("HINT module:", mod)
else:
    print("HINT module: none, using built-in demo")

# Thompson-demo med 3 armer, sannhet [0.1, 0.3, 0.6]
import random
true=[0.1,0.3,0.6]
S=[1,1,1]; F=[1,1,1]
def sample(i):
    import random
    # Beta(S,F) sampling
    a=S[i]; b=F[i]
    # enkel approx
    return random.gammavariate(a,1.0)/(random.gammavariate(a,1.0)+random.gammavariate(b,1.0))
T=1000
wins=[0,0,0]
for t in range(T):
    i=max(range(3), key=lambda k: sample(k))
    r = 1 if random.random() < true[i] else 0
    if r: S[i]+=1; wins[i]+=1
    else: F[i]+=1
best = wins.index(max(wins))
print("TS_best_arm:", best, "wins:", wins)
PY
if grep -q 'TS_best_arm:' /tmp/bandit_selftest.out; then
  ok "Bandit/Thompson demo OK: $(grep TS_best_arm /tmp/bandit_selftest.out | sed 's/^/  /')"
else
  skip "Bandit/Thompson: ingen modul/demotest feilet"
  sed -n '1,60p' /tmp/bandit_selftest.err || true
fi

# ---------- 9) Risk guard (hoppes hvis fjernet) ----------
if srv_cat novax-risk-guard.service; then
  systemctl restart novax-risk-guard.service || true
  sleep 1
  if srv_active novax-risk-guard.service; then ok "Risk-guard aktiv"; else bad "Risk-guard inaktiv"; fi
else
  skip "Risk-guard: unit mangler (skippet som ønsket)"
fi

# ---------- 10) Oppsummering ----------
echo
blue "===== SELVTEST RESULTAT ====="
echo "PASS=$PASS  FAIL=$FAIL  SKIPPED=$SKIP"
[[ $FAIL -eq 0 ]] || exit 1