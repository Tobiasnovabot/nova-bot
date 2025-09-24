#!/usr/bin/env bash
set -euo pipefail

PROM="http://127.0.0.1:9090"
jqnum='if .status=="success" and (.data.result|length)>=1 then (.data.result[0].value[1]|tonumber) else null end'

qnum(){ curl -fsS "$PROM/api/v1/query" --get --data-urlencode "query=$1" | jq -r "$jqnum"; }

lag=$(qnum 'novax_engine_lag_seconds')
avail=$(qnum 'novax_balance_available_usd')
equity=$(qnum 'novax_equity_total_usd')
pos=$(qnum 'novax_positions_open')
hb_cnt=$(qnum 'increase(novax_engine_heartbeat_total[15m])')
expo_up=$(curl -fsS "$PROM/api/v1/query" --get --data-urlencode 'query=up{job="novax_exporter"}' \
     | jq -r 'if .data.result|length>0 then (.data.result[0].value[1]|tonumber) else 0 end')

now_utc="$(date -u +'%Y-%m-%d %H:%M:%S UTC')"

fmt(){
  v="$1"; d="$2"
  if [[ "$v" == "null" || -z "${v}" ]]; then echo "$d"; else printf "%'.2f" "$v"; fi
}

lag_s="n/a"; if [[ "$lag" != "null" && -n "${lag}" ]]; then lag_s="${lag%.*}s"; fi
avail_s="$(fmt "${avail:-}" "n/a")"
equity_s="$(fmt "${equity:-}" "n/a")"
pos_s="$(printf "%s" "${pos:-0}" | sed 's/\.0$//;s/null/0/')"
hb_s="$(printf "%s" "${hb_cnt:-0}" | sed 's/\.0$//;s/null/0/')"
expo_emoji=$([ "$expo_up" = "1" ] && echo "🟢" || echo "🔴")

cat <<MSG
🧠 NovaX Status
🕒 ${now_utc}
${expo_emoji} exporter: $( [ "$expo_up" = "1" ] && echo "UP" || echo "DOWN" )
💓 heartbeats(15m): ${hb_s}
⏱️ engine-lag: ${lag_s}
💰 balance avail: \$${avail_s}
📈 equity total: \$${equity_s}
📦 open positions: ${pos_s}
MSG