import os
# diff.py
import difflib, pathlib

def unified_diff_str(a:str, b:str, path:str)->str:
    return "".join(difflib.unified_diff(
        a.splitlines(True), b.splitlines(True),
        fromfile=path+" (old)", tofile=path+" (new)", lineterm=""
    ))

def selftest()->bool:
    d = unified_diff_str("x\n", "y\n", "t.txt")
    assert "--- t.txt (old)" in d and "+++ t.txt (new)" in d
    return True

if __name__=="__main__":
    print("diff selftest:", selftest())
