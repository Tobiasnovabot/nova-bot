#!/usr/bin/env bash
set -Eeuo pipefail
cd "${1:-$PWD}"

# Én fast karantene-mappe, ikke rekursivt navn
TRASH="z_trash"
mkdir -p "$TRASH"/{secrets,bad_syntax,hidden,venv,logs,archives,unused}

echo "[1] Backup liten (uten .venv/.git/.tar/zip)"
tar --exclude='.venv' --exclude='.git' --exclude='*.tar*' --exclude='*.zip' \
    -czf "../novax_backup_$(date +%Y%m%d_%H%M%S).tar.gz" . || true

echo "[2] Flytt .venv trygt (hvis finnes)"
[ -d ".venv" ] && mv -f .venv "$TRASH/venv/.venv_$(date +%s)" || true

echo "[3] Fjern cache og søppel"
find . -type d -name "__pycache__" -prune -exec rm -rf {} + || true
find . -type d -name ".pytest_cache" -prune -exec rm -rf {} + || true
find . -type f -name "*.py[co]" -delete || true
find . -type f -name "*.log" -exec mv -f {} "$TRASH/logs/" \; || true
rm -rf build dist .tox .coverage htmlcov || true
find . -maxdepth 2 -type d -name "*.egg-info" -exec rm -rf {} + || true
for d in backups backup old legacy tmp temp scratch drafts notebooks experiments data/raw_dumps; do
  [ -e "$d" ] && mv -f "$d" "$TRASH/unused/$d.$(date +%s)" || true
done

echo "[4] Skjulte filer (behold .git, .env, .gitignore, .gitattributes)"
find . -mindepth 1 -maxdepth 3 -type f -name ".*" \
  ! -path "./.git/*" ! -name ".gitignore" ! -name ".gitattributes" ! -name ".env" \
  -exec mv -f {} "$TRASH/hidden/" \; || true
find . -mindepth 1 -maxdepth 3 -type d -name ".*" ! -name ".git" -prune \
  -exec bash -lc 'for p in "$@"; do mv -f "$p" "'"$TRASH"'/hidden/$(basename "$p").$(date +%s)"; done' _ {} \; || true

echo "[5] Hemmeligheter og arkiver"
find . -type f -regextype posix-extended -regex '.*(\.env\.bak.*|\.bak(\.|$)).*' -exec mv -f {} "$TRASH/secrets/" \; || true
find . -type f \( -iname "*alertmanager*.yml" -o -iname "*alertmanager*.yaml" \) -exec mv -f {} "$TRASH/secrets/" \; || true
find . -type f \( -iname "*.tar" -o -iname "*.tar.gz" -o -iname "*.zip" \) -exec mv -f {} "$TRASH/archives/" \; || true

echo "[6] Sørg for __init__.py"
python3 - <<'PY'
import pathlib
root=pathlib.Path(".")
for d in root.rglob("*"):
    if d.is_dir() and not any(x in d.parts for x in (".git","z_trash","__pycache__", ".venv")):
        p=d/"__init__.py"
        if not p.exists():
            try: p.write_text("# auto: package marker\n", encoding="utf-8")
            except: pass
print("init-ok")
PY

echo "[7] Stub manglende strategier fra router"
python3 - <<'PY'
import re, pathlib
root=pathlib.Path(".")
router=root/"nova"/"engine"/"router.py"
sdir=root/"strategies"; sdir.mkdir(parents=True, exist_ok=True)
if router.exists():
    s=router.read_text(encoding="utf-8", errors="ignore")
    mods=set(re.findall(r"from\s+nova\.strategies\.([A-Za-z0-9_]+)\s+import\s+", s))
    for mod in sorted(mods):
        t=sdir/f"{mod}.py"
        if not t.exists():
            t.write_text(f"class Strategy:\n name='{mod}'\n timeframe='auto'\n def setup(self,**k):pass\n def on_bar(self,df):return None\n def on_tick(self,t):return None\n def teardown(self):pass\n", encoding="utf-8")
print("strategies-ok")
PY

echo "[8] IKKE flytt ødelagte filer lenger (kun rapporter)"
python3 - <<'PY'
import ast, pathlib
bad=[]
for p in pathlib.Path(".").rglob("*.py"):
    if any(x in p.parts for x in (".git","z_trash","__pycache__", ".venv")): 
        continue
    try: ast.parse(p.read_text(encoding="utf-8",errors="ignore"))
    except Exception as e: bad.append((str(p), str(e).splitlines()[-1]))
print("files_with_syntax_errors=", len(bad))
for f,e in bad[:50]: print("-", f, "=>", e)
PY

echo "[9] .gitignore"
[ -f .gitignore ] || cat > .gitignore <<'IGN'
__pycache__/
*.py[cod]
.venv/
*.log
z_trash/
data/
*.tar
*.tar.gz
*.zip
.env.bak*
IGN

echo "Done."
