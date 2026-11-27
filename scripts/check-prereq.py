#!/usr/bin/env python3
"""Deterministic Step 0 prerequisite guard and post-command reactive chain evaluator for ASE.

Supports two modes (ADR-004, ADR-008):
  1. Step 0 Prerequisite Check (`--command <cmd>`):
     Verifies whether the invoked `/ase-*` command's lifecycle prerequisites are satisfied.
     When a prerequisite is missing, instead of a dead-end failure, outputs `prerequisite_chain`
     and `chain_approval_prompt` so the agent can ask the Human Owner for approval to run the
     prerequisite command first and then automatically resume the requested command.
  2. Post-Command Reactive Cascade Evaluation (`--post --command <cmd>`):
     Inspects workspace state after `<cmd>` completes and returns `downstream_chain`,
     `recommended_next_command`, `applicable_hag`, and `chain_approval_prompt` (including
     token-aware Graphify `--update` gating under `HAG-04`).
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
    "ase-memo",
    "ase-context",
    "ase-task",
    "ase-review",
    "ase-pack",
    "ase-export",
    "ase-status",
    "ase-plugin",
    "ase-switch",
    "ase-upgrade",
)


def detect_pending_release_clone(root: Path) -> Path | None:
    for install_py in sorted(root.rglob("install.py")):
        cand = install_py.parent.resolve()
        if cand == root:
            continue
        rel = cand.relative_to(root).as_posix()
        if rel in (".ase/template", "implementazione/dcp-template"):
            continue
        if (cand / "AGENTS.md").is_file() and (cand / ".agents" / "skills").is_dir() and (cand / "project-memory").is_dir():
            return cand
    return None


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
        "context_alerts": "none",
        "pending_chain": "none",
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
    m_alert = re.search(r"\*\*Context Alerts:\*\*\s*([^\n]+)", text)
    if m_alert:
        info["context_alerts"] = m_alert.group(1).strip().strip("`")
    m_chain = re.search(r"\*\*Pending Command Chain:\*\*\s*([^\n]+)", text)
    if m_chain:
        info["pending_chain"] = m_chain.group(1).strip().strip("`")
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


def count_unprocessed_inputs(root: Path, memory_dir: Path) -> dict[str, int]:
    inputs_dir = root / "inputs"
    state_path = memory_dir / "state" / "INPUTS_STATE.json"
    recorded: dict[str, Any] = {}
    if state_path.is_file():
        try:
            recorded = json.loads(state_path.read_text(encoding="utf-8")).get("files", {})
        except (OSError, json.JSONDecodeError):
            recorded = {}

    pending_docs = 0
    pending_total = 0
    if inputs_dir.is_dir():
        for p in sorted(inputs_dir.rglob("*")):
            if not p.is_file() or p.name in (".gitkeep", "README.md"):
                continue
            rel = p.relative_to(inputs_dir).as_posix()
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
            if recorded.get(rel, {}).get("sha256") != sha:
                pending_total += 1
                if p.suffix.lower() in (".md", ".txt", ".pdf", ".png", ".jpg", ".jpeg", ".webp"):
                    pending_docs += 1
    return {"pending_total": pending_total, "pending_docs": pending_docs}


def check_pending_context_hag(memory_dir: Path) -> str:
    log_path = memory_dir / "state" / "CONTEXT_LOG.md"
    if not log_path.is_file():
        return ""
    lines = [ln.strip() for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip().startswith("|")]
    if not lines:
        return ""
    last_row = lines[-1]
    m = re.search(r"PENDING\s*:?\s*(HAG-0[1-7])", last_row, re.IGNORECASE)
    return m.group(1).upper() if m else ""


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

    pending_clone = detect_pending_release_clone(root)
    if command in ("ase-switch", "ase-upgrade"):
        if pending_clone is None:
            blockers.append(
                "No cloned ASE release directory was found in the workspace root. "
                "Clone the new release into the workspace root first (e.g. `git clone .../agentic-dcp-template`)."
            )
    elif pending_clone is not None:
        rel_clone = pending_clone.relative_to(root).as_posix()
        blockers.append(
            f"Detected a cloned ASE release at `./{rel_clone}/`. "
            f"Run `/ase-switch` / `/ase-upgrade` (or `python3 {rel_clone}/install.py . --switch`) first to complete the in-place release switch and auto-remove the clone."
        )
        run_first.append("/ase-switch")

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

    elif command in ("ase-plan", "ase-memo", "ase-context"):
        if not baseline_ready:
            blockers.append(
                "Baseline setup (`M0` or `M0-A`) is not marked `PASS` in `state/PROJECT_STATE.md`."
            )
            run_first.extend(["/ase-adopt (existing/local repo)", "/ase-setup (new GitHub repo)"])
        if command == "ase-plan" and next_task["status"] == "IN_REVIEW":
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
        if next_task["context_alerts"] not in ("none", ""):
            warnings.append(
                f"Active Context Alert on `NEXT_TASK.md`: {next_task['context_alerts']}. "
                "Confirm with the Human Owner whether to adjust the task via `/ase-plan` before coding."
            )

    elif command == "ase-review":
        if not baseline_ready:
            blockers.append(
                "Baseline setup (`M0` or `M0-A`) is not marked `PASS` in `state/PROJECT_STATE.md`."
            )
            run_first.extend(["/ase-adopt", "/ase-setup"])
        elif not done_tasks and next_task["status"] != "IN_REVIEW":
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
        elif not done_tasks and next_task["status"] != "IN_REVIEW":
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
    canonical_cmd = "/ase-memo" if command == "ase-context" else f"/{command}"
    prerequisite_chain: list[str] = []
    chain_approval_prompt = ""
    if not ok and run_first:
        first_clean = run_first[0].split()[0]
        prerequisite_chain = [*[c.split()[0] for c in run_first], f"/{command}"]
        chain_approval_prompt = (
            f"Upstream Prerequisite Chain detected (`{' -> '.join(prerequisite_chain)}`). "
            f"Ask the Human Owner for approval to execute `{first_clean}` first and then automatically continue with `/{command}`."
        )

    # Inspect federated topology & HANDOFF.json (ADR-009)
    handoff_file = memory_dir / "state" / "HANDOFF.json"
    pending_handoff: dict[str, Any] | None = None
    if handoff_file.is_file():
        try:
            hdata = json.loads(handoff_file.read_text(encoding="utf-8"))
            for h in hdata.get("handoffs", []):
                if h.get("status") == "PENDING":
                    pending_handoff = {
                        "handoff_id": h.get("handoff_id"),
                        "handoff_type": h.get("handoff_type"),
                        "recommended_command": h.get("governance", {}).get("recommended_command", "/ase-plan"),
                        "objective": h.get("dispatch_payload", {}).get("objective", ""),
                    }
                    warnings.append(
                        f"Pending Parent Orchestrator Handoff `{pending_handoff['handoff_id']}` ({pending_handoff['handoff_type']}): "
                        f"{pending_handoff['objective']} -> recommended command `{pending_handoff['recommended_command']}`."
                    )
                    break
        except (OSError, json.JSONDecodeError):
            pass

    return {
        "command": f"/{command}",
        "canonical_command": canonical_cmd,
        "is_context_alias": command in ("ase-memo", "ase-context"),
        "ok": ok,
        "m0_pass": m0_pass,
        "m0a_pass": m0a_pass,
        "next_task": next_task,
        "pending_handoff": pending_handoff,
        "blockers": blockers,
        "warnings": warnings,
        "run_first": run_first,
        "prerequisite_chain": prerequisite_chain,
        "chain_approval_prompt": chain_approval_prompt,
    }


def evaluate_post_command(root: Path, command: str) -> dict[str, Any]:
    """Evaluate downstream cascade triggers after `command` completes (Category 1 Reactive Chaining)."""
    root = root.resolve()
    memory_dir = resolve_memory_dir(root)
    m0_pass, m0a_pass = check_baseline_state(memory_dir)
    baseline_ready = m0_pass or m0a_pass
    next_task = read_next_task(memory_dir)
    tasks = collect_task_states(memory_dir)

    done_tasks = [t["id"] for t in tasks if t["status"] == "DONE"]
    todo_tasks = [t["id"] for t in tasks if t["status"] == "TODO"]
    paused_tasks = [t["id"] for t in tasks if t["status"] == "PAUSED"]
    in_review_tasks = [t["id"] for t in tasks if t["status"] == "IN_REVIEW"]

    pending_hag = check_pending_context_hag(memory_dir)
    inputs_info = count_unprocessed_inputs(root, memory_dir)
    graph_file = root / "graphify-out" / "graph.json"
    graph_present = graph_file.is_file()
    plugins_dir = root / "plugins"
    has_plugins = plugins_dir.is_dir() and any(p.is_dir() for p in plugins_dir.iterdir())

    recommended_next = ""
    applicable_hag = ""
    downstream_chain: list[str] = []
    chain_reason = ""
    graphify_advisory = ""

    if graph_present and inputs_info["pending_docs"] > 0:
        graphify_advisory = (
            f"Graphify (`graphify-out/graph.json`) is present and {inputs_info['pending_docs']} new/modified document(s)/image(s) exist in `inputs/`. "
            "Running `/graphify --update` on semantic files incurs LLM token usage (`HAG-04` cost gate)."
        )

    if command in ("ase-memo", "ase-context"):
        if pending_hag:
            recommended_next = "/ase-plan"
            applicable_hag = pending_hag
            downstream_chain = [f"/{command}", "/ase-plan"]
            chain_reason = (
                f"Context update logged a normative change requiring `{pending_hag}` approval and backlog/ADR reshaping via `/ase-plan`."
            )
        elif next_task["context_alerts"] not in ("none", ""):
            recommended_next = "/ase-plan"
            applicable_hag = "HAG-02"
            downstream_chain = [f"/{command}", "/ase-plan"]
            chain_reason = (
                f"Context update raised an alert on open work (`{next_task['context_alerts']}`). Propose `/ase-plan` to adjust the task or insert a WBS `T-NNNN.1` step."
            )
        elif has_plugins:
            recommended_next = "/ase-plugin"
            applicable_hag = "HAG-02"
            downstream_chain = [f"/{command}", "/ase-plugin"]
            chain_reason = "Project conventions were updated and a domain plugin exists in `plugins/`; propose syncing via `/ase-plugin`."

    elif command in ("ase-adopt", "ase-setup"):
        if baseline_ready and not tasks:
            recommended_next = "/ase-plan"
            applicable_hag = "HAG-02"
            downstream_chain = [f"/{command}", "/ase-plan"]
            chain_reason = "Baseline onboarding is `PASS` and no backlog tasks exist yet; propose `/ase-plan` to create the initial Wave/Feature backlog."

    elif command == "ase-plan":
        if pending_hag:
            recommended_next = "/ase-plan"
            applicable_hag = pending_hag
            downstream_chain = ["/ase-plan", "/ase-plan"]
            chain_reason = f"Pending `{pending_hag}` normative change from context update requires approval before reshaping the backlog."
        elif next_task["id"] not in ("none", "") and next_task["status"] == "TODO":
            recommended_next = "/ase-task"
            downstream_chain = ["/ase-plan", "/ase-task"]
            chain_reason = f"Task `{next_task['id']}` (`TODO`) is assigned in `NEXT_TASK.md` and ready for execution via `/ase-task`."

    elif command == "ase-task":
        if in_review_tasks:
            applicable_hag = "HAG-01"
            if todo_tasks or paused_tasks or next_task["queued"] not in ("none", "") or next_task["return_stack"] not in ("none", ""):
                recommended_next = "/ase-task"
                downstream_chain = ["/ase-task (HAG-01 accept)", "/ase-task (next task)"]
                chain_reason = (
                    f"Once `{in_review_tasks[0]}` is accepted under `HAG-01` (`DONE`), advance `NEXT_TASK.md` and run `/ase-task` on the next queued/remaining task."
                )
            else:
                recommended_next = "/ase-review"
                downstream_chain = ["/ase-task (HAG-01 accept)", "/ase-review"]
                chain_reason = (
                    f"Once `{in_review_tasks[0]}` is accepted under `HAG-01` (`DONE`), all planned tasks in the Work Package will be complete; propose `/ase-review`."
                )
        elif done_tasks and not todo_tasks and not paused_tasks:
            recommended_next = "/ase-review"
            downstream_chain = ["/ase-task", "/ase-review"]
            chain_reason = "All planned tasks are `DONE`; propose `/ase-review` to run the Work Package quality gate."
        elif todo_tasks or paused_tasks:
            recommended_next = "/ase-task"
            downstream_chain = ["/ase-task", "/ase-task"]
            chain_reason = "Remaining `TODO` or `PAUSED` tasks exist; propose continuing with `/ase-task`."

    elif command == "ase-review":
        if done_tasks and not in_review_tasks and not todo_tasks and not paused_tasks:
            recommended_next = "/ase-pack"
            downstream_chain = ["/ase-review", "/ase-pack"]
            chain_reason = "Work Package review is complete; propose `/ase-pack` to curate `deliverables/` and generate `deliverables/INDEX.md`."

    elif command == "ase-pack":
        pack_state_file = memory_dir / "state" / "PACK_STATE.json"
        if pack_state_file.is_file():
            recommended_next = "/ase-export"
            downstream_chain = ["/ase-pack", "/ase-export"]
            chain_reason = "Workspace and `deliverables/` are freshly packed; offer optional `/ase-export` if the Human Owner needs a standalone `.zip` handover bundle."

    elif command in ("ase-switch", "ase-upgrade"):
        if inputs_info["pending_total"] > 0:
            recommended_next = "/ase-memo"
            downstream_chain = [f"/{command}", "/ase-memo"]
            chain_reason = f"Release switch succeeded and {inputs_info['pending_total']} new file(s) exist in `inputs/`; propose `/ase-memo` to ingest them."
        elif next_task["id"] not in ("none", "") and next_task["status"] in ("TODO", "IN_PROGRESS"):
            recommended_next = "/ase-task"
            downstream_chain = [f"/{command}", "/ase-task"]
            chain_reason = f"Release switch succeeded; propose resuming active task `{next_task['id']}` via `/ase-task`."

    chain_approval_prompt = ""
    if recommended_next:
        hag_prefix = f" under `{applicable_hag}`" if applicable_hag else ""
        chain_approval_prompt = (
            f"{chain_reason} Ask the Human Owner for approval{hag_prefix} before executing `{recommended_next}`."
        )

    return {
        "completed_command": f"/{command}",
        "recommended_next_command": recommended_next,
        "applicable_hag": applicable_hag,
        "downstream_chain": downstream_chain,
        "chain_reason": chain_reason,
        "chain_approval_prompt": chain_approval_prompt,
        "graphify_advisory": graphify_advisory,
        "next_task": next_task,
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
    if res.get("prerequisite_chain"):
        cmds = " -> ".join(f"`{c}`" for c in res["prerequisite_chain"])
        lines.append(f"Reactive Prerequisite Chain: {cmds}")
        lines.append(f"Action: {res['chain_approval_prompt']}")
    elif res["run_first"]:
        cmds = " -> ".join(f"`{c}`" for c in res["run_first"])
        lines.append(f"Required action first: run {cmds} before `{res['command']}`.")
    return "\n".join(lines)


def format_post_report(res: dict[str, Any]) -> str:
    lines = [f"POST-CHECK: completed `{res['completed_command']}`."]
    if res["recommended_next_command"]:
        chain_str = " -> ".join(f"`{c}`" for c in res["downstream_chain"])
        lines.append(f"Recommended Reactive Chain: {chain_str}")
        if res["applicable_hag"]:
            lines.append(f"Applicable Approval Gate: `{res['applicable_hag']}`")
        lines.append(f"Action: {res['chain_approval_prompt']}")
    else:
        lines.append("No automatic downstream command trigger detected.")
    if res["graphify_advisory"]:
        lines.append(f"GRAPHIFY ADVISORY: {res['graphify_advisory']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--command",
        required=True,
        choices=COMMANDS,
        help="ASE command slug to check (e.g. ase-plan, ase-memo, ase-context, ase-task, ase-pack, ase-export).",
    )
    parser.add_argument(
        "--post",
        action="store_true",
        help="Evaluate post-command downstream reactive chaining instead of Step 0 prerequisites.",
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

    if args.post:
        res = evaluate_post_command(args.root, args.command)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(format_post_report(res))
        return 0

    res = evaluate_prerequisites(args.root, args.command)
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        stream = sys.stdout if res["ok"] else sys.stderr
        print(format_report(res), file=stream)
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
