#!/usr/bin/env python3
import argparse, hashlib, json, os, subprocess, sys, tempfile, shutil
from pathlib import Path
from datetime import datetime

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE/"parity_manifest.json").read_text())
SHARED = MANIFEST["shared_paths"]
PROD_ONLY = set(MANIFEST["production_only"])
REPLAY_ONLY = set(MANIFEST["replay_only"])
ACCOUNTING_SHA = MANIFEST["accounting_sha"]

def run(*args, cwd=None, check=True, capture=False):
    return subprocess.run(args, cwd=cwd, check=check, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.STDOUT if capture else None)

def out(*args, cwd=None):
    return run(*args, cwd=cwd, capture=True).stdout.strip()

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def repo_root():
    return Path(out("git","rev-parse","--show-toplevel")).resolve()

def branch_exists(name, root):
    return subprocess.run(["git","show-ref","--verify","--quiet",f"refs/heads/{name}"],cwd=root).returncode==0

def guess(root, explicit, replay):
    if explicit: return explicit
    candidates = (["replay-v2-architecture","replay","develop","main","master","production","live"]
                  if replay else ["production","live","develop","main","master"])
    for c in candidates:
        if branch_exists(c,root): return c
    return None

def clean(root):
    s=out("git","status","--porcelain",cwd=root)
    if s: raise SystemExit("STOP: working tree is not clean. Commit/stash first:\n"+s)

def verify_accounting(root):
    p=root/"scanner/trade_manager.py"
    if not p.exists(): raise SystemExit("STOP: scanner/trade_manager.py not found.")
    actual=sha(p)
    if actual != ACCOUNTING_SHA:
        raise SystemExit(f"STOP: accounting SHA mismatch.\nExpected: {ACCOUNTING_SHA}\nActual:   {actual}")
    print("ACCOUNTING SHA VERIFIED")

def backup(root, label):
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    tag=f"parity-{label}-{stamp}"
    run("git","tag",tag,cwd=root)
    print("SAFETY TAG:",tag)
    return tag

def branch_diff(root, source, target):
    # Content differences in the explicitly shared surface only.
    cmd=["git","diff","--binary",f"{target}..{source}","--"]+SHARED
    return subprocess.run(cmd,cwd=root,text=False,stdout=subprocess.PIPE,check=True).stdout

def apply_direction(root, source, target, label):
    if source==target: raise SystemExit("STOP: source and target branches are identical.")
    clean(root)
    # Checkout target only after all preflight checks.
    verify_accounting(root)
    patch=branch_diff(root,source,target)
    if not patch:
        print("NO SHARED DIFFERENCES. NOTHING TO SYNC.")
        return
    backup(root,label)
    run("git","checkout",target,cwd=root)
    try:
        verify_accounting(root)
        # Apply only shared paths. Production/replay-only files can never cross.
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(patch); patchfile=f.name
        try:
            run("git","apply","--index",patchfile,cwd=root)
        finally:
            os.unlink(patchfile)
        # Safety: ensure forbidden surfaces were not changed.
        changed=out("git","diff","--cached","--name-only",cwd=root).splitlines()
        forbidden = PROD_ONLY | REPLAY_ONLY | {"scanner/trade_manager.py"}
        bad=[x for x in changed if x in forbidden]
        if bad: raise SystemExit("STOP: forbidden files changed: "+", ".join(bad))
        verify_accounting(root)
        # Compile all shared Python modules.
        for p in SHARED:
            if p.endswith(".py") and (root/p).exists():
                run(sys.executable,"-m","py_compile",str(root/p),cwd=root)
        run("git","commit","-m",f"parity: sync shared engine {label}",cwd=root)
        print("SYNC COMPLETE:",source,"->",target)
        print("Changed shared files:")
        print("\n".join(changed) if changed else "(none)")
    except Exception:
        subprocess.run(["git","reset","--hard"],cwd=root)
        raise

def status(root, prod, replay):
    print("Production branch:",prod or "(not detected)")
    print("Replay branch:    ",replay or "(not detected)")
    print("Current branch:   ",out("git","branch","--show-current",cwd=root))
    print("\nShared surface:")
    for p in SHARED: print(" ",p)
    print("\nProtected Production-only:")
    for p in sorted(PROD_ONLY): print(" ",p)
    print("\nProtected Replay-only:")
    for p in sorted(REPLAY_ONLY): print(" ",p)
    try: verify_accounting(root)
    except SystemExit as e: print(str(e))

def main():
    ap=argparse.ArgumentParser(description="PaisaAI guarded bidirectional shared-engine parity controller")
    ap.add_argument("command",choices=["status","production-to-replay","replay-to-production"])
    ap.add_argument("--production")
    ap.add_argument("--replay")
    args=ap.parse_args()
    root=repo_root()
    prod=guess(root,args.production,False)
    rep=guess(root,args.replay,True)
    if args.command=="status":
        status(root,prod,rep); return
    if not prod or not rep:
        raise SystemExit("STOP: could not detect both Production and Replay branches. Use --production NAME --replay NAME.")
    if args.command=="production-to-replay":
        apply_direction(root,prod,rep,"production-to-replay")
    else:
        # Promotion is guarded; it never auto-runs. User explicitly invokes this command.
        apply_direction(root,rep,prod,"replay-to-production")

if __name__=="__main__":
    main()
