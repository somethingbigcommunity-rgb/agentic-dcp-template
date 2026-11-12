#!/usr/bin/env python3
"""Print the next unused sequential ASE identifier in a project."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ID_TYPES = {
    "requirement": ("REQ", 3, ("dcp/01-requirements",)),
    "wave": ("W", 2, ("dcp/04-implementation/waves",)),
    "feature": ("F", 3, ("dcp/04-implementation/features",)),
    "work-package": ("WP", 3, ("dcp/04-implementation/features",)),
    "user-story": ("US", 3, ("dcp/01-requirements/user-stories",)),
    "task": ("T", 4, ("dcp/04-implementation/tasks",)),
    "adr": ("ADR", 3, ("adr",)),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", required=True, choices=tuple(ID_TYPES))
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root containing project-memory/ (default: current directory)",
    )
    return parser.parse_args()


def canonical_files(root: Path, identifier_type: str) -> list[Path]:
    prefix, width, relative_dirs = ID_TYPES[identifier_type]
    paths: set[Path] = set()
    for relative_dir in relative_dirs:
        directory = root / "project-memory" / relative_dir
        if directory.is_dir():
            paths.update(directory.rglob("*.md"))

    if identifier_type == "task":
        task_log = root / "project-memory/state/TASK_LOG.md"
        if task_log.is_file():
            paths.add(task_log)

    return sorted(paths)


def used_ids(root: Path, identifier_type: str) -> set[int]:
    prefix, width, _ = ID_TYPES[identifier_type]
    identifier = re.compile(rf"{re.escape(prefix)}-(\d{{{width}}})\b")
    front_matter_id = re.compile(r"^id:\s*([A-Z]+-\d+)\s*$")
    requirement_heading = re.compile(r"^#{1,6}\s+")
    task_log_entry = re.compile(r"^\|\s*\d{4}-\d{2}-\d{2}\s*\|\s*(T-\d{4})\s*\|")
    found: set[int] = set()

    for path in canonical_files(root, identifier_type):
        if path.name.startswith(f"{prefix}-"):
            match = identifier.match(path.name)
            if match:
                found.add(int(match.group(1)))
        for line in path.read_text(encoding="utf-8").splitlines():
            candidate = line.strip()
            if identifier_type == "task" and path.name == "TASK_LOG.md":
                log_match = task_log_entry.match(candidate)
                if log_match:
                    match = identifier.match(log_match.group(1))
                    if match:
                        found.add(int(match.group(1)))
                continue
            if identifier_type == "requirement" and requirement_heading.match(candidate):
                candidate = requirement_heading.sub("", candidate, count=1)
            elif not candidate.startswith("id:"):
                continue
            else:
                id_match = front_matter_id.match(candidate)
                candidate = id_match.group(1) if id_match else ""
            match = identifier.match(candidate)
            if match:
                found.add(int(match.group(1)))
    return found


def next_id(root: Path, identifier_type: str) -> str:
    if not root.is_dir():
        raise ValueError(f"project root is not a directory: {root}")
    prefix, width, _ = ID_TYPES[identifier_type]
    used = used_ids(root, identifier_type)
    return f"{prefix}-{max(used, default=0) + 1:0{width}d}"


def main() -> int:
    args = parse_args()
    try:
        print(next_id(args.root.resolve(), args.type))
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
