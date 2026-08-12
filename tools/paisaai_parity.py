#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "parity_manifest.json").read_text())

SHARED = list(MANIFEST["shared_paths"])
PROD_ONLY = set(MANIFEST["production_only"])
REPLAY_ONLY = set(MANIFEST["replay_only"])
ACCOUNTING_SHA = MANIFEST["accounting_sha"]

CONTROLLER_FILES = {
    "tools/paisaai-parity",
    "tools/paisaai_parity.py",
    "tools/parity_manifest.json",
}


def run(*args, cwd=None, check=True, capture=False):
    return subprocess.run(
        args,
        cwd=cwd,
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def out(*args, cwd=None):
    return run(*args, cwd=cwd, capture=True).stdout.strip()


def repo_root():
    return Path(out("git", "rev-parse", "--show-toplevel")).resolve()


def branch_exists(root, name):
    return (
        subprocess.run(
            [
                "git",
                "show-ref",
                "--verify",
                "--quiet",
                f"refs/heads/{name}",
            ],
            cwd=root,
        ).returncode
        == 0
    )


def guess_branch(root, explicit, replay=False):
    if explicit:
        return explicit

    candidates = (
        [
            "replay-v2-architecture",
            "replay",
            "develop",
            "main",
            "master",
        ]
        if replay
        else [
            "develop",
            "production",
            "live",
            "main",
            "master",
        ]
    )

    for name in candidates:
        if branch_exists(root, name):
            return name

    return None


def current_branch(root):
    return out("git", "branch", "--show-current", cwd=root)


def path_exists_in_ref(root, ref, path):
    return (
        subprocess.run(
            [
                "git",
                "cat-file",
                "-e",
                f"{ref}:{path}",
            ],
            cwd=root,
        ).returncode
        == 0
    )


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def accounting_sha_ref(root, ref):
    proc = subprocess.run(
        [
            "git",
            "show",
            f"{ref}:scanner/trade_manager.py",
        ],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return hashlib.sha256(proc.stdout).hexdigest()


def verify_accounting_ref(root, ref):
    actual = accounting_sha_ref(root, ref)

    if actual != ACCOUNTING_SHA:
        raise SystemExit(
            "\n".join(
                [
                    f"STOP: accounting SHA mismatch on {ref}.",
                    f"Expected: {ACCOUNTING_SHA}",
                    f"Actual:   {actual}",
                ]
            )
        )

    print(f"ACCOUNTING SHA VERIFIED: {ref}")


def verify_accounting_worktree(root):
    path = root / "scanner/trade_manager.py"

    if not path.exists():
        raise SystemExit("STOP: scanner/trade_manager.py not found.")

    actual = sha256_file(path)

    if actual != ACCOUNTING_SHA:
        raise SystemExit(
            "\n".join(
                [
                    "STOP: working-tree accounting SHA mismatch.",
                    f"Expected: {ACCOUNTING_SHA}",
                    f"Actual:   {actual}",
                ]
            )
        )

    print("ACCOUNTING SHA VERIFIED: working tree")


def status_paths(root):
    raw = out(
        "git",
        "status",
        "--porcelain=v1",
        cwd=root,
    )

    paths = []

    for line in raw.splitlines():
        if len(line) < 4:
            continue

        path = line[3:]

        # Rename/copy status can contain "old -> new".
        if " -> " in path:
            old, new = path.split(" -> ", 1)
            paths.append(old)
            paths.append(new)
        else:
            paths.append(path)

    return paths


def dirty_nonshared(root):
    dirty = status_paths(root)

    allowed = set(SHARED) | CONTROLLER_FILES

    return sorted(
        path
        for path in dirty
        if path not in allowed
    )


def stash_existing_paths(root, paths, label):
    paths = [p for p in paths if p in status_paths(root)]

    if not paths:
        return None

    before = out(
        "git",
        "rev-parse",
        "-q",
        "--verify",
        "refs/stash",
        cwd=root,
    )

    cmd = [
        "git",
        "stash",
        "push",
        "-u",
        "-m",
        label,
        "--",
    ] + paths

    run(*cmd, cwd=root)

    after = out(
        "git",
        "rev-parse",
        "-q",
        "--verify",
        "refs/stash",
    )

    if before == after:
        raise SystemExit(
            "STOP: expected a safety stash but no new stash was created."
        )

    print("WORKTREE SNAPSHOT CREATED:", after[:12])
    print("Snapshot paths:")
    for p in paths:
        print(" ", p)

    return "stash@{0}"


def create_safety_tag(root, label):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"parity-{label}-{stamp}"
    tag = base
    n = 2

    while (
        subprocess.run(
            [
                "git",
                "rev-parse",
                "--verify",
                f"refs/tags/{tag}",
            ],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    ):
        tag = f"{base}-{n}"
        n += 1

    run(
        "git",
        "tag",
        "-m",
        f"PaisaAI parity safety checkpoint: {label}",
        tag,
        cwd=root,
    )

    print("SAFETY TAG:", tag)
    return tag


def shared_paths_existing_in_ref(root, ref):
    return [
        path
        for path in SHARED
        if path_exists_in_ref(root, ref, path)
    ]


def compile_shared(root):
    failures = []

    for path in SHARED:
        full = root / path

        if not full.exists():
            continue

        if not path.endswith(".py"):
            continue

        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "py_compile",
                str(full),
            ],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        if proc.returncode != 0:
            failures.append(
                f"{path}\n{proc.stdout.strip()}"
            )

    if failures:
        raise SystemExit(
            "STOP: shared-engine compilation failed:\n"
            + "\n\n".join(failures)
        )

    print("SHARED ENGINE COMPILE: OK")


def staged_paths(root):
    raw = out(
        "git",
        "diff",
        "--cached",
        "--name-only",
        cwd=root,
    )

    return [
        p for p in raw.splitlines()
        if p
    ]


def verify_staged_surface(root):
    changed = staged_paths(root)

    forbidden = (
        PROD_ONLY
        | REPLAY_ONLY
        | {"scanner/trade_manager.py"}
    )

    bad = [
        path
        for path in changed
        if path not in SHARED
    ]

    protected = [
        path
        for path in changed
        if path in forbidden
    ]

    if bad:
        raise SystemExit(
            "STOP: non-shared files staged:\n"
            + "\n".join(bad)
        )

    if protected:
        raise SystemExit(
            "STOP: protected files staged:\n"
            + "\n".join(protected)
        )

    print("SURFACE GUARD: OK")

    return changed


def restore_clean_index(root):
    run(
        "git",
        "reset",
        "--mixed",
        "HEAD",
        "--",
        *SHARED,
        cwd=root,
    )


def stage_source_committed_files(root, source):
    source_paths = shared_paths_existing_in_ref(root, source)

    changed = []

    for path in source_paths:
        run(
            "git",
            "checkout",
            source,
            "--",
            path,
            cwd=root,
        )
        changed.append(path)

    return changed


def clean_target_for_switch(root, target):
    # We deliberately refuse unrelated working-tree changes.
    dirty = dirty_nonshared(root)

    if dirty:
        raise SystemExit(
            "STOP: unrelated working-tree changes exist. "
            "Parity will not touch them:\n"
            + "\n".join(dirty)
        )

    if current_branch(root) != target:
        run(
            "git",
            "checkout",
            target,
            cwd=root,
        )


def apply_direction(root, source, target, label):
    if source == target:
        raise SystemExit(
            "STOP: source and target branches are identical."
        )

    original = current_branch(root)

    print("SOURCE:", source)
    print("TARGET:", target)
    print("CURRENT:", original)

    # Production is always checked before any branch movement.
    verify_accounting_ref(root, "develop")

    # Snapshot current shared work.
    #
    # If current == target:
    #   target dirty shared work is backed up before synchronization.
    #
    # If current == source:
    #   source dirty shared work is backed up and later promoted too.
    #
    # If neither:
    #   we refuse to guess which branch the dirty work belongs to.
    if original == target:
        stash_paths = [
            p
            for p in SHARED
            if path_exists_in_ref(root, source, p)
        ]
    elif original == source:
        stash_paths = list(SHARED)
    else:
        if status_paths(root):
            raise SystemExit(
                "STOP: current branch is neither source nor target "
                "and working tree is not clean."
            )
        stash_paths = []

    source_work_stash = None

    if stash_paths:
        source_work_stash = stash_existing_paths(
            root,
            stash_paths,
            f"parity-{label}-working-tree-backup",
        )

    # The target's current HEAD is now safe to checkpoint.
    if not branch_exists(root, target):
        raise SystemExit(
            f"STOP: target branch does not exist: {target}"
        )

    create_safety_tag(root, label)

    # Move to target if necessary.
    clean_target_for_switch(root, target)

    # Production must remain accounting-safe after branch switch.
    if target == "develop":
        verify_accounting_worktree(root)
    else:
        verify_accounting_ref(root, "develop")

    # Pull only shared files from the source's committed tree.
    source_paths = stage_source_committed_files(
        root,
        source,
    )

    # If the source branch was the original working branch,
    # reapply its captured shared working-tree changes on top
    # of the committed source snapshot.
    if original == source and source_work_stash:
        print(
            "APPLYING SOURCE WORKTREE SNAPSHOT:",
            source_work_stash,
        )

        proc = subprocess.run(
            [
                "git",
                "stash",
                "apply",
                source_work_stash,
            ],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        if proc.returncode != 0:
            # Keep stash intact for recovery.
            raise SystemExit(
                "STOP: source working-tree snapshot could not be "
                "applied safely.\n\n"
                + proc.stdout
                + "\nThe safety stash was NOT dropped."
            )

        print("SOURCE WORKTREE SNAPSHOT APPLIED.")

    # Stage only actual shared files that now exist.
    existing_shared = [
        p
        for p in SHARED
        if (root / p).exists()
    ]

    if existing_shared:
        run(
            "git",
            "add",
            "--",
            *existing_shared,
            cwd=root,
        )

    changed = verify_staged_surface(root)

    if not changed:
        print("NO SHARED DIFFERENCES. NOTHING TO SYNC.")
        return

    compile_shared(root)

    if target == "develop":
        verify_accounting_worktree(root)
    else:
        verify_accounting_ref(root, "develop")

    message = f"parity: sync shared engine {label}"

    run(
        "git",
        "commit",
        "-m",
        message,
        cwd=root,
    )

    print()
    print("========================================")
    print("PARITY SYNC COMPLETE")
    print("========================================")
    print(f"{source} -> {target}")
    print()
    print("Changed shared files:")
    for path in changed:
        print(" ", path)

    if source_work_stash:
        print()
        print("SOURCE WORKTREE BACKUP RETAINED:")
        print(" ", source_work_stash)

    print()
    print("Production accounting:")
    verify_accounting_ref(root, "develop")


def status(root, prod, replay):
    print("Production branch:", prod or "(not detected)")
    print("Replay branch:    ", replay or "(not detected)")
    print("Current branch:   ", current_branch(root))

    print()
    print("Mode: GUARDED WORKING-TREE BIDIRECTIONAL PARITY")
    print("Shared files are synchronized individually.")
    print("One-sided shared files are preserved.")
    print("Dirty shared work is snapshotted before branch movement.")
    print("Production accounting remains SHA-protected.")
    print("No protected production/replay surfaces cross.")

    print()
    print("Shared surface:")
    for path in SHARED:
        print(" ", path)

    print()
    print("Protected Production-only:")
    for path in sorted(PROD_ONLY):
        print(" ", path)

    print()
    print("Protected Replay-only:")
    for path in sorted(REPLAY_ONLY):
        print(" ", path)

    print()
    try:
        verify_accounting_ref(root, "develop")
    except SystemExit as exc:
        print(str(exc))

    print()
    print("Working-tree status:")
    dirty = status_paths(root)

    if dirty:
        for path in dirty:
            print(" ", path)
    else:
        print(" CLEAN")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "PaisaAI guarded bidirectional shared-engine "
            "parity controller"
        )
    )

    parser.add_argument(
        "command",
        choices=[
            "status",
            "production-to-replay",
            "replay-to-production",
        ],
    )

    parser.add_argument("--production")
    parser.add_argument("--replay")

    args = parser.parse_args()

    root = repo_root()

    prod = guess_branch(
        root,
        args.production,
        replay=False,
    )

    replay = guess_branch(
        root,
        args.replay,
        replay=True,
    )

    if args.command == "status":
        status(root, prod, replay)
        return

    if not prod or not replay:
        raise SystemExit(
            "STOP: could not detect both Production and Replay branches.\n"
            "Use --production NAME --replay NAME."
        )

    if args.command == "production-to-replay":
        apply_direction(
            root,
            prod,
            replay,
            "production-to-replay",
        )
    else:
        apply_direction(
            root,
            replay,
            prod,
            "replay-to-production",
        )


if __name__ == "__main__":
    main()
