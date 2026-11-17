#!/usr/bin/env python3
"""Install the ASE harness into an existing Git repository without overwriting files.

Usage:
  python3 install.py /path/to/repo            # local footprint (default): excluded from Git
  python3 install.py /path/to/repo --versioned
  python3 install.py /path/to/repo --dry-run
  python3 install.py /path/to/repo --uninstall  # removes unchanged installed files
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
INCLUDE = [
    "AGENTS.md",
    ".agents",
    ".github/agents",
    ".github/instructions",
    "project-memory",
    "templates",
    "scripts/next-id.py",
    "scripts/append-task-log.py",
    "scripts/build-traceability.py",
]
MANIFEST = ".agents/.ase-install.json"
FALLBACK_RULES = ".agents/AGENTS.md"
POINTER = ".github/instructions/ase.instructions.md"
BEGIN = "# >>> ASE harness (local) >>>"
END = "# <<< ASE harness (local) <<<"
POINTER_TEXT = """---
description: "ASE harness rules for this repository. Read before any /ase-* command or ASE agent work."
applyTo: "**"
---

This repository uses the ASE harness. The ASE global rules are in `.agents/AGENTS.md` because the repository already has its own root `AGENTS.md`. Read `.agents/AGENTS.md` before running an ASE skill or acting as an ASE agent; the repository's `AGENTS.md` still applies to the code.
"""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files() -> list[Path]:
    files: list[Path] = []
    for item in INCLUDE:
        path = SOURCE / item
        candidates = sorted(path.rglob("*")) if path.is_dir() else [path]
        for file in candidates:
            if file.is_file() and "__pycache__" not in file.parts:
                files.append(file.relative_to(SOURCE))
    return files


def git_root(target: Path) -> Path:
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=target,
                             capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.exit(f"error: {target} is not inside a Git repository")
    root = Path(out).resolve()
    if root != target.resolve():
        sys.exit(f"error: run against the repository root: {root}")
    return root


def exclude_file(root: Path) -> Path:
    out = subprocess.run(["git", "rev-parse", "--git-path", "info/exclude"], cwd=root,
                         capture_output=True, text=True, check=True).stdout.strip()
    path = Path(out)
    return path if path.is_absolute() else root / path


def write_exclude(root: Path, paths: list[str]) -> None:
    path = exclude_file(root)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if BEGIN in text:
        before, _, rest = text.partition(BEGIN)
        _, _, after = rest.partition(END)
        text = before.rstrip("\n") + ("\n" if before.strip() else "") + after.lstrip("\n")
    if paths:
        block = "\n".join([BEGIN, *sorted(set(paths)), "graphify-out/", END]) + "\n"
        text = (text.rstrip("\n") + "\n\n" if text.strip() else "") + block
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def install(root: Path, versioned: bool, dry_run: bool) -> int:
    manifest_path = root / MANIFEST
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"files": {}}
    installed: dict[str, str] = dict(previous["files"])
    skipped: list[str] = []
    agents_conflict = False
    for rel in source_files():
        dest_rel = rel.as_posix()
        if dest_rel == "AGENTS.md" and (root / "AGENTS.md").exists() and "AGENTS.md" not in installed:
            agents_conflict = True
            dest_rel = FALLBACK_RULES
        dest = root / dest_rel
        if dest.exists():
            if dest_rel not in installed:
                skipped.append(dest_rel)
            continue
        print(f"  + {dest_rel}")
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((SOURCE / rel).read_bytes())
            dest.chmod((SOURCE / rel).stat().st_mode)
            installed[dest_rel] = digest(dest)
    if agents_conflict and not (root / POINTER).exists():
        print(f"  + {POINTER}  (existing AGENTS.md kept; ASE rules in {FALLBACK_RULES})")
        if not dry_run:
            (root / POINTER).parent.mkdir(parents=True, exist_ok=True)
            (root / POINTER).write_text(POINTER_TEXT, encoding="utf-8")
            installed[POINTER] = digest(root / POINTER)
    for rel in skipped:
        print(f"  = {rel}  (already exists, not overwritten)")
    if dry_run:
        print("dry run: nothing written")
        return 0
    installed[MANIFEST] = ""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"versioned": versioned, "files": installed}, indent=2) + "\n")
    if not versioned:
        write_exclude(root, ["/" + p for p in installed])
        print(f"ASE files excluded from Git via {exclude_file(root)}")
    print("Done. Open the repository in VS Code, select the 'ASE Lead' agent and run /ase-adopt.")
    return 0


def uninstall(root: Path) -> int:
    manifest_path = root / MANIFEST
    if not manifest_path.exists():
        sys.exit("error: no ASE installation manifest found")
    data = json.loads(manifest_path.read_text())
    kept = []
    for rel, sha in data["files"].items():
        path = root / rel
        if not path.exists() or rel == MANIFEST:
            continue
        if sha and digest(path) == sha:
            path.unlink()
        else:
            kept.append(rel)
    manifest_path.unlink()
    for rel in sorted({str(Path(r).parent) for r in data["files"]}, key=len, reverse=True):
        d = root / rel
        while d != root and d.is_dir() and not any(d.iterdir()):
            d.rmdir()
            d = d.parent
    write_exclude(root, [])
    for rel in kept:
        print(f"  kept (modified by you): {rel}")
    print("ASE removed. Files you changed (e.g. Project Memory) were kept.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", type=Path)
    parser.add_argument("--versioned", action="store_true", help="do not exclude ASE files from Git")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    root = git_root(args.target)
    if (root / "install.py").resolve() == Path(__file__).resolve():
        sys.exit("error: target is the ASE template itself")
    return uninstall(root) if args.uninstall else install(root, args.versioned, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
