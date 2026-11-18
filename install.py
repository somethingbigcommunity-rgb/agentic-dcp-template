#!/usr/bin/env python3
"""Install the ASE harness into an existing Git repository without overwriting files.

Default layout (Option 1A — Encapsulated `.ase/` + Root IDE Hooks):
  - Root IDE discovery hooks: `.agents/`, `.github/agents/`, `.github/instructions/`, `AGENTS.md` (or `.agents/AGENTS.md`)
  - Encapsulated ASE workspace: `.ase/project-memory/`, `.ase/artifacts/`, `.ase/scripts/`, `.ase/templates/`

Usage:
  python3 install.py /path/to/repo                  # encapsulated .ase/ layout (default), excluded from Git
  python3 install.py /path/to/repo --flat           # legacy flat root layout
  python3 install.py /path/to/repo --upgrade        # upgrade unmodified ASE files
  python3 install.py /path/to/repo --verify-layout  # check .ase/ encapsulation and detect stray template clones
  python3 install.py /path/to/repo --versioned
  python3 install.py /path/to/repo --dry-run
  python3 install.py /path/to/repo --uninstall      # removes unchanged installed files
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
    "artifacts",
    "templates",
    "scripts/next-id.py",
    "scripts/append-task-log.py",
    "scripts/build-traceability.py",
    "scripts/verify-external-clean.py",
    "scripts/sync-plugin.py",
    "scripts/build-stakeholder-pdf.py",
]
ENCAPSULATED_PREFIX = ".ase"
ENCAPSULATED_ROOTS = ("project-memory", "artifacts", "templates", "scripts")
MANIFEST = ".agents/.ase-install.json"
FALLBACK_RULES = ".agents/AGENTS.md"
POINTER = ".github/instructions/ase.instructions.md"
AGY_POINTER = ".agents/rules/ase.md"
BEGIN = "# >>> ASE harness (local) >>>"
END = "# <<< ASE harness (local) <<<"
POINTER_TEXT = """---
description: "ASE harness rules for this repository. Read before any /ase-* command or ASE agent work."
applyTo: "**"
---

This repository uses the ASE harness. The ASE global rules are in `.agents/AGENTS.md` because the repository already has its own root `AGENTS.md`. Read `.agents/AGENTS.md` before running an ASE skill or acting as an ASE agent; the repository's `AGENTS.md` still applies to the code.
"""
AGY_POINTER_TEXT = """---
trigger: always_on
description: "ASE harness rules for this repository. Read before any /ase-* command or ASE agent work."
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


def map_dest_rel(rel: Path, encapsulated: bool) -> str:
    posix = rel.as_posix()
    if encapsulated and rel.parts and rel.parts[0] in ENCAPSULATED_ROOTS:
        return f"{ENCAPSULATED_PREFIX}/{posix}"
    return posix


def git_root(target: Path, allow_no_git: bool = False) -> tuple[Path, bool]:
    if not target.is_dir():
        sys.exit(f"error: {target} is not a directory")
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=target,
                             capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        if allow_no_git:
            return target.resolve(), False
        sys.exit(f"error: {target} is not inside a Git repository (pass --no-git to install anyway)")
    root = Path(out).resolve()
    if root != target.resolve():
        sys.exit(f"error: run against the repository root: {root}")
    return root, True


def exclude_file(root: Path) -> Path:
    out = subprocess.run(["git", "rev-parse", "--git-path", "info/exclude"], cwd=root,
                         capture_output=True, text=True, check=True).stdout.strip()
    path = Path(out)
    return path if path.is_absolute() else root / path


def write_exclude(root: Path, paths: list[str]) -> bool:
    path = exclude_file(root)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if BEGIN in text:
        before, _, rest = text.partition(BEGIN)
        _, _, after = rest.partition(END)
        text = before.rstrip("\n") + ("\n" if before.strip() else "") + after.lstrip("\n")
    if paths:
        block = "\n".join([BEGIN, *sorted(set(paths)), "graphify-out/", END]) + "\n"
        text = (text.rstrip("\n") + "\n\n" if text.strip() else "") + block
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return True
    except OSError as exc:
        print(f"warning: could not update {path} ({exc}); run with --versioned or outside sandbox to update Git exclude", file=sys.stderr)
        return False


def verify_layout(root: Path) -> int:
    errors: list[str] = []
    if not (root / ".agents" / "agents" / "ase-lead.md").is_file():
        errors.append("missing root .agents/agents/ase-lead.md (Antigravity entry point)")
    has_encapsulated = (root / ".ase" / "project-memory" / "state" / "PROJECT_STATE.md").is_file()
    has_flat = (root / "project-memory" / "state" / "PROJECT_STATE.md").is_file()
    if not has_encapsulated and not has_flat:
        errors.append("missing Project Memory (.ase/project-memory/ or project-memory/)")

    # Detect stray template clones inside the workspace (excluding .ase/template and implementazione/dcp-template)
    for cand in root.rglob("install.py"):
        rel = cand.relative_to(root).as_posix()
        if rel in ("install.py", ".ase/template/install.py", "implementazione/dcp-template/install.py"):
            continue
        if (cand.parent / "project-memory").is_dir() and (cand.parent / ".agents").is_dir():
            errors.append(
                f"stray template clone detected at '{cand.parent.relative_to(root)}'; "
                f"move it to '.ase/template/' or outside the project workspace so it does not pollute the repository"
            )

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1

    layout_mode = "encapsulated (.ase/)" if has_encapsulated else "flat (root)"
    print(f"PASS: verified ASE workspace layout ({layout_mode}) at {root}")
    return 0


