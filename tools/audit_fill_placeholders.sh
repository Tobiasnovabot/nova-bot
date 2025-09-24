#!/usr/bin/env bash
set -euo pipefail
ROOT="${ROOT:-$HOME/nova-bot}"
cd "$ROOT"

# Mapper å utelate
EXCL=(-path "./.venv" -o -path "./__pycache__" -o -path "./logs" -o -path "./data/backups" -o -path "./backups")

changed=()
empty=()

# Finn alle TOMME filer (0 bytes) i repoet (utenom ekskluderte mapper)
while IFS= read -r -d '' f; do
  empty+=("$f")
done < <(find . -type f -size 0 \( ! \( "${EXCL[@]}" \) \) -print0)

# Funksjon: trygg utfylling av kjente filtyper
fill_if_empty() {
  local f="$1"
  case "$f" in
    ./nova/**/__init__.py|./nova/*/__init__.py|./nova/*/*/__init__.py)
      printf "# Package init: %s\n" "$(basename "$(dirname "$f")")" > "$f"
      changed+=("$f")
      ;;
    ./data/equity.json)
      cat > "$f" <<'JSON'
{
  "timestamp": "1970-01-01T00:00:00Z",
  "equity_usdt": 0.0,
  "balance": {},
  "positions": [],
  "pnl": { "realized": 0.0, "unrealized": 0.0 }
}
JSON
      changed+=("$f")
      ;;
    ./data/state.json)
      cat > "$f" <<'JSON'
{
  "watch": [],
  "mode": "paper",
  "exchange": "binance"
}
JSON
      changed+=("$f")
      ;;
    ./data/alerts_state.json)
      echo '{}' > "$f"
      changed+=("$f")
      ;;
    ./data/metrics.prom)
      echo 'novax_exporter_ok 1' > "$f"
      changed+=("$f")
      ;;
    *.py)
      cat > "$f" <<'PY'
#!/usr/bin/env python3
"""Placeholder file created to avoid import errors; please fill with real logic."""
PY
      changed+=("$f")
      ;;
    *.sh)
      cat > "$f" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
# TODO: implement
SH
      chmod +x "$f"
      changed+=("$f")
      ;;
    *.service|*.timer|*.conf|*.ini|*.yaml|*.yml|*.toml)
      echo "# placeholder" > "$f"
      changed+=("$f")
      ;;
    *)
      # Ikke rør ukjente tomme filer – legg dem kun til review
      :
      ;;
  esac
}

# Fyll kjente tomme filer
for f in "${empty[@]}"; do
  fill_if_empty "$f"
done

# Lag review-lister
mkdir -p tools/_audit
printf "%s\n" "${empty[@]}"   | sed 's|^\./||' > tools/_audit/EMPTY_FOUND.txt
printf "%s\n" "${changed[@]}" | sed 's|^\./||' > tools/_audit/FILLED_NOW.txt

echo "== RESULTAT =="
echo "Tomme filer funnet: ${#empty[@]}  (liste: tools/_audit/EMPTY_FOUND.txt)"
echo "Utfylt nå:          ${#changed[@]} (liste: tools/_audit/FILLED_NOW.txt)"
echo ""
echo "Neste steg:"
echo "1) Sjekk ALT som fortsatt er tomt (ikke automatisk utfylt):"
echo "   while read -r f; do [ -s \"$f\" ] || nano \"$f\"; done < tools/_audit/EMPTY_FOUND.txt"
echo ""
echo "2) Gå gjennom alt som ble fylt nå (for å lagre ordentlig):"
echo "   while read -r f; do nano \"$f\"; done < tools/_audit/FILLED_NOW.txt"