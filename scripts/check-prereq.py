#!/usr/bin/env python3
"""Deterministic Step 0 command dependency and prerequisite guard for ASE.

Checks whether the invoked /ase-* command's lifecycle prerequisites are satisfied.
When a hard dependency is violated, exits with code 1 and prints the exact blocker
and the prerequisite command the Human Owner must run first (ADR-004).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

COMMANDS = (
    "ase-setup",
    "ase-adopt",
    "ase-plan",
    "ase-task",
    "ase-review",
    "ase-pack",
    "ase-export",
    "ase-status",
    "ase-plugin",
)


def resolve_memory_dir(root: Path) -> Path:
    encapsulated = root / ".ase" / "project-memory"
    if encapsulated.is_dir():
        return encapsulated
    return root / "project-memory"


def resolve_deliverables_dir(root: Path) -> Path:
    if (root / "deliverables").is_dir():
        return root / "deliverables"
    if (root / ".ase" / "deliverables").is_dir():
        return root / ".ase" / "deliverables"
    if (root / "artifacts").is_dir():
        return root / "artifacts"
    if (root / ".ase" / "artifacts").is_dir():
        return root / ".ase" / "artifacts"
    return root / "deliverables"


def parse_front_matter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---(?:\s*\n|\Z)", text, re.DOTALL)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        m = re.match(r"^([a-zA-Z_][\w-]*):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip("'\"")
    return fields


def check_baseline_state(memory_dir: Path) -> tuple[bool, bool]:
    """Return (m0_pass, m0a_pass) from state/PROJECT_STATE.md."""
    state_file = memory_dir / "state" / "PROJECT_STATE.md"
    if not state_file.is_file():
        return False, False
    text = state_file.read_text(encoding="utf-8")
    m0_pass = bool(re.search(r"\|\s*M0\s*\|\s*PASS\b", text, re.IGNORECASE))
    m0a_pass = bool(re.search(r"\|\s*M0-A\s*\|\s*PASS\b", text, re.IGNORECASE))
    return m0_pass, m0a_pass


def read_next_task(memory_dir: Path) -> dict[str, str]:
    info = {
        "id": "none",
        "status": "none",
        "queued": "none",
        "return_stack": "none",
    }
    nt_file = memory_dir / "state" / "NEXT_TASK.md"
    if not nt_file.is_file():
        return info
    text = nt_file.read_text(encoding="utf-8")
    m_id = re.search(r"\*\*ID:\*\*\s*`([^`]+)`", text)
    if m_id:
        info["id"] = m_id.group(1).strip()
    m_st = re.search(r"\*\*Status:\*\*\s*`([^`]+)`", text)
    if m_st:
        info["status"] = m_st.group(1).strip()
    m_q = re.search(r"\*\*Queued next in inner sequence:\*\*\s*([^\n]+)", text)
    if m_q:
        info["queued"] = m_q.group(1).strip().strip("`")
    m_ret = re.search(r"\*\*Return Stack[^:]*:\*\*\s*([^\n]+)", text)
    if m_ret:
        info["return_stack"] = m_ret.group(1).strip().strip("`")
    return info


def collect_task_states(memory_dir: Path) -> list[dict[str, str]]:
    tasks_dir = memory_dir / "dcp" / "04-implementation" / "tasks"
    if not tasks_dir.is_dir():
        return []
    out: list[dict[str, str]] = []
    for p in sorted(tasks_dir.glob("*.md")):
        fm = parse_front_matter(p)
        tid = fm.get("id", "").strip()
        if tid:
            out.append(
                {
                    "id": tid,
                    "status": fm.get("status", "TODO").strip() or "TODO",
                    "parent": fm.get("parent", "").strip(),
                }
            )
    return out


def compute_workspace_pack_digest(root: Path, memory_dir: Path) -> str:
    """Compute a deterministic digest of task states and deliverables content (excluding INDEX.md)."""
    h = hashlib.sha256()
    for t in collect_task_states(memory_dir):
        h.update(f"task:{t['id']}:{t['status']}\n".encode("utf-8"))
    deliv_dir = resolve_deliverables_dir(root)
    if deliv_dir.is_dir():
        for p in sorted(deliv_dir.rglob("*")):
            if not p.is_file() or p.name in (".gitkeep", "INDEX.md", "README.md"):
                continue
            rel = p.relative_to(deliv_dir).as_posix()
            h.update(f"deliv:{rel}:{p.stat().st_size}\n".encode("utf-8"))
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def evaluate_prerequisites(root: Path, command: str) -> dict[str, Any]:
    root = root.resolve()
    memory_dir = resolve_memory_dir(root)
    m0_pass, m0a_pass = check_baseline_state(memory_dir)
    baseline_ready = m0_pass or m0a_pass
    next_task = read_next_task(memory_dir)
    tasks = collect_task_states(memory_dir)

    done_tasks = [t["id"] for t in tasks if t["status"] == "DONE"]
    in_flight = [
        f"{t['id']} ({t['status']})"
        for t in tasks
        if t["status"] in ("IN_PROGRESS", "IN_REVIEW", "PAUSED", "BLOCKED")
    ]
    todo_tasks = [t["id"] for t in tasks if t["status"] == "TODO"]

    blockers: list[str] = []
    warnings: list[str] = []
    run_first: list[str] = []

    if command == "ase-setup":
        if m0a_pass:
            blockers.append(
                "Repository is already onboarded in `local` Git mode (`M0-A | PASS` in `PROJECT_STATE.md`). "
                "`/ase-setup` and `/ase-adopt` are mutually exclusive."
            )
            run_first.append("/ase-plan")

    elif command == "ase-adopt":
        if m0_pass:
            blockers.append(
                "Repository is already configured in `remote` Git mode (`M0 | PASS` in `PROJECT_STATE.md`). "
                "`/ase-adopt` and `/ase-setup` are mutually exclusive."
            )
            run_first.append("/ase-plan")

    elif command == "ase-plan":
        if not baseline_ready:
            blockers.append(
                "Baseline setup (`M0` or `M0-A`) is not marked `PASS` in `state/PROJECT_STATE.md`."
            )
            run_first.extend(["/ase-adopt (existing/local repo)", "/ase-setup (new GitHub repo)"])
        if next_task["status"] == "IN_REVIEW":
            warnings.append(
                f"Task `{next_task['id']}` is currently `IN_REVIEW`. Accept its diff first (`HAG-01`) "
                "or confirm pausing it (`PAUSED`) on the Return Stack before changing `NEXT_TASK.md`."
            )

    elif command == "ase-task":
        if not baseline_ready:
            blockers.append(
                "Baseline setup (`M0` or `M0-A`) is not marked `PASS` in `state/PROJECT_STATE.md`."
            )
            run_first.extend(["/ase-adopt", "/ase-setup"])
        elif next_task["id"] in ("none", "") or next_task["status"] == "none":
            blockers.append(
                "No active task is assigned in `state/NEXT_TASK.md`."
            )
            run_first.append("/ase-plan")
        elif next_task["status"] == "BLOCKED":
            blockers.append(
                f"Assigned task `{next_task['id']}` is `BLOCKED`. Resolve the blocker or re-plan first."
            )
            run_first.append("/ase-plan")

    elif command == "ase-review":
        if not baseline_ready:
            blockers.append(
                "Baseline setup (`M0` or `M0-A`) is not marked `PASS` in `state/PROJECT_STATE.md`."
            )
            run_first.extend(["/ase-adopt", "/ase-setup"])
        elif not done_tasks:
            blockers.append(
                "No completed (`DONE`) tasks exist yet to review."
            )
            run_first.append("/ase-task" if todo_tasks or in_flight else "/ase-plan")
        elif in_flight:
            blockers.append(
                f"Cannot run `/ase-review` while tasks are still in flight or suspended: {', '.join(in_flight)}."
            )
            run_first.append("/ase-task")
        elif next_task["return_stack"] not in ("none", ""):
            blockers.append(
                f"Cannot run `/ase-review` while the Return Stack in `NEXT_TASK.md` still holds paused work (`{next_task['return_stack']}`)."
            )
            run_first.append("/ase-task")

    elif command == "ase-pack":
        if not baseline_ready:
            blockers.append(
                "Baseline setup (`M0` or `M0-A`) is not marked `PASS` in `state/PROJECT_STATE.md`."
            )
            run_first.extend(["/ase-adopt", "/ase-setup"])
        elif not done_tasks:
            blockers.append(
                "Cannot run `/ase-pack` before at least one task is `DONE`."
            )
            run_first.append("/ase-task" if todo_tasks or in_flight else "/ase-plan")
        elif in_flight:
            blockers.append(
                f"Cannot run `/ase-pack` while tasks are still active or suspended: {', '.join(in_flight)}."
            )
            run_first.append("/ase-task")
        elif next_task["return_stack"] not in ("none", ""):
            blockers.append(
                f"Cannot run `/ase-pack` while the Return Stack in `NEXT_TASK.md` still holds paused work (`{next_task['return_stack']}`)."
            )
            run_first.append("/ase-task")
        else:
            reviews_dir = memory_dir / "state" / "reviews"
            has_reviews = reviews_dir.is_dir() and any(
                p.suffix == ".md" for p in reviews_dir.iterdir()
            )
            if not has_reviews:
                warnings.append(
                    "No Work Package review report was found under `state/reviews/`. "
                    "Consider running `/ase-review` before `/ase-pack` when closing a Work Package."
                )

    elif command == "ase-export":
        deliv_dir = resolve_deliverables_dir(root)
        index_file = deliv_dir / "INDEX.md"
        pack_state_file = memory_dir / "state" / "PACK_STATE.json"
        if not baseline_ready:
            blockers.append(
                "Baseline setup (`M0` or `M0-A`) is not marked `PASS` in `state/PROJECT_STATE.md`."
            )
            run_first.extend(["/ase-adopt", "/ase-setup"])
        elif in_flight:
            blockers.append(
                f"Cannot run `/ase-export` while tasks are active or suspended: {', '.join(in_flight)}."
            )
            run_first.extend(["/ase-task", "/ase-pack"])
        elif not index_file.is_file() or not pack_state_file.is_file():
            blockers.append(
                "Dependency violation: `/ase-export` requires `/ase-pack` to be executed first "
                "(`deliverables/INDEX.md` or `state/PACK_STATE.json` is missing)."
            )
            run_first.append("/ase-pack")
        else:
            try:
                pack_state = json.loads(pack_state_file.read_text(encoding="utf-8"))
                expected_digest = pack_state.get("workspace_digest", "")
            except (OSError, json.JSONDecodeError):
                expected_digest = ""
            current_digest = compute_workspace_pack_digest(root, memory_dir)
            if not expected_digest or expected_digest != current_digest:
                blockers.append(
                    "Dependency violation: workspace tasks or `deliverables/` changed after the last `/ase-pack` run. "
                    "Re-run `/ase-pack` before `/ase-export` so the exported archive is up to date."
                )
                run_first.append("/ase-pack")

    elif command == "ase-plugin":
        if not baseline_ready:
            blockers.append(
                "Baseline setup (`M0` or `M0-A`) is not marked `PASS` in `state/PROJECT_STATE.md`."
            )
            run_first.extend(["/ase-adopt", "/ase-setup"])

    elif command == "ase-status":
        if not baseline_ready:
            warnings.append(
                "Baseline setup (`M0` or `M0-A`) is not complete yet; run `/ase-adopt` or `/ase-setup` first."
            )

    ok = len(blockers) == 0
    return {
        "command": f"/{command}",
        "ok": ok,
        "m0_pass": m0_pass,
        "m0a_pass": m0a_pass,
        "next_task": next_task,
        "blockers": blockers,
        "warnings": warnings,
        "run_first": run_first,
    }


def format_report(res: dict[str, Any]) -> str:
    if res["ok"]:
        lines = [f"PASS: prerequisites satisfied for `{res['command']}`."]
        for w in res["warnings"]:
            lines.append(f"WARNING: {w}")
        return "\n".join(lines)

    lines = [f"BLOCKED: prerequisites not met for `{res['command']}`."]
    for b in res["blockers"]:
        lines.append(f"  - {b}")
    if res["run_first"]:
        cmds = " -> ".join(f"`{c}`" for c in res["run_first"])
        lines.append(f"Required action first: run {cmds} before `{res['command']}`.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--command",
        required=True,
        choices=COMMANDS,
        help="ASE command slug to check (e.g. ase-plan, ase-task, ase-pack, ase-export).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: current directory).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON.",
    )
    args = parser.parse_args()

    res = evaluate_prerequisites(args.root, args.command)
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        stream = sys.stdout if res["ok"] else sys.stderr
        print(format_report(res), file=stream)
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
