import os
from pathlib import Path
try:
    from dotenv import dotenv_values
except Exception:
    dotenv_values=None

def _parse_env(p:Path):
    if dotenv_values: return dotenv_values(p)
    out={}
    for line in p.read_text().splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1); out[k.strip()]=v.strip()
    return out

def load_secrets(dir_path='secrets'):
    d=Path(dir_path)
    if not d.exists(): return
    for p in sorted(d.glob('*.env')):
        data=_parse_env(p) or {}
        if 'OKX_PASSPHRASE' in data and 'OKX_PASSWORD' not in data:
            data['OKX_PASSWORD']=data['OKX_PASSPHRASE']
        for k,v in data.items():
            if (k not in os.environ) or (os.environ.get(k,'')==''):
                os.environ[k]=str(v)
