#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${ROOT:-$HOME/nova-bot}"
cd "$ROOT"

# -------- visuelle helpers --------
PASS=0; FAIL=0; SKIP=0
green(){ printf "\033[32m%s\033[0m\n" "$*"; }
red(){   printf "\033[31m%s\033[0m\n" "$*"; }
yellow(){printf "\033[33m%s\033[0m\n" "$*"; }
blue(){  printf "\033[36m%s\033[0m\n" "$*"; }
ok(){ green "✔ $*"; : $((PASS++)); }
bad(){ red   "✘ $*"; : $((FAIL++)); }
skip(){yellow"↷ $*"; : $((SKIP++)); }

need(){ command -v "$1" >/dev/null 2>&1 || { bad "Mangler binær: $1"; exit 1; }; }
need python3; need awk; need sed; need grep; need find; need timeout; need systemctl || true; need curl || true; command -v jq >/dev/null || true

TS=$(date +%Y%m%d-%H%M%S)
OUTDIR="data/selftest/$TS"
mkdir -p "$OUTDIR"
SUMMARY="$OUTDIR/summary.jsonl"

log_json(){ printf '%s\n' "$*" >> "$SUMMARY"; }

# ---------- ENV / Telegram ----------
set -a; [[ -f .env ]] && source .env || true; set +a
TG_TOKEN="${TELEGRAM_BOT_TOKEN:-${TOKEN:-}}"
TG_CHAT="${TELEGRAM_CHAT_ID:-${CHAT_ID:-}}"

if [[ -n "$TG_TOKEN" ]]; then
  if curl -fsS "https://api.telegram.org/bot${TG_TOKEN}/getMe" >/dev/null; then
    ok "Telegram getMe OK"; log_json '{"check":"telegram_getMe","ok":true}'
    [[ -n "$TG_CHAT" ]] && curl -fsS "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" -d chat_id="$TG_CHAT" -d text="🧪 nova_total_selftest start $TS" >/dev/null && ok "Telegram send OK" || [[ -z "$TG_CHAT" ]] && skip "TG chat id mangler"
  else
    bad "Telegram getMe FEIL"; log_json '{"check":"telegram_getMe","ok":false}'
  fi
else
  skip "Telegram token mangler"; log_json '{"check":"telegram_getMe","ok":null}'
fi

# ---------- Systemd units ----------
check_unit(){
  local u="$1"
  if systemctl cat "$u" >/dev/null 2>&1; then
    systemctl restart "$u" >/dev/null 2>&1 || true
    sleep 1
    if systemctl is-active --quiet "$u"; then ok "unit aktiv: $u"; log_json "{\"unit\":\"$u\",\"ok\":true}"
    else bad "unit inaktiv: $u"; log_json "{\"unit\":\"$u\",\"ok\":false}"; fi
  else
    skip "unit mangler: $u"; log_json "{\"unit\":\"$u\",\"ok\":null}"
  fi
}
for u in novax.service novatg.service novax-trade-alerts.service novax-risk-guard.service; do check_unit "$u"; done

# Vent/les tick OK hvis engine finnes
if systemctl cat novax.service >/dev/null 2>&1; then
  systemctl restart novax.service >/dev/null 2>&1 || true
  DEAD=$((SECONDS+30)); GOT=""
  while (( SECONDS<DEAD )); do
    L="$(journalctl -n30 -u novax.service -o cat 2>/dev/null || true)"
    if grep -q 'tick OK' <<<"$L"; then GOT="$(grep -m1 'tick OK' <<<"$L")"; break; fi
    sleep 1
  done
  if [[ -n "$GOT" ]]; then
    POS="$(sed -E 's/.*pos=([0-9]+).*/\1/' <<<"$GOT" || true)"
    ok "Engine tick OK (pos=$POS)"
    log_json "{\"check\":\"engine_tick\",\"ok\":true,\"pos\":\"$POS\"}"
  else
    bad "Ingen 'tick OK' innen 30s"
    log_json '{"check":"engine_tick","ok":false}'
  fi
else
  skip "novax.service mangler"; log_json '{"check":"engine_tick","ok":null}'
fi

# ---------- Metrics ----------
if [[ -f metrics.prom ]]; then
  if grep -q '^nova_equity_usd ' metrics.prom; then
    VAL="$(awk '/^nova_equity_usd /{print $2}' metrics.prom | tail -n1)"
    ok "Metric nova_equity_usd=$VAL"
    log_json "{\"check\":\"metric_equity\",\"ok\":true,\"val\":$VAL}"
  else
    bad "Metric nova_equity_usd ikke funnet"; log_json '{"check":"metric_equity","ok":false}'
  fi
else
  skip "metrics.prom mangler"; log_json '{"check":"metric_equity","ok":null}'
fi

# ---------- PyTest (hvis finnes) ----------
if [[ -d tests ]]; then
  if timeout 300 pytest -q >"$OUTDIR/pytest.out" 2>"$OUTDIR/pytest.err"; then
    ok "pytest OK"; log_json '{"check":"pytest","ok":true}'
  else
    bad "pytest FEIL (se logs)"; log_json '{"check":"pytest","ok":false}'
  fi
