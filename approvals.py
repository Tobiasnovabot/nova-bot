import os
# approvals.py
import pathlib, json, time

INBOX = pathlib.Path("/opt/guardian/inbox"); INBOX.mkdir(parents=True, exist_ok=True)

def enqueue(spec:dict)->str:
    jobid = f"job-{int(time.time())}"
    p = INBOX / f"{jobid}.await"
    p.write_text(json.dumps(spec, ensure_ascii=False, indent=2))
    return jobid

def mark_approved(jobid:str)->bool:
    src = INBOX / f"{jobid}.await"
    dst = INBOX / f"{jobid}.yaml"
    if not src.exists(): return False
    src.rename(dst); return True

def list_pending()->list[str]:
    return [p.stem for p in INBOX.glob("*.await")]

def selftest()->bool:
    job = enqueue({"t":1})
    assert job in list_pending()
    assert mark_approved(job) is True
    return True

if __name__=="__main__":
    print("approvals selftest:", selftest())
