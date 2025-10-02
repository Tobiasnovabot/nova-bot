# nova/learn/optimizer.py
import json, time, math, pathlib, statistics as stats
from collections import defaultdict, deque

TRADES_FILE = pathlib.Path("runtime/trades.jsonl")
OVERRIDES_FILE = pathlib.Path("runtime/overrides.json")   # leses av ultra_runner via load_overrides()
STATE_FILE = pathlib.Path("runtime/optimizer_state.json") # intern tilstand (for glatting/rollback)

# --- konfig (enkle “hyperparametre” du kan tweake) ---
LOOKBACK_TRADES   = 400           # hvor mange siste trades vurderes (rullerende)
MIN_TRADES_STRAT  = 20            # min trades per strategi før vi stoler på score
MIN_TRADES_PAIR   = 10            # min trades per par før per-par skruing
TOP_PAIRS_PER_STRAT = 30          # maks antall par vi eksplisitt favoriserer per strategi
RISK_MIN, RISK_MAX = 0.01, 0.08   # auto-justering av RISK_FRAC
EPS_EXPLORE       = 0.10          # 10% utforsking: tvang på litt signaler selv om score er svak
DD_HARD_STOP      = 0.12          # hard daily drawdown cut (ekstra failsafe)
ROLLBACK_THRESHOLD= -0.08         # hvis ny policy gir -8% relativt, rull tilbake

# --- hjelpefunksjoner ---
def load_trades(limit=LOOKBACK_TRADES):
    rows = []
    if not TRADES_FILE.exists(): return rows
    with TRADES_FILE.open() as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try:
                rows.append(json.loads(line))
            except:
                pass
    # behold kun siste N, og kun live trades med symbol/side/cost/qty
    rows = [r for r in rows if r.get("live") and r.get("symbol") and r.get("side")]
    return rows[-limit:]

def trade_pnl_estimate(t):
    """
    Estimer trade-PnL i QUOTE (enkelt anslag):
    - For MARKET-fills har vi 'cummulativeQuoteQty' på order-info
    - Fees finnes ofte per fill i 'fee'
    Vi bruker sign (+1 buy ut, -1 sell inn) for rullerende PnL dersom ordrepar (buy->sell) finnes.
    For enkel robusthet: vi estimerer 'cash flow' per trade.
    """
    o = t.get("order", {})
    info = o.get("info", {})
    quote_qty = float(info.get("cummulativeQuoteQty") or 0.0)
    side = t.get("side")
    fee = 0.0
    # summer fees i quote dersom de finnes
    if "fees" in o and isinstance(o["fees"], list):
        for fee_row in o["fees"]:
            if fee_row.get("currency","").upper() in ("USDC","USDT","FDUSD"):  # enkel heuristikk
                fee += float(fee_row.get("cost") or 0.0)
    if side == "buy":
        cash = -(quote_qty + fee)
    else:
        cash = +(quote_qty - fee)
    return cash

def expectancy(win_flows, loss_flows):
    # forventningsverdi per trade (forenklet):
    if not win_flows and not loss_flows: return 0.0
    wr = len(win_flows) / (len(win_flows) + len(loss_flows)) if (win_flows or loss_flows) else 0.0
    avg_win  = stats.fmean(win_flows) if win_flows else 0.0
    avg_loss = abs(stats.fmean(loss_flows)) if loss_flows else 0.0
    # klassisk: E = WR*avg_win - (1-WR)*avg_loss
    return wr * avg_win - (1 - wr) * avg_loss

def score_series(flows):
    """
    flows = liste av cash flows per ordre (positiv/negativ i QUOTE).
    Vi grupperer inn/ut parvis grovt via rullerende sum for å skille 'round-trip' gevinst.
    """
    if not flows: return 0.0, 0.0, 0.0
    # enkel dekomponering i vinner/taper transjer: positive/negative
    wins  = [x for x in flows if x > 0]
    losses= [x for x in flows if x < 0]
    expc  = expectancy(wins, losses)
    # “stabilitet”: Sharpe-ish på flows (unscaled)
    sharpe = 0.0
    if len(flows) >= 5 and (sd:=stats.pstdev(flows))>1e-9:
        sharpe = (stats.fmean(flows))/sd
    # “edge-score”: kombiner litt
    score = 0.7*expc + 0.3*sharpe
    return score, expc, sharpe

def capped(v, lo, hi): return max(lo, min(hi, v))

def softmax(xs):
    if not xs: return []
    m = max(xs)
    ex = [math.exp(x-m) for x in xs]
    s  = sum(ex)
    return [e/s for e in ex] if s>0 else [1/len(xs)]*len(xs)