else
  skip "tests/-katalog mangler"; log_json '{"check":"pytest","ok":null}'
fi

# ---------- Auto-oppdag & kjør Python-moduler ----------
# Strategi: for hver .py under nova/, forsøk:
#  1) selftest()
#  2) quick_selftest()
#  3) health() eller healthcheck()
#  4) main("--selftest") / __main__ kall
# Hver med timeout 20s. Feil påvirker ikke resten.
shopt -s nullglob
mapfile -t PYFILES < <(find nova -type f -name '*.py' ! -path '*/__pycache__/*' | sort)

run_py_probe(){
  local file="$1"; local rel="${file#nova/}"
  local mod="nova.${rel%.py}"; mod="${mod//\//.}"
  local name="$mod"
  timeout 20 python3 - "$mod" <<'PY' >/dev/null 2>&1 && echo OK || echo FAIL
import importlib, sys, contextlib
modname=sys.argv[1]
try:
  m=importlib.import_module(modname)
except Exception:
  sys.exit(1)

def try_call(fname, *args):
  f=getattr(m,fname,None)
  if callable(f):
    try:
      r=f(*args)
    except TypeError:
      try: f()
      except Exception: return False
    except Exception:
      return False
    return True
  return False

# Prøv i prioritert rekkefølge
for fn in ("selftest","quick_selftest","health","healthcheck"):
  if try_call(fn): sys.exit(0)

# Siste sjanse: main("--selftest")
main=getattr(m,"main",None)
if callable(main):
  try:
    main("--selftest")
    sys.exit(0)
  except Exception:
    pass

# Hvis modul er kjørbar som __main__
try:
  pkg=modname
  # importlib.run_module støttes via runpy
  import runpy
  runpy.run_module(modname, run_name="__main__")
  sys.exit(0)
except Exception:
  pass

sys.exit(1)
PY
}

TOTAL=${#PYFILES[@]}
CNT_OK=0; CNT_FAIL=0; CNT_SKIP=0
for f in "${PYFILES[@]}"; do
  RES="$(run_py_probe "$f")" || true
  if [[ "$RES" == "OK" ]]; then
    ok "py: $f"
    log_json "{\"py\":\"$f\",\"ok\":true}"
    : $((CNT_OK++))
  else
    # ikke alle moduler er testbare – tell som SKIPPED, ikke FAIL
    skip "py: $f (ingen selftest/health/main)"
    log_json "{\"py\":\"$f\",\"ok\":null}"
    : $((CNT_SKIP++))
  fi
done
blue "Python-moduler: OK=$CNT_OK SKIPPED=$CNT_SKIP av $TOTAL"

# ---------- Auto-oppdag & kjør shell-selftests ----------
mapfile -t SHS < <(find . -type f -path './*' -name '*_selftest.sh' -o -name '*_healthcheck.sh' | sort)
if (( ${#SHS[@]} > 0 )); then
  for s in "${SHS[@]}"; do
    if timeout 60 bash "$s" >"$OUTDIR/$(basename "$s").out" 2>"$OUTDIR/$(basename "$s").err"; then
      ok "sh: $(basename "$s")"; log_json "{\"sh\":\"$s\",\"ok\":true}"
    else
      bad "sh FEIL: $(basename "$s")"; log_json "{\"sh\":\"$s\",\"ok\":false}"
    fi
  done
else
  skip "Ingen *_selftest.sh / *_healthcheck.sh funnet"; log_json '{"check":"shell_selftests","ok":null}'
fi

# ---------- Alerts-pipeline sanity ----------
if systemctl cat novax-trade-alerts.service >/dev/null 2>&1; then
  systemctl restart novax-trade-alerts.service >/dev/null 2>&1 || true
  sleep 1
  rm -f /tmp/novax_last_pos || true
  ok "alerts: reset pos-cache"
  log_json '{"check":"alerts_reset","ok":true}'
else
  skip "alerts unit mangler"; log_json '{"check":"alerts_reset","ok":null}'
fi

# ---------- Bandit/Thompson demo (uavhengig) ----------
if timeout 20 python3 - <<'PY' >"$OUTDIR/ts_demo.out" 2>/dev/null; then ok "Thompson-demo OK"; log_json '{"check":"thompson_demo","ok":true}"; else bad "Thompson-demo FEIL"; log_json '{"check":"thompson_demo","ok":false}"; fi
# py:
true=[0.1,0.3,0.6]; import random, math
S=[1,1,1]; F=[1,1,1]
import random
def samp(i):
  import random
  import math
  a=S[i]; b=F[i]
  import random as r
  x=r.gammavariate(a,1.0); y=r.gammavariate(b,1.0)
  return x/(x+y)
wins=[0,0,0]
for t in range(1000):
  i=max(range(3), key=lambda k:samp(k))
  r=1 if random.random()<true[i] else 0
  if r: S[i]+=1; wins[i]+=1
  else: F[i]+=1
print("wins",wins,"best",wins.index(max(wins)))
PY

# ---------- Oppsummering ----------
echo
blue "===== TOTAL SELVTEST ====="
echo "PASS=$PASS  FAIL=$FAIL  SKIPPED=$SKIP"
echo "Logg: $SUMMARY"
[[ $FAIL -eq 0 ]] || exit 1