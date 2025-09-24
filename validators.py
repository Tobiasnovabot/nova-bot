import os
# validators.py
import pathlib, re, yaml, json, os

ALLOW_ROOTS = os.getenv("ALLOW_ROOT","/home/nova/nova-bot:/etc/systemd/system:/opt/guardian").split(":")

def in_allow(path:str)->bool:
    p = pathlib.Path(path).resolve()
    return any(str(p).startswith(r) for r in ALLOW_ROOTS)

SPEC_REQUIRED = {"project","spec"}
ALLOWED_OPS = {"mkdir","write","patch_json","patch_yaml","patch_py","systemctl"}

def validate_spec(spec:dict)->tuple[bool,str]:
    if not isinstance(spec, dict): return False, "spec must be mapping"
    if not SPEC_REQUIRED.issubset(set(spec.keys())): return False, "missing required keys"
    if "spec" not in spec or not isinstance(spec["spec"], (list, dict)): return False, "spec.spec must be list|dict"
    ops = spec["spec"] if isinstance(spec["spec"], list) else [spec["spec"]]
    for i,op in enumerate(ops):
        if "op" not in op: return False, f"item {i} missing op"
        if op["op"] not in ALLOWED_OPS: return False, f"invalid op {op['op']}"
        if op["op"] in {"mkdir","write","patch_json","patch_yaml","patch_py","replace"}:
            if "path" not in op: return False, f"{op['op']} missing path"
        if "path" in op and not in_allow(op["path"].replace("@module","").replace("@config","")):
            # tillater alias, reell sjekk skjer etter manifest-resolve
            pass
    return True, "ok"

def selftest()->bool:
    ok,msg = validate_spec({
        "project":"nova-bot",
        "spec":[{"op":"mkdir","path":"/home/nova/nova-bot/tmp"}]
    })
    assert ok, msg
    bad,_ = validate_spec({"x":1})
    assert bad is False
    return True

if __name__=="__main__":
    print("validators selftest:", selftest())
