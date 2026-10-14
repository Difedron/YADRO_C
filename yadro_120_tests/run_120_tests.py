#!/usr/bin/env python3
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MANIFEST=json.loads((ROOT/"manifest.json").read_text(encoding="utf-8"))
TIMEOUT=60

def run(cmd,cwd=None):
    try:
        return subprocess.run(cmd,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=TIMEOUT)
    except subprocess.TimeoutExpired as e:
        return None

def main():
    if len(sys.argv)!=2:
        print(f"Usage: {sys.argv[0]} /path/to/solution",file=sys.stderr); return 2
    exe=Path(sys.argv[1]).resolve()
    if not exe.exists(): print(f"Executable not found: {exe}",file=sys.stderr); return 2
    passed=0; failed=[]
    with tempfile.TemporaryDirectory(prefix="yadro120_") as td:
        tmp=Path(td)
        # use test 001 as canonical valid source/expected for CLI special cases
        base_in=ROOT/"cases/001_scalar_zero.in"
        base_out=ROOT/"cases/001_scalar_zero.out"
        for idx,t in enumerate(MANIFEST,1):
            name=t["name"]; kind=t["kind"]
            ok=False; detail=""
            if kind=="valid":
                out=tmp/f"{name}.out"
                p=run([str(exe),"-i",str(ROOT/t["input_file"]),"-o",str(out)])
                if p is None: detail="TIMEOUT"
                elif p.returncode!=0: detail=f"rc={p.returncode}, stderr={p.stderr.decode(errors='replace').strip()}"
                elif not out.exists(): detail="output not created"
                elif out.read_bytes()!=(ROOT/t["output_file"]).read_bytes(): detail="binary output mismatch"
                else: ok=True
            elif kind=="invalid_input":
                out=tmp/f"{name}.out"
                p=run([str(exe),"-i",str(ROOT/t["input_file"]),"-o",str(out)])
                if p is None: detail="TIMEOUT"
                elif p.returncode==t["expected_rc"]: ok=True
                else: detail=f"expected rc={t['expected_rc']}, got {p.returncode}; stderr={p.stderr.decode(errors='replace').strip()}"
            else:
                mode=t["mode"]
                if mode=="no_args": cmd=[str(exe)]; cwd=None
                elif mode=="only_i": cmd=[str(exe),"-i",str(base_in)]; cwd=None
                elif mode=="only_o": cmd=[str(exe),"-o",str(tmp/"x.out")]; cwd=None
                elif mode=="flag_as_name": cmd=[str(exe),"-i","-o",str(tmp/"x.out")]; cwd=None
                elif mode=="missing_input": cmd=[str(exe),"-i",str(tmp/"does_not_exist.bin"),"-o",str(tmp/"x.out")]; cwd=None
                elif mode=="missing_output_dir": cmd=[str(exe),"-i",str(base_in),"-o",str(tmp/"no_such_dir"/"x.out")]; cwd=None
                elif mode=="leading_dash":
                    wd=tmp/"dash"; wd.mkdir(exist_ok=True)
                    shutil.copy2(base_in,wd/"-input.bin")
                    cmd=[str(exe),"-i","-input.bin","-o","-output.bin"]; cwd=wd
                elif mode=="same_path":
                    same=tmp/"same.bin"; shutil.copy2(base_in,same)
                    cmd=[str(exe),"-i",str(same),"-o",str(same)]; cwd=None
                p=run(cmd,cwd=cwd)
                if p is None: detail="TIMEOUT"
                elif p.returncode!=t["expected_rc"]: detail=f"expected rc={t['expected_rc']}, got {p.returncode}; stderr={p.stderr.decode(errors='replace').strip()}"
                elif mode=="leading_dash" and (cwd/"-output.bin").read_bytes()!=base_out.read_bytes(): detail="leading-dash output mismatch"
                elif mode=="same_path" and Path(cmd[-1]).read_bytes()!=base_out.read_bytes(): detail="same-path output mismatch"
                else: ok=True
            if ok:
                passed+=1; print(f"PASS {idx:03d}: {name}")
            else:
                failed.append((idx,name,detail)); print(f"FAIL {idx:03d}: {name}: {detail}")
    print(f"\nPassed {passed}/120 tests")
    if failed:
        print("Failures:")
        for i,n,d in failed: print(f"  {i:03d} {n}: {d}")
        return 1
    return 0

if __name__=="__main__": raise SystemExit(main())