# --- hovedlogikk ---
def optimize():
    trades = load_trades()
    if not trades:
        return {"message":"no_trades_yet", "overrides":{}}

    # trekk ut “strategy” hvis vi har det i trade-logg (kan ligge i order->info eller vi kan mappe senere)
    # robust fallback: vi scorer per symbol og bruker globale strategy metrics fra metricsfil senere hvis ønskelig
    # her: anta at strategi-navn ligger i t.get("strategy") hvis du begynner å logge det.
    flows_by_strat = defaultdict(list)
    flows_by_pair  = defaultdict(list)

    for t in trades:
        cash = trade_pnl_estimate(t)
        sym  = t.get("symbol","")
        strat = t.get("strategy") or "unknown"
        flows_by_pair[sym].append(cash)
        flows_by_strat[strat].append(cash)

    # score strategier
    strat_scores = {}
    for s, flows in flows_by_strat.items():
        sc, expc, shrp = score_series(flows)
        strat_scores[s] = {"score": sc, "exp": expc, "sharpe": shrp, "n": len(flows)}

    # score par
    pair_scores = {}
    for p, flows in flows_by_pair.items():
        sc, expc, shrp = score_series(flows)
        pair_scores[p] = {"score": sc, "exp": expc, "sharpe": shrp, "n": len(flows)}

    # velg strategier: disable svake, vekt gode
    # filtrer på min trades
    active = {s:v for s,v in strat_scores.items() if v["n"]>=MIN_TRADES_STRAT}
    if not active:
        # for tidlig – ikke rør strategier enda
        strat_policy = {"enable": {}, "weights": {}}
    else:
        # normaliser til vekter via softmax
        names = list(active.keys())
        xs    = [active[s]["score"] for s in names]
        ws    = softmax(xs)
        strat_policy = {
            "enable": {s: (active[s]["score"]>0 or (i==xs.index(max(xs)))) for i,s in enumerate(names)},
            "weights": {s: w for s,w in zip(names, ws)}
        }

    # velg topp-par per strategi (enkelt: samme topp-liste for begge strategier basert på par-score)
    good_pairs = [k for k,v in sorted(pair_scores.items(), key=lambda kv: kv[1]["score"], reverse=True)
                  if v["n"]>=MIN_TRADES_PAIR and v["score"]>0][:TOP_PAIRS_PER_STRAT]

    # foreslå risiko basert på total “edge”
    all_flows = [trade_pnl_estimate(t) for t in trades]
    total_score, total_exp, total_sh = score_series(all_flows)
    # enkel mapping: høyere score -> høyere risiko innenfor [RISK_MIN,RISK_MAX]
    if total_score <= 0:
        risk_frac = RISK_MIN
    else:
        # squashing
        risk_frac = capped(RISK_MIN + 0.5*(RISK_MAX-RISK_MIN)*(1 - math.exp(-total_score)), RISK_MIN, RISK_MAX)

    # Epsilon-utforskning: tving litt “på” for å samle data
    explore_flag = (time.time() % 100.0) < (EPS_EXPLORE*100.0)

    overrides = {
        "risk_frac": risk_frac,
        "strategies": {},
        "enable_pairs": {},   # whitelist
        "disable_pairs": {},  # blacklist (ikke brukt her, men støttes)
    }

    for s in strat_scores.keys():
        en = strat_policy.get("enable", {}).get(s, True)
        w  = strat_policy.get("weights", {}).get(s, 0.5)
        if explore_flag:  # aldri skru helt av alt – hold et lite signalinntak
            en = True if s != "unknown" else en
            w  = max(w, 0.1)
        overrides["strategies"][s] = {"enabled": bool(en), "weight": float(w)}

    for p in good_pairs:
        overrides["enable_pairs"][p] = True

    # daglig dd hard-stop (for sikkerhet – runner’en kan også håndheve denne)
    overrides["daily_dd_limit"] = DD_HARD_STOP

    # enkel rollback-beskyttelse: hvis forrige policy fungerte betydelig bedre, behold den
    try:
        prev = json.loads(STATE_FILE.read_text())
        prev_score = float(prev.get("total_score", 0.0))
        if (total_score - prev_score) < ROLLBACK_THRESHOLD:
            # rull tilbake
            old_over = prev.get("last_overrides")
            if old_over:
                OVERRIDES_FILE.write_text(json.dumps(old_over, indent=2))
                return {"message":"rollback_to_previous_overrides", "overrides": old_over}
    except Exception:
        pass

    # lagre ny policy
    OVERRIDES_FILE.parent.mkdir(exist_ok=True)
    OVERRIDES_FILE.write_text(json.dumps(overrides, indent=2))
    STATE_FILE.write_text(json.dumps({"total_score": total_score, "last_overrides": overrides}, indent=2))
    return {"message":"ok", "overrides": overrides}

if __name__ == "__main__":
    out = optimize()
    print(json.dumps(out, indent=2))
