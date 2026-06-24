#!/usr/bin/env python3
"""Back up Simon's active Compound Engineering plugin cache into his fork."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_CACHE_ROOT = Path(
    "/home/simon/.codex/plugins/cache/personal/compound-engineering/3.13.1"
)
DEFAULT_REPO = Path("/home/simon/plugins/compound-engineering")

BACKUP_PATHS = [
    Path("AGENTS.md"),
    Path("package.json"),
    Path("skills"),
    Path("src/release"),
    Path("scripts/release"),
    Path(".opencode"),
    Path(".pi"),
    Path(".agents/plugins/marketplace.json"),
    Path(".agy/plugin.json"),
    Path(".claude-plugin/marketplace.json"),
    Path(".claude-plugin/plugin.json"),
    Path(".codex-plugin/plugin.json"),
    Path(".cursor-plugin/marketplace.json"),
    Path(".cursor-plugin/plugin.json"),
]

IGNORE_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
}
IGNORE_FILES = {".DS_Store"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def is_ignored_file(rel: Path) -> bool:
    return (
        any(part in IGNORE_DIRS for part in rel.parts)
        or rel.name in IGNORE_FILES
        or rel.name.endswith(".pyc")
    )


def iter_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if root.is_file():
        return [Path(root.name)]
    return sorted(
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and not is_ignored_file(path.relative_to(root))
    )


def backup_labels_for(root: Path) -> dict[str, Path]:
    labels: dict[str, Path] = {}
    for rel in BACKUP_PATHS:
        src = root / rel
        if not src.exists():
            continue
        if src.is_file():
            labels[rel.as_posix()] = src
            continue
        for child in iter_files(src):
            labels[f"{rel.as_posix()}/{child.as_posix()}"] = src / child
    return labels


def require_paths(cache_root: Path, repo: Path) -> None:
    missing = []
    if not cache_root.exists():
        missing.append(str(cache_root))
    if not repo.exists():
        missing.append(str(repo))
    for rel in BACKUP_PATHS:
        if not (cache_root / rel).exists():
            missing.append(str(cache_root / rel))
    if missing:
        raise FileNotFoundError("Missing required paths:\n" + "\n".join(missing))


def compare_cache_to_fork(cache_root: Path, repo: Path) -> dict[str, list[str]]:
    expected = backup_labels_for(cache_root)
    actual = backup_labels_for(repo)

    changed: list[str] = []
    missing: list[str] = []
    for label, cache_path in expected.items():
        repo_path = repo / label
        if not repo_path.exists():
            missing.append(label)
            continue
        if sha256_file(cache_path) != sha256_file(repo_path):
            changed.append(label)

    stale = sorted(set(actual) - set(expected))
    return {
        "changed": sorted(changed),
        "missing": sorted(missing),
        "stale": stale,
    }


def has_drift(drift: dict[str, list[str]]) -> bool:
    return any(drift[key] for key in ("changed", "missing", "stale"))


def copy_path_clean(src: Path, dest: Path) -> None:
    if src.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return

    if dest.exists():
        shutil.rmtree(dest)

    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {
            name
            for name in names
            if name in IGNORE_DIRS or name in IGNORE_FILES or name.endswith(".pyc")
        }

    shutil.copytree(src, dest, ignore=ignore)


def apply_backup(cache_root: Path, repo: Path) -> None:
    for rel in BACKUP_PATHS:
        copy_path_clean(cache_root / rel, repo / rel)


def run_git(repo: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return result.stdout.rstrip("\n")


def remote_status(repo: Path) -> tuple[str, str]:
    branch_lines = run_git(repo, ["status", "--short", "--branch"]).splitlines()
    branch_line = branch_lines[0] if branch_lines else "unknown"
    dirty = bool(run_git(repo, ["status", "--porcelain"]))
    if dirty:
        return "working_tree_dirty", branch_line
    if "ahead" in branch_line and "behind" in branch_line:
        return "diverged", branch_line
    if "ahead" in branch_line:
        return "local_ahead_remote", branch_line
    if "behind" in branch_line:
        return "local_behind_remote", branch_line
    return "in_sync", branch_line


def scoped_status(repo: Path) -> str:
    args = ["status", "--short", "--branch", "--", *[path.as_posix() for path in BACKUP_PATHS]]
    return run_git(repo, args)


def changed_scoped_files(repo: Path) -> list[str]:
    output = run_git(repo, ["status", "--porcelain", "--", *[p.as_posix() for p in BACKUP_PATHS]])
    files: list[str] = []
    for line in output.splitlines():
        if not line:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return sorted(files)


def validate(cache_root: Path, repo: Path) -> tuple[bool, list[str]]:
    drift = compare_cache_to_fork(cache_root, repo)
    errors: list[str] = []
    for key in ("changed", "missing", "stale"):
        for value in drift[key]:
            errors.append(f"{key}: {value}")
    return not errors, errors


def action_needed(cache_root: Path, repo: Path) -> str:
    drift = compare_cache_to_fork(cache_root, repo)
    remote_state, branch_line = remote_status(repo)
    if "behind" in branch_line and "ahead" in branch_line:
        return "resolve_remote_first"
    if "behind" in branch_line:
        return "resolve_remote_first"
    if has_drift(drift):
        return "apply_backup"
    if changed_scoped_files(repo) or "ahead" in branch_line:
        return "commit_push"
    if remote_state == "working_tree_dirty":
        return "unrelated_dirty"
    return "none"


def print_plan(cache_root: Path, repo: Path) -> None:
    print("bundle=compound-engineering-personal")
    print(f"active_cache={cache_root}")
    print(f"destination_fork={repo}")
    print(f"backup_paths={len(BACKUP_PATHS)}")
    for rel in BACKUP_PATHS:
        print(f"  - {rel.as_posix()}")


def print_drift_report(cache_root: Path, repo: Path) -> None:
    drift = compare_cache_to_fork(cache_root, repo)
    remote_state, branch_line = remote_status(repo)
    action = action_needed(cache_root, repo)
    cache_manifest = cache_root / "skills/shared/ce-bundle.json"
    repo_manifest = repo / "skills/shared/ce-bundle.json"
    if cache_manifest.exists() and repo_manifest.exists():
        manifest_state = (
            "checksum_match"
            if sha256_file(cache_manifest) == sha256_file(repo_manifest)
            else "checksum_mismatch"
        )
    elif cache_manifest.exists() or repo_manifest.exists():
        manifest_state = "missing_one_side"
    else:
        manifest_state = "missing_both"

    print(f"remote_status={remote_state}")
    print(f"remote_branch={branch_line}")
    print(f"cache_vs_fork={'drift_detected' if has_drift(drift) else 'in_sync'}")
    print(f"bundle_manifest={manifest_state}")
    print(f"action_needed={action}")
    if action in {"apply_backup", "commit_push"}:
        print(
            "suggested_commit_message="
            "chore(skills): backup Compound Engineering personal plugin patches"
        )
        print(
            "decision_question="
            "Soll ich diesen CE-Backup-Stand jetzt anwenden, validieren, committen und nach GitHub pushen?"
        )
    if action == "resolve_remote_first":
        print("warning=local fork is behind or diverged; resolve remote state before backup")
    if action == "unrelated_dirty":
        print("warning=working tree has changes outside the CE backup scope")

    for key, title in [
        ("changed", "changed_files"),
        ("missing", "missing_in_fork"),
        ("stale", "stale_in_fork"),
    ]:
        values = drift[key]
        print(f"{title}={len(values)}")
        for value in values[:80]:
            print(f"  - {value}")
        if len(values) > 80:
            print(f"  ... {len(values) - 80} more")

    changed_files = changed_scoped_files(repo)
    print(f"git_scoped_changed_files={len(changed_files)}")
    for value in changed_files[:80]:
        print(f"  - {value}")
    if len(changed_files) > 80:
        print(f"  ... {len(changed_files) - 80} more")


def print_manifest(cache_root: Path, repo: Path) -> None:
    labels = backup_labels_for(cache_root)
    manifest = {
        "$schema": "sanctum-ce-skill-backup-v1",
        "name": "compound-engineering-personal",
        "source": str(cache_root),
        "destination": str(repo),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "files": {
            label: hashlib.sha256(read_text(path).encode("utf-8")).hexdigest()
            if path.suffix in {".md", ".json", ".yaml", ".yml", ".txt", ".ts", ".js", ".py"}
            else sha256_file(path)
            for label, path in labels.items()
        },
    }
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["preview", "apply", "status", "manifest"])
    parser.add_argument("--cache-root", type=Path, default=DEFAULT_CACHE_ROOT)
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    cache_root = args.cache_root.expanduser().resolve()
    repo = args.repo.expanduser().resolve()

    try:
        require_paths(cache_root, repo)
        if args.command == "preview":
            print_plan(cache_root, repo)
            print("\nbackup_status:")
            print_drift_report(cache_root, repo)
            print("\nrepo_status:")
            print(scoped_status(repo) or "clean for backup scope")
            return 0
        if args.command == "apply":
            print_plan(cache_root, repo)
            apply_backup(cache_root, repo)
            ok, errors = validate(cache_root, repo)
            print("\nvalidation=" + ("ok" if ok else "failed"))
            for error in errors:
                print(f"  - {error}")
            print("\nrepo_status:")
            print(scoped_status(repo) or "clean for backup scope")
            return 0 if ok else 1
        if args.command == "status":
            ok, errors = validate(cache_root, repo)
            print("validation=" + ("ok" if ok else "failed"))
            for error in errors[:80]:
                print(f"  - {error}")
            if len(errors) > 80:
                print(f"  ... {len(errors) - 80} more")
            print("\nbackup_status:")
            print_drift_report(cache_root, repo)
            print("\nrepo_status:")
            print(scoped_status(repo) or "clean for backup scope")
            return 0 if ok else 1
        if args.command == "manifest":
            print_manifest(cache_root, repo)
            return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