def install(
    root: Path,
    versioned: bool,
    dry_run: bool,
    has_git: bool = True,
    upgrade: bool = False,
    encapsulated: bool = True,
) -> int:
    manifest_path = root / MANIFEST
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"files": {}}
    if manifest_path.exists() and "versioned" in previous and not versioned:
        versioned = bool(previous["versioned"])
    if manifest_path.exists() and "encapsulated" in previous:
        encapsulated = bool(previous["encapsulated"])
    elif manifest_path.exists() and any(k.startswith("project-memory/") for k in previous.get("files", {})):
        encapsulated = False

    installed: dict[str, str] = dict(previous["files"])
    skipped: list[str] = []
    agents_conflict = False
    for rel in source_files():
        dest_rel = map_dest_rel(rel, encapsulated)
        if dest_rel == "AGENTS.md" and (root / "AGENTS.md").exists() and "AGENTS.md" not in installed:
            if (root / FALLBACK_RULES).exists() or not upgrade:
                agents_conflict = True
                dest_rel = FALLBACK_RULES
        dest = root / dest_rel
        src_file = SOURCE / rel
        if dest.exists():
            if upgrade and dest_rel in installed and installed[dest_rel]:
                current_sha = digest(dest)
                new_sha = digest(src_file)
                if current_sha == installed[dest_rel]:
                    if current_sha != new_sha:
                        print(f"  ~ {dest_rel}  (upgraded)")
                        if not dry_run:
                            dest.write_bytes(src_file.read_bytes())
                            dest.chmod(src_file.stat().st_mode)
                            installed[dest_rel] = digest(dest)
                    continue
                else:
                    skipped.append(f"{dest_rel} (modified locally, preserved)")
                    continue
            if dest_rel not in installed:
                skipped.append(dest_rel)
            continue
        print(f"  + {dest_rel}")
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src_file.read_bytes())
            dest.chmod(src_file.stat().st_mode)
            installed[dest_rel] = digest(dest)
    if agents_conflict and not (root / POINTER).exists():
        print(f"  + {POINTER}  (existing AGENTS.md kept; ASE rules in {FALLBACK_RULES})")
        if not dry_run:
            (root / POINTER).parent.mkdir(parents=True, exist_ok=True)
            (root / POINTER).write_text(POINTER_TEXT, encoding="utf-8")
            installed[POINTER] = digest(root / POINTER)
    if agents_conflict and not (root / AGY_POINTER).exists():
        print(f"  + {AGY_POINTER}  (Antigravity always_on pointer to {FALLBACK_RULES})")
        if not dry_run:
            (root / AGY_POINTER).parent.mkdir(parents=True, exist_ok=True)
            (root / AGY_POINTER).write_text(AGY_POINTER_TEXT, encoding="utf-8")
            installed[AGY_POINTER] = digest(root / AGY_POINTER)
    for rel in skipped:
        print(f"  = {rel}  (already exists, not overwritten)")
    if dry_run:
        print("dry run: nothing written")
        return 0
    installed[MANIFEST] = ""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps({"versioned": versioned, "encapsulated": encapsulated, "files": installed}, indent=2) + "\n"
    )
    if not versioned and has_git:
        exclude_entries = ["/" + p for p in installed]
        if encapsulated:
            exclude_entries.append(f"/{ENCAPSULATED_PREFIX}/")
        if write_exclude(root, exclude_entries):
            print(f"ASE files excluded from Git via {exclude_file(root)}")
    print("Done. Open the repository in Antigravity (or VS Code), select the 'ASE Lead' agent and run /ase-adopt.")
    return 0


def uninstall(root: Path, has_git: bool = True) -> int:
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
    if has_git:
        write_exclude(root, [])
    for rel in kept:
        print(f"  kept (modified by you): {rel}")
    print("ASE removed. Files you changed (e.g. Project Memory) were kept.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", type=Path)
    parser.add_argument("--versioned", action="store_true", help="do not exclude ASE files from Git")
    parser.add_argument("--flat", action="store_true", help="install project-memory, artifacts, scripts, templates at root instead of .ase/")
    parser.add_argument("--no-git", action="store_true", help="allow installing into a directory that is not yet a Git repo")
    parser.add_argument("--upgrade", action="store_true", help="upgrade unmodified ASE files to the latest template version")
    parser.add_argument("--verify-layout", action="store_true", help="verify .ase/ encapsulation and check for stray template clones")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    root, has_git = git_root(args.target, allow_no_git=args.no_git)
    if (root / "install.py").resolve() == Path(__file__).resolve() and not args.verify_layout:
        sys.exit("error: target is the ASE template itself")
    if args.verify_layout:
        return verify_layout(root)
    return (
        uninstall(root, has_git)
        if args.uninstall
        else install(root, args.versioned, args.dry_run, has_git, args.upgrade, encapsulated=not args.flat)
    )


if __name__ == "__main__":
    raise SystemExit(main())
