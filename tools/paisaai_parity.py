#!/usr/bin/env python3
import argparse, hashlib, json, shutil, subprocess, sys, tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(subprocess.check_output(["git","rev-parse","--show-toplevel"], text=True).strip()).resolve()
HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "paisaai_parity_manifest.json").read_text())
SHARED = tuple(MANIFEST["shared_paths"])
PROD_ONLY = frozenset(MANIFEST["production_only"])
REPLAY_ONLY = frozenset(MANIFEST["replay_only"])
ACCOUNTING_SHA = MANIFEST["accounting_sha"]

def run(args, check=True, capture=False):
    return subprocess.run(args, cwd=ROOT, check=check, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None)

def out(*args): return run(list(args), capture=True).stdout.strip()
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p):
    h=hashlib.sha256();
    with open(p,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def branch_exists(name):
    return run(["git","show-ref","--verify","--quiet",f"refs/heads/{name}"],check=False).returncode==0

def detect(explicit,replay):
    if explicit: return explicit
    names=(['replay-v2-architecture','replay','develop','main','master','production','live'] if replay else ['develop','production','live','main','master'])
    return next((n for n in names if branch_exists(n)),None)

def verify_accounting_worktree():
    p=ROOT/'scanner/trade_manager.py'
    if not p.is_file(): raise SystemExit('STOP: scanner/trade_manager.py missing')
    actual=sha_file(p)
    if actual!=ACCOUNTING_SHA: raise SystemExit(f'STOP: accounting SHA mismatch\nExpected: {ACCOUNTING_SHA}\nActual:   {actual}')
    print('ACCOUNTING SHA VERIFIED')

def verify_accounting_branch(branch):
    try: b=run(['git','show',f'{branch}:scanner/trade_manager.py'],capture=True).stdout.encode()
    except subprocess.CalledProcessError: raise SystemExit(f'STOP: {branch} missing scanner/trade_manager.py')
    actual=sha_bytes(b)
    if actual!=ACCOUNTING_SHA: raise SystemExit(f'STOP: accounting SHA mismatch on {branch}\nExpected: {ACCOUNTING_SHA}\nActual:   {actual}')
    print(f'ACCOUNTING SHA VERIFIED: {branch}')

def tag(label):
    t=f'parity-v4-{label}-{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    run(['git','tag',t]); print('SAFETY TAG:',t); return t

def snapshot_shared():
    tmp=Path(tempfile.mkdtemp(prefix='paisaai-parity-v4-')); m={}
    for rel in SHARED:
        src=ROOT/rel
        if src.is_file():
            dst=tmp/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst); m[rel]=True
        else: m[rel]=False
    return tmp,m

def restore_shared(tmp,m):
    for rel in SHARED:
        dst=ROOT/rel
        if m[rel]:
            src=tmp/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
        elif dst.is_file(): dst.unlink()

def compile_shared():
    for rel in SHARED:
        p=ROOT/rel
        if p.is_file() and p.suffix=='.py': run([sys.executable,'-m','py_compile',str(p)])

def forbidden_staged():
    changed=out('git','diff','--cached','--name-only').splitlines()
    bad=[p for p in changed if p in PROD_ONLY or p in REPLAY_ONLY or p=='scanner/trade_manager.py']
    if bad: raise SystemExit('STOP: protected file staged: '+', '.join(bad))
    return changed

def apply(source,target,production,label):
    if out('git','branch','--show-current')!=source: raise SystemExit(f'STOP: checkout {source} first')
    if source==production: verify_accounting_worktree()
    if target==production: verify_accounting_branch(target)
    # Target must be clean before branch movement. Source dirty shared work is handled by stash.
    target_status=run(['git','status','--porcelain'],check=False,capture=True).stdout
    tmp,m=snapshot_shared(); dirty=bool(target_status); stash=False
    try:
        safety=tag(label)
        if dirty:
            run(['git','stash','push','-u','-m',f'parity-v4-preserve-{label}']); stash=True
            print('SOURCE WORKTREE SNAPSHOTTED')
        run(['git','checkout',target])
        if target==production: verify_accounting_worktree()
        restore_shared(tmp,m)
        stage_paths = []
        for rel in SHARED:
            tracked = run(['git','ls-files','--error-unmatch','--',rel], check=False, capture=True).returncode == 0
            if (ROOT / rel).exists() or tracked:
                stage_paths.append(rel)
        if stage_paths:
            run(['git','add','-A','--',*stage_paths])
        changed=forbidden_staged()
        if changed:
            compile_shared()
            if target==production: verify_accounting_worktree()
            run(['git','commit','-m',f'parity: sync shared engine {label}'])
            print(f'PARITY SYNC COMPLETE: {source} -> {target}')
            print('\n'.join('  '+x for x in changed))
        else: print('NO SHARED DIFFERENCES. NOTHING TO SYNC.')
        if target==production: verify_accounting_worktree()
        print('CURRENT BRANCH:',out('git','branch','--show-current'))
        print('SAFETY TAG:',safety)
    except Exception:
        run(['git','reset','--hard'],check=False); run(['git','checkout',source],check=False)
        raise
    finally:
        if stash:
            # Stash belongs to source and is intentionally retained; source was dirty before switch.
            print('SOURCE WORKTREE STASH RETAINED: run git stash list if needed.')
        shutil.rmtree(tmp,ignore_errors=True)

def status(prod,replay):
    print('Production branch:',prod or '(not detected)')
    print('Replay branch:    ',replay or '(not detected)')
    print('Current branch:   ',out('git','branch','--show-current'))
    print('\nMode: GUARDED BIDIRECTIONAL PARITY V4 — STAYS ON TARGET')
    print('Shared surface:')
    for p in SHARED: print(' ',p)
    print('Protected Production-only:')
    for p in sorted(PROD_ONLY): print(' ',p)
    print('Protected Replay-only:')
    for p in sorted(REPLAY_ONLY): print(' ',p)
    if prod:
        try: verify_accounting_branch(prod)
        except SystemExit as e: print(str(e))
    print('Working-tree status:')
    s=out('git','status','--short'); print(' CLEAN' if not s else s)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('command',choices=['status','production-to-replay','replay-to-production']); ap.add_argument('--production'); ap.add_argument('--replay'); a=ap.parse_args()
    prod=detect(a.production,False); replay=detect(a.replay,True)
    if a.command=='status': status(prod,replay); return
    if not prod or not replay: raise SystemExit('STOP: could not detect Production and Replay branches')
    apply(prod,replay,prod,'production-to-replay') if a.command=='production-to-replay' else apply(replay,prod,prod,'replay-to-production')
if __name__=='__main__': main()
