#!/usr/bin/env python3
"""Deterministic Federated Multi-Project Topology & Polymorphic HANDOFF.json Engine for ASE (ADR-009).

Responsibilities (< 50ms, 0 LLM tokens):
  1. Role & Hierarchy Auto-Discovery (`--scan`):
     - Detects `standalone`, `orchestrator` (Father Umbrella Root), or `member` (Child ASE Project).
     - Identifies `member` child folders (already have ASE) and `unmanaged_child` folders (have code/.git but no ASE yet).
     - Also reads any `*.code-workspace` `folders` entries if present.
  2. Proactive Unmanaged Subproject Onboarding (`--onboard-child <dir>`):
     - Runs `install.py` into `<dir>`, links `"parent_root"` in `<dir>/.agents/.ase-install.json`,
       and dispatches an initial `ONBOARD_ADOPT` (`HO-NNNN`) handoff into `<dir>/.ase/project-memory/state/HANDOFF.json`.
  3. Polymorphic & Temporal (`T0 -> T1 -> T2 -> T3`) `HANDOFF.json` State Machine:
     - 6 Handoff Types: `ONBOARD_ADOPT`, `CONTEXT_MEMO_SYNC`, `CONTRACT_AND_PLAN`,
       `TASK_OR_HOTFIX_EXECUTION`, `INTEGRATION_REVIEW_GATE`, `DELIVERABLE_PACK_ROLLUP`.
     - States: `WAITING_DEPENDENCY -> PENDING -> ACKNOWLEDGED -> IN_PROGRESS -> ESCALATED_TO_PARENT -> IN_REVIEW -> COMPLETED | BLOCKED | SUPERSEDED`.
     - `--dispatch` (T0: Father -> Child), `--ack` (T1: Child start & local ID binding),
       `--escalate` (T2: Child upward HAG/contract escalation), `--complete` (T3: Child -> Father receipt).
  4. Zero-Token Federation Rollup (`--rollup`):
     - Reads all child `HANDOFF.json` and `NEXT_TASK.md` states, automatically unblocks sibling handoffs
       whose `depends_on_handoffs` are `COMPLETED`, checks SHA-256 `contract_digest` drift, and writes
       Father `state/FEDERATION_STATE.json`.
  5. Zero-Token Cross-Project Graphify Blast-Radius Query (`--query-graph <term>`):
     - Queries across all `<child>/graphify-out/graph.json` files locally in 0 LLM tokens.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

IGNORED_DIRS = {
    ".ase",
    ".agents",
    ".github",
    ".git",
    ".vscode",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "deliverables",
    "artifacts",
    "handover",
    "inputs",
    "plugins",
    "graphify-out",
    "implementazione",
    "paradigma",
    "specs",
    "scripts",
    "templates",
    "project-memory",
}

PROJECT_MARKERS = (
    ".git",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "pom.xml",
    "build.gradle",
    "Cargo.toml",
    "go.mod",
    "Makefile",
    "CMakeLists.txt",
    "src",
    "app",
)

VALID_HANDOFF_TYPES = (
    "ONBOARD_ADOPT",
    "CONTEXT_MEMO_SYNC",
    "CONTRACT_AND_PLAN",
    "TASK_OR_HOTFIX_EXECUTION",
    "INTEGRATION_REVIEW_GATE",
    "DELIVERABLE_PACK_ROLLUP",
)

DEFAULT_COMMAND_BY_TYPE = {
    "ONBOARD_ADOPT": "/ase-adopt",
    "CONTEXT_MEMO_SYNC": "/ase-memo",
    "CONTRACT_AND_PLAN": "/ase-plan",
    "TASK_OR_HOTFIX_EXECUTION": "/ase-task",
    "INTEGRATION_REVIEW_GATE": "/ase-review",
    "DELIVERABLE_PACK_ROLLUP": "/ase-pack",
}

VALID_STATUSES = (
    "WAITING_DEPENDENCY",
    "PENDING",
    "ACKNOWLEDGED",
    "IN_PROGRESS",
    "ESCALATED_TO_PARENT",
    "IN_REVIEW",
    "COMPLETED",
    "BLOCKED",
    "SUPERSEDED",
)

SECRET_RE = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----|"
    r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b|"
    r"\bsk-[A-Za-z0-9_-]{20,}\b|"
    r"\bAKIA[0-9A-Z]{16}\b|"
    r"\bAIza[0-9A-Za-z_-]{30,}\b|"
    r"(?i:\b(?:password|passwd|secret_key|api_key|access_token|private_key)\s*[:=]\s*['\"]?[A-Za-z0-9_\-/.@#]{10,}['\"]?)"
)

FIRST_PERSON_PLURAL_RE = re.compile(r"\b(?:we|our|ours|us|noi|abbiamo|nostro|nostra|nostri|nostre)\b", re.IGNORECASE)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def resolve_memory_dir(root: Path) -> Path:
    encapsulated = root / ".ase" / "project-memory"
    if encapsulated.is_dir():
        return encapsulated
    return root / "project-memory"


def has_ase_installed(folder: Path) -> bool:
    return (
        (folder / ".ase" / "project-memory" / "state" / "PROJECT_STATE.md").is_file()
        or (folder / "project-memory" / "state" / "PROJECT_STATE.md").is_file()
        or (folder / ".agents" / ".ase-install.json").is_file()
    )


def looks_like_subproject(folder: Path) -> bool:
    if has_ase_installed(folder):
        return True
    for marker in PROJECT_MARKERS:
        if (folder / marker).exists():
            return True
    return False


def discover_code_workspace_folders(root: Path) -> list[Path]:
    extra: list[Path] = []
    for ws_file in sorted(root.glob("*.code-workspace")):
        try:
            data = json.loads(ws_file.read_text(encoding="utf-8"))
            for item in data.get("folders", []):
                rel_p = item.get("path") if isinstance(item, dict) else None
                if rel_p:
                    cand = (root / rel_p).resolve()
                    if cand != root and cand.is_dir() and cand not in extra:
                        extra.append(cand)
        except (OSError, json.JSONDecodeError):
            pass
    return extra


def detect_parent_root(root: Path) -> Path | None:
    root = root.resolve()
    manifest = root / ".agents" / ".ase-install.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            p_raw = data.get("parent_root")
            if p_raw:
                cand = (root / p_raw).resolve()
                if cand.is_dir() and has_ase_installed(cand):
                    return cand
        except (OSError, json.JSONDecodeError):
            pass

    handoff_file = resolve_memory_dir(root) / "state" / "HANDOFF.json"
    if handoff_file.is_file():
        try:
            hdata = json.loads(handoff_file.read_text(encoding="utf-8"))
            p_raw = hdata.get("parent_root")
            if p_raw:
                cand = (root / p_raw).resolve()
                if cand.is_dir():
                    return cand
        except (OSError, json.JSONDecodeError):
            pass

    parent = root.parent
    if parent != root and (
        (parent / ".ase" / "project-memory" / "state" / "FEDERATION_STATE.json").is_file()
        or (parent / "project-memory" / "state" / "FEDERATION_STATE.json").is_file()
    ):
        return parent
    return None


def scan_topology(root: Path) -> dict[str, Any]:
    root = root.resolve()
    memory_dir = resolve_memory_dir(root)
    parent_root = detect_parent_root(root)

    candidates: list[Path] = []
    if root.is_dir():
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name.startswith(".") or child.name in IGNORED_DIRS:
                continue
            if looks_like_subproject(child):
                candidates.append(child.resolve())

    for ws_folder in discover_code_workspace_folders(root):
        if ws_folder not in candidates and ws_folder.name not in IGNORED_DIRS:
            candidates.append(ws_folder)

    member_children: list[dict[str, Any]] = []
    unmanaged_children: list[dict[str, str]] = []

    for cand in candidates:
        rel_name = cand.relative_to(root).as_posix() if root in cand.parents else cand.name
        if has_ase_installed(cand):
            c_mem = resolve_memory_dir(cand)
            nt_info = _read_child_next_task(c_mem)
            ho_info = load_child_handoff_file(cand, root)
            active_ho = None
            escalated_ho = None
            pending_ho = None
            for h in ho_info.get("handoffs", []):
                st = h.get("status", "")
                if st == "ESCALATED_TO_PARENT":
                    escalated_ho = h["handoff_id"]
                elif st in ("PENDING", "WAITING_DEPENDENCY") and pending_ho is None:
                    pending_ho = f"{h['handoff_id']} ({st}: {h.get('handoff_type', '')})"
                if st in ("ACKNOWLEDGED", "IN_PROGRESS", "IN_REVIEW"):
                    active_ho = f"{h['handoff_id']} ({st})"
            member_children.append(
                {
                    "name": cand.name,
                    "path": rel_name,
                    "abs_path": str(cand),
                    "next_task_id": nt_info["id"],
                    "next_task_status": nt_info["status"],
                    "active_handoff": active_ho or pending_ho or "none",
                    "escalated_handoff": escalated_ho or "none",
                    "handoff_count": len(ho_info.get("handoffs", [])),
                }
            )
        else:
            unmanaged_children.append(
                {
                    "name": cand.name,
                    "path": rel_name,
                    "abs_path": str(cand),
                }
            )

    fed_state_file = memory_dir / "state" / "FEDERATION_STATE.json"
    if member_children or fed_state_file.is_file() or len(member_children) + len(unmanaged_children) >= 2:
        role = "orchestrator"
    elif parent_root is not None:
        role = "member"
    else:
        role = "standalone"

    onboarding_prompt = ""
    if role == "orchestrator" and unmanaged_children:
        names = ", ".join(f"`{u['path']}`" for u in unmanaged_children)
        onboarding_prompt = (
            f"Detected {len(unmanaged_children)} unmanaged sub-project(s) without ASE installed ({names}). "
            "Ask the Human Owner if I should auto-install ASE and dispatch an `ONBOARD_ADOPT` handoff (`--onboard-child <dir>`) so they join the hierarchy."
        )

    return {
        "root": str(root),
        "role": role,
        "parent_root": str(parent_root) if parent_root else None,
        "member_children": member_children,
        "unmanaged_children": unmanaged_children,
        "onboarding_prompt": onboarding_prompt,
    }


def _read_child_next_task(memory_dir: Path) -> dict[str, str]:
    nt_path = memory_dir / "state" / "NEXT_TASK.md"
    info = {"id": "none", "status": "none", "context_alerts": "none", "pending_chain": "none"}
    if not nt_path.is_file():
        return info
    txt = nt_path.read_text(encoding="utf-8")
    m_id = re.search(r"\*\*ID:\*\*\s*`([^`]+)`", txt)
    if m_id:
        info["id"] = m_id.group(1).strip()
    m_st = re.search(r"\*\*Status:\*\*\s*`([^`]+)`", txt)
    if m_st:
        info["status"] = m_st.group(1).strip()
    m_al = re.search(r"\*\*Context Alerts:\*\*\s*([^\n]+)", txt)
    if m_al:
        info["context_alerts"] = m_al.group(1).strip().strip("`")
    m_ch = re.search(r"\*\*Pending Command Chain:\*\*\s*([^\n]+)", txt)
    if m_ch:
        info["pending_chain"] = m_ch.group(1).strip().strip("`")
    return info


def load_child_handoff_file(child_root: Path, parent_root: Path | None = None) -> dict[str, Any]:
    c_mem = resolve_memory_dir(child_root)
    ho_path = c_mem / "state" / "HANDOFF.json"
    if ho_path.is_file():
        try:
            data = json.loads(ho_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("handoffs"), list):
                return data
        except (OSError, json.JSONDecodeError):
            pass
    rel_parent = "../"
    if parent_root is not None:
        try:
            rel_parent = Path("..") .as_posix() if parent_root == child_root.parent else str(parent_root)
        except ValueError:
            rel_parent = str(parent_root)
    return {
        "schema_version": "1.0",
        "child_project": child_root.name,
        "parent_root": rel_parent,
        "last_synced_at": now_iso(),
        "active_handoff_id": None,
        "handoffs": [],
    }


def save_child_handoff_file(child_root: Path, data: dict[str, Any]) -> Path:
    c_mem = resolve_memory_dir(child_root)
    ho_path = c_mem / "state" / "HANDOFF.json"
    ho_path.parent.mkdir(parents=True, exist_ok=True)
    data["last_synced_at"] = now_iso()
    active_id = None
    for h in data.get("handoffs", []):
        if h.get("status") in ("IN_PROGRESS", "ACKNOWLEDGED", "PENDING", "ESCALATED_TO_PARENT"):
            active_id = h.get("handoff_id")
            break
    data["active_handoff_id"] = active_id
    ho_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return ho_path


def _set_child_next_task_handoff_banner(child_root: Path, banner: str, chain: str | None = None) -> None:
    c_mem = resolve_memory_dir(child_root)
    nt_path = c_mem / "state" / "NEXT_TASK.md"
    if not nt_path.is_file():
        nt_path.parent.mkdir(parents=True, exist_ok=True)
        nt_path.write_text(
            "# Next Task\n\n## Current task\n\n- **ID:** `none`\n- **File:** `none`\n- **Status:** `none`\n\n"
            "## Inner Sequence Queue & Return Stack\n\n- **Queued next in inner sequence:** `none`\n"
            "- **Return Stack (PAUSED tasks to resume):** `none`\n\n"
            "## Context Alerts & Pending Command Chain\n\n"
            f"- **Context Alerts:** `{banner}`\n"
            f"- **Pending Command Chain:** `{chain or 'none'}`\n",
            encoding="utf-8",
        )
        return
    txt = nt_path.read_text(encoding="utf-8")
    if "Context Alerts & Pending Command Chain" not in txt:
        txt = txt.rstrip("\n") + (
            "\n\n## Context Alerts & Pending Command Chain\n\n"
            "- **Context Alerts:** `none`\n"
            "- **Pending Command Chain:** `none`\n"
        )
    txt = re.sub(
        r"^(-\s*\*\*Context Alerts:\*\*\s*).*$",
        rf"\g<1>`{banner}`",
        txt,
        flags=re.MULTILINE,
    )
    if chain is not None:
        txt = re.sub(
            r"^(-\s*\*\*Pending Command Chain:\*\*\s*).*$",
            rf"\g<1>`{chain}`",
            txt,
            flags=re.MULTILINE,
        )
    nt_path.write_text(txt, encoding="utf-8")


def _allocate_next_handoff_id(parent_root: Path) -> str:
    topo = scan_topology(parent_root)
    max_num = 0
    p_mem = resolve_memory_dir(parent_root)
    fed_path = p_mem / "state" / "FEDERATION_STATE.json"
    if fed_path.is_file():
        for m in re.findall(r"HO-(\d{4})", fed_path.read_text(encoding="utf-8")):
            max_num = max(max_num, int(m))
    for mc in topo["member_children"]:
        c_path = Path(mc["abs_path"])
        ho_data = load_child_handoff_file(c_path, parent_root)
        for h in ho_data.get("handoffs", []):
            m = re.match(r"^HO-(\d{4})$", str(h.get("handoff_id", "")))
            if m:
                max_num = max(max_num, int(m.group(1)))
    return f"HO-{max_num + 1:04d}"


def _is_dependency_completed(parent_root: Path, dep_ref: str) -> bool:
    """Check whether `<child>#HO-NNNN` or `HO-NNNN` is COMPLETED."""
    if "#" in dep_ref:
        c_name, ho_id = dep_ref.split("#", 1)
        c_root = (parent_root / c_name).resolve()
        if not c_root.is_dir():
            return False
        ho_data = load_child_handoff_file(c_root, parent_root)
        for h in ho_data.get("handoffs", []):
            if h.get("handoff_id") == ho_id:
                return h.get("status") == "COMPLETED"
        return False
    topo = scan_topology(parent_root)
    for mc in topo["member_children"]:
        ho_data = load_child_handoff_file(Path(mc["abs_path"]), parent_root)
        for h in ho_data.get("handoffs", []):
            if h.get("handoff_id") == dep_ref:
                return h.get("status") == "COMPLETED"
    return False


def dispatch_handoff(
    parent_root: Path,
    child_rel: str,
    handoff_type: str,
    objective: str,
    parent_wave: str = "",
    parent_feature: str = "",
    parent_reqs: list[str] | None = None,
    parent_adrs: list[str] | None = None,
    contracts: list[str] | None = None,
    depends_on: list[str] | None = None,
    hag_approved: list[str] | None = None,
    risk: str = "medium",
    recommended_command: str | None = None,
    extra_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """T0 Dispatch: Father Orchestrator writes a typed HANDOFF.json entry to a Child project."""
    parent_root = parent_root.resolve()
    child_root = (parent_root / child_rel).resolve()
    if not child_root.is_dir():
        raise FileNotFoundError(f"Child project directory not found: {child_root}")
    if handoff_type not in VALID_HANDOFF_TYPES:
        raise ValueError(f"Invalid handoff_type '{handoff_type}'; must be one of {VALID_HANDOFF_TYPES}")
    if SECRET_RE.search(objective) or SECRET_RE.search(json.dumps(extra_payload or {})):
        raise ValueError("Blocked by HAG-03 secret-hygiene guard: handoff payload contains a secret or token.")

    ho_id = _allocate_next_handoff_id(parent_root)
    cmd = recommended_command or DEFAULT_COMMAND_BY_TYPE[handoff_type]
    deps = [d.strip() for d in (depends_on or []) if d.strip()]
    all_deps_met = all(_is_dependency_completed(parent_root, d) for d in deps)
    initial_status = "PENDING" if all_deps_met else "WAITING_DEPENDENCY"

    contract_entries: list[dict[str, str]] = []
    for c_spec in contracts or []:
        # Format: CTR-001:path/to/contract.json[:provider|consumer]
        parts = c_spec.split(":")
        c_id = parts[0].strip() if len(parts) >= 2 else "CTR-001"
        c_path_str = parts[1].strip() if len(parts) >= 2 else parts[0].strip()
        c_role = parts[2].strip() if len(parts) >= 3 else "provider"
        resolved_c = (parent_root / c_path_str).resolve()
        sha = (
            hashlib.sha256(resolved_c.read_bytes()).hexdigest()
            if resolved_c.is_file()
            else "UNRESOLVED"
        )
        contract_entries.append(
            {
                "contract_id": c_id,
                "path": c_path_str,
                "sha256": sha,
                "role": c_role,
            }
        )

    payload: dict[str, Any] = {
        "objective": objective,
        "contracts": contract_entries,
    }
    if handoff_type == "ONBOARD_ADOPT":
        payload.setdefault("context_profile", (extra_payload or {}).get("context_profile", "work"))
    elif handoff_type == "CONTEXT_MEMO_SYNC":
        payload.setdefault("source", (extra_payload or {}).get("source", "parent-orchestrator-memo"))
        payload.setdefault("memo_summary", objective)
    elif handoff_type == "TASK_OR_HOTFIX_EXECUTION":
        payload.setdefault("is_urgent_detour", bool((extra_payload or {}).get("is_urgent_detour", False)))
    if extra_payload:
        payload.update(extra_payload)

    entry: dict[str, Any] = {
        "handoff_id": ho_id,
        "handoff_type": handoff_type,
        "status": initial_status,
        "timestamps": {
            "created_at": now_iso(),
            "acknowledged_at": None,
            "completed_at": None,
        },
        "parent_refs": {
            "wave": parent_wave,
            "feature": parent_feature,
            "requirements": parent_reqs or [],
            "adrs": parent_adrs or [],
        },
        "dependencies": {
            "depends_on_handoffs": deps,
        },
        "governance": {
            "recommended_command": cmd,
            "risk": risk,
            "hag_approved_in_parent": hag_approved or [],
            "hag_required_in_child": ["HAG-01"],
        },
        "dispatch_payload": payload,
        "child_tracking": {
            "allocated_ids": [],
            "current_child_task": None,
            "current_child_status": None,
        },
        "escalation": None,
        "completion_receipt": None,
    }

    ho_data = load_child_handoff_file(child_root, parent_root)
    ho_data["handoffs"].append(entry)
    save_child_handoff_file(child_root, ho_data)

    # Link parent_root in child's .agents/.ase-install.json if present
    c_manifest = child_root / ".agents" / ".ase-install.json"
    if c_manifest.is_file():
        try:
            mdata = json.loads(c_manifest.read_text(encoding="utf-8"))
            mdata["parent_root"] = ".." if parent_root == child_root.parent else str(parent_root)
            c_manifest.write_text(json.dumps(mdata, indent=2) + "\n", encoding="utf-8")
        except (OSError, json.JSONDecodeError):
            pass

    if initial_status == "PENDING":
        _set_child_next_task_handoff_banner(
            child_root,
            f"Parent Handoff {ho_id} ({handoff_type}): {objective}",
            chain=cmd,
        )
    else:
        _set_child_next_task_handoff_banner(
            child_root,
            f"Parent Handoff {ho_id} (WAITING_DEPENDENCY on {', '.join(deps)}): {objective}",
        )

    _append_parent_handoff_ledger(parent_root, ho_id, child_root.name, handoff_type, initial_status, objective)
    rollup_federation_state(parent_root)
    return entry


def acknowledge_handoff(
    child_root: Path,
    handoff_id: str,
    allocated_ids: list[str] | None = None,
    current_task: str | None = None,
) -> dict[str, Any]:
    """T1 Acknowledge & Plan: Child ASE Lead acknowledges HO-NNNN and binds local child IDs."""
    child_root = child_root.resolve()
    ho_data = load_child_handoff_file(child_root)
    target = None
    for h in ho_data.get("handoffs", []):
        if h.get("handoff_id") == handoff_id:
            target = h
            break
    if target is None:
        raise ValueError(f"Handoff '{handoff_id}' not found in {child_root}")
    if target.get("status") == "WAITING_DEPENDENCY":
        raise ValueError(f"Handoff '{handoff_id}' is still WAITING_DEPENDENCY and cannot be started yet.")

    target["timestamps"]["acknowledged_at"] = target["timestamps"].get("acknowledged_at") or now_iso()
    if allocated_ids:
        existing = target["child_tracking"].get("allocated_ids", [])
        for aid in allocated_ids:
            if aid not in existing:
                existing.append(aid)
        target["child_tracking"]["allocated_ids"] = existing
        target["status"] = "IN_PROGRESS"
    else:
        target["status"] = "ACKNOWLEDGED"

    if current_task:
        target["child_tracking"]["current_child_task"] = current_task
        target["child_tracking"]["current_child_status"] = "IN_PROGRESS"

    save_child_handoff_file(child_root, ho_data)
    return target


def escalate_handoff(
    child_root: Path,
    handoff_id: str,
    reason: str,
    required_hag: str = "HAG-02",
    proposed_contract_change: str = "",
) -> dict[str, Any]:
    """T2 Escalation: Child pauses HO-NNNN and escalates an HAG or contract conflict up to the Father."""
    child_root = child_root.resolve()
    ho_data = load_child_handoff_file(child_root)
    for h in ho_data.get("handoffs", []):
        if h.get("handoff_id") == handoff_id:
            h["status"] = "ESCALATED_TO_PARENT"
            h["escalation"] = {
                "escalated_at": now_iso(),
                "reason": reason,
                "required_hag": required_hag,
                "proposed_contract_change": proposed_contract_change,
            }
            save_child_handoff_file(child_root, ho_data)
            _set_child_next_task_handoff_banner(
                child_root,
                f"ESCALATED {handoff_id} to Parent ({required_hag}): {reason}",
            )
            return h
    raise ValueError(f"Handoff '{handoff_id}' not found in {child_root}")


def complete_handoff(
    child_root: Path,
    handoff_id: str,
    summary_i_voice: str,
    completed_tasks: list[str] | None = None,
    fast_ci_result: str = "PASS",
    deliverables: list[str] | None = None,
) -> dict[str, Any]:
    """T3 Completion Receipt: Child writes verified completion receipt back into HANDOFF.json."""
    child_root = child_root.resolve()
    if FIRST_PERSON_PLURAL_RE.search(summary_i_voice):
        raise ValueError(
            "Violation of AGENTS.md §11: completion receipt summary must be strictly in first-person singular ('I', never 'we'/'our'/'us')."
        )
    ho_data = load_child_handoff_file(child_root)
    for h in ho_data.get("handoffs", []):
        if h.get("handoff_id") == handoff_id:
            h["status"] = "COMPLETED"
            h["timestamps"]["completed_at"] = now_iso()
            if completed_tasks:
                h["child_tracking"]["allocated_ids"] = sorted(
                    set(h["child_tracking"].get("allocated_ids", []) + completed_tasks)
                )
                h["child_tracking"]["current_child_status"] = "DONE"
            h["escalation"] = None
            h["completion_receipt"] = {
                "summary_i_voice": summary_i_voice,
                "completed_tasks": completed_tasks or h["child_tracking"].get("allocated_ids", []),
                "fast_ci_result": fast_ci_result,
                "deliverables": deliverables or [],
                "completed_at": h["timestamps"]["completed_at"],
            }
            save_child_handoff_file(child_root, ho_data)
            _set_child_next_task_handoff_banner(child_root, "none", chain="none")
            parent_root = detect_parent_root(child_root)
            if parent_root is not None:
                rollup_federation_state(parent_root)
            return h
    raise ValueError(f"Handoff '{handoff_id}' not found in {child_root}")


def _append_parent_handoff_ledger(
    parent_root: Path, ho_id: str, child_name: str, ho_type: str, status: str, objective: str
) -> None:
    p_mem = resolve_memory_dir(parent_root)
    ledger = p_mem / "state" / "HANDOFF_LEDGER.md"
    if not ledger.is_file():
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(
            "# Federated Handoff Ledger\n\n"
            "Append-only log of orders dispatched by the Father Orchestrator to Child ASE projects.\n\n"
            "| Date | Handoff ID | Target Child | Type | Status | Objective |\n"
            "|------|------------|--------------|------|--------|-----------|\n",
            encoding="utf-8",
        )
    today = now_iso()[:10]
    safe_obj = objective.replace("|", "/").replace("\n", " ").strip()
    row = f"| {today} | {ho_id} | {child_name} | {ho_type} | {status} | {safe_obj} |\n"
    ledger.write_text(ledger.read_text(encoding="utf-8").rstrip("\n") + "\n" + row, encoding="utf-8")


def rollup_federation_state(parent_root: Path) -> dict[str, Any]:
    """Zero-token rollup across all children; unblocks WAITING_DEPENDENCY handoffs and detects contract drift."""
    parent_root = parent_root.resolve()
    topo = scan_topology(parent_root)
    p_mem = resolve_memory_dir(parent_root)

    unblocked_handoffs: list[str] = []
    contract_drift_alerts: list[str] = []
    escalations: list[dict[str, str]] = []
    all_handoffs_summary: list[dict[str, Any]] = []

    # Pass 1: Check WAITING_DEPENDENCY handoffs and unblock if dependencies are COMPLETED
    for mc in topo["member_children"]:
        c_root = Path(mc["abs_path"])
        ho_data = load_child_handoff_file(c_root, parent_root)
        changed = False
        for h in ho_data.get("handoffs", []):
            deps = h.get("dependencies", {}).get("depends_on_handoffs", [])
            if h.get("status") == "WAITING_DEPENDENCY" and all(
                _is_dependency_completed(parent_root, d) for d in deps
            ):
                h["status"] = "PENDING"
                changed = True
                unblocked_handoffs.append(f"{c_root.name}#{h['handoff_id']}")
                cmd = h.get("governance", {}).get("recommended_command", "/ase-plan")
                obj = h.get("dispatch_payload", {}).get("objective", "")
                _set_child_next_task_handoff_banner(
                    c_root,
                    f"Parent Handoff {h['handoff_id']} ({h['handoff_type']}): {obj}",
                    chain=cmd,
                )

            # Check contract SHA-256 drift for active handoffs
            if h.get("status") in ("PENDING", "ACKNOWLEDGED", "IN_PROGRESS", "IN_REVIEW"):
                for ctr in h.get("dispatch_payload", {}).get("contracts", []):
                    c_path = (parent_root / ctr.get("path", "")).resolve()
                    expected_sha = ctr.get("sha256", "")
                    if c_path.is_file() and expected_sha not in ("", "UNRESOLVED"):
                        actual_sha = hashlib.sha256(c_path.read_bytes()).hexdigest()
                        if actual_sha != expected_sha:
                            contract_drift_alerts.append(
                                f"{c_root.name}#{h['handoff_id']}: contract `{ctr.get('contract_id')}` changed on disk since dispatch."
                            )

            if h.get("status") == "ESCALATED_TO_PARENT" and h.get("escalation"):
                escalations.append(
                    {
                        "child": c_root.name,
                        "handoff_id": h["handoff_id"],
                        "required_hag": h["escalation"].get("required_hag", "HAG-02"),
                        "reason": h["escalation"].get("reason", ""),
                    }
                )

            all_handoffs_summary.append(
                {
                    "child": c_root.name,
                    "handoff_id": h.get("handoff_id"),
                    "type": h.get("handoff_type"),
                    "status": h.get("status"),
                    "parent_feature": h.get("parent_refs", {}).get("feature", ""),
                    "allocated_child_ids": h.get("child_tracking", {}).get("allocated_ids", []),
                    "completed": h.get("status") == "COMPLETED",
                }
            )
        if changed:
            save_child_handoff_file(c_root, ho_data)

    # Refresh topology after any unblocking updates
    topo = scan_topology(parent_root)
    fed_state = {
        "schema_version": "1.0",
        "updated_at": now_iso(),
        "parent_root": str(parent_root),
        "role": "orchestrator",
        "member_children": topo["member_children"],
        "unmanaged_children": topo["unmanaged_children"],
        "handoffs": all_handoffs_summary,
        "unblocked_handoffs": unblocked_handoffs,
        "escalations": escalations,
        "contract_drift_alerts": contract_drift_alerts,
        "onboarding_prompt": topo["onboarding_prompt"],
    }
    fed_path = p_mem / "state" / "FEDERATION_STATE.json"
    fed_path.parent.mkdir(parents=True, exist_ok=True)
    fed_path.write_text(json.dumps(fed_state, indent=2) + "\n", encoding="utf-8")
    return fed_state


def onboard_unmanaged_child(
    parent_root: Path, child_rel: str, context_profile: str = "work"
) -> dict[str, Any]:
    """Install ASE into an unmanaged subfolder and dispatch an initial ONBOARD_ADOPT handoff."""
    parent_root = parent_root.resolve()
    child_root = (parent_root / child_rel).resolve()
    if not child_root.is_dir():
        raise FileNotFoundError(f"Sub-project directory not found: {child_root}")

    # Locate install.py (either at parent_root/install.py, parent_root/implementazione/dcp-template/install.py, or sibling)
    installer: Path | None = None
    for cand in (
        parent_root / "implementazione" / "dcp-template" / "install.py",
        parent_root / ".ase" / "template" / "install.py",
        parent_root / "install.py",
        Path(__file__).resolve().parents[1] / "install.py",
    ):
        if cand.is_file():
            installer = cand
            break

    if not has_ase_installed(child_root):
        if installer is not None:
            subprocess.run(
                [sys.executable, str(installer), str(child_root), "--no-git"],
                check=True,
                capture_output=True,
                text=True,
            )
        else:
            # Minimal fallback skeleton if install.py is not adjacent
            (child_root / ".ase" / "project-memory" / "state").mkdir(parents=True, exist_ok=True)
            (child_root / ".ase" / "project-memory" / "state" / "PROJECT_STATE.md").write_text(
                "# Project State\n\n| Gate | Status |\n|---|---|\n| M0-A | PENDING |\n",
                encoding="utf-8",
            )

    ho = dispatch_handoff(
        parent_root=parent_root,
        child_rel=child_rel,
        handoff_type="ONBOARD_ADOPT",
        objective=f"Run /ase-adopt on {child_root.name} to establish M0-A baseline and join the umbrella hierarchy.",
        extra_payload={"context_profile": context_profile},
    )
    return {"onboarded_child": child_root.name, "handoff": ho}


def query_federated_graphify(parent_root: Path, term: str) -> dict[str, Any]:
    """Query across all member children's graphify-out/graph.json files in 0 LLM tokens."""
    parent_root = parent_root.resolve()
    topo = scan_topology(parent_root)
    q_lower = term.lower().strip()
    hits_by_child: dict[str, Any] = {}
    any_god_node = False

    for mc in topo["member_children"]:
        c_root = Path(mc["abs_path"])
        g_file = c_root / "graphify-out" / "graph.json"
        if not g_file.is_file():
            continue
        try:
            gdata = json.loads(g_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        nodes = gdata.get("nodes", [])
        edges = gdata.get("links") or gdata.get("edges") or []
        deg: dict[str, int] = {}
        for e in edges:
            s, t = str(e.get("source", "")), str(e.get("target", ""))
            deg[s] = deg.get(s, 0) + 1
            deg[t] = deg.get(t, 0) + 1

        matched = []
        god_hit = False
        for n in nodes:
            nid = str(n.get("id", ""))
            hay = f"{nid} {n.get('label', '')} {n.get('source_file', '')}".lower()
            if q_lower in hay:
                matched.append(nid)
                if deg.get(nid, 0) >= 5:
                    god_hit = True
                    any_god_node = True
        if matched:
            hits_by_child[c_root.name] = {
                "matched_nodes": matched,
                "god_node_hit": god_hit,
            }

    return {
        "term": term,
        "children_matched": hits_by_child,
        "god_node_hit": any_god_node,
        "applicable_hag": "HAG-02" if any_god_node else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Workspace root directory.")
    parser.add_argument("--scan", action="store_true", help="Scan workspace hierarchy role and children.")
    parser.add_argument("--rollup", action="store_true", help="Run 0-token federation rollup and update FEDERATION_STATE.json.")
    parser.add_argument("--onboard-child", default=None, help="Install ASE into an unmanaged subfolder and dispatch ONBOARD_ADOPT.")
    parser.add_argument("--context-profile", default="work", choices=("work", "personal"))
    parser.add_argument("--dispatch", action="store_true", help="Dispatch a typed HANDOFF.json entry from Father to Child.")
    parser.add_argument("--child", default=None, help="Target child project folder name/relative path.")
    parser.add_argument("--type", default="CONTRACT_AND_PLAN", choices=VALID_HANDOFF_TYPES, help="Polymorphic handoff_type.")
    parser.add_argument("--objective", default="", help="Objective for --dispatch.")
    parser.add_argument("--wave", default="", help="Parent Wave ID (e.g. W-01).")
    parser.add_argument("--feature", default="", help="Parent Feature ID (e.g. F-001).")
    parser.add_argument("--req", action="append", default=[], help="Parent Requirement ID (repeatable).")
    parser.add_argument("--adr", action="append", default=[], help="Parent ADR ID (repeatable).")
    parser.add_argument("--contract", action="append", default=[], help="Contract spec CTR-001:path[:provider|consumer].")
    parser.add_argument("--depends-on", action="append", default=[], help="Dependency <child>#HO-NNNN (repeatable).")
    parser.add_argument("--hag-approved", action="append", default=[], help="HAGs already approved in Parent (repeatable).")
    parser.add_argument("--risk", default="medium", choices=("low", "medium", "high"))
    parser.add_argument("--ack", default=None, help="Acknowledge HO-NNNN in Child.")
    parser.add_argument("--child-ids", default="", help="Comma-separated child IDs allocated for --ack or --complete (e.g. T-0001,T-0002).")
    parser.add_argument("--escalate", default=None, help="Escalate HO-NNNN from Child to Parent.")
    parser.add_argument("--reason", default="", help="Reason for --escalate.")
    parser.add_argument("--required-hag", default="HAG-02", help="Required HAG for --escalate.")
    parser.add_argument("--complete", default=None, help="Complete HO-NNNN in Child with receipt.")
    parser.add_argument("--summary", default="", help="First-person singular ('I') completion summary for --complete.")
    parser.add_argument("--fast-ci", default="PASS", help="Fast CI result for --complete.")
    parser.add_argument("--query-graph", default=None, help="Query across all child graphify-out/graph.json files in 0 tokens.")
    parser.add_argument("--json", action="store_true", help="Output JSON.")
    args = parser.parse_args()

    try:
        if args.onboard_child:
            res = onboard_unmanaged_child(args.root, args.onboard_child, context_profile=args.context_profile)
        elif args.dispatch:
            if not args.child or not args.objective:
                sys.exit("error: --dispatch requires --child and --objective")
            res = dispatch_handoff(
                parent_root=args.root,
                child_rel=args.child,
                handoff_type=args.type,
                objective=args.objective,
                parent_wave=args.wave,
                parent_feature=args.feature,
                parent_reqs=args.req,
                parent_adrs=args.adr,
                contracts=args.contract,
                depends_on=args.depends_on,
                hag_approved=args.hag_approved,
                risk=args.risk,
            )
        elif args.ack:
            target_dir = (args.root / args.child).resolve() if args.child else args.root.resolve()
            ids = [x.strip() for x in args.child_ids.split(",") if x.strip()]
            res = acknowledge_handoff(target_dir, args.ack, allocated_ids=ids)
        elif args.escalate:
            target_dir = (args.root / args.child).resolve() if args.child else args.root.resolve()
            res = escalate_handoff(target_dir, args.escalate, reason=args.reason, required_hag=args.required_hag)
        elif args.complete:
            target_dir = (args.root / args.child).resolve() if args.child else args.root.resolve()
            ids = [x.strip() for x in args.child_ids.split(",") if x.strip()]
            res = complete_handoff(
                target_dir,
                args.complete,
                summary_i_voice=args.summary or "I completed and verified the delegated handoff tasks.",
                completed_tasks=ids,
                fast_ci_result=args.fast_ci,
            )
        elif args.query_graph is not None:
            res = query_federated_graphify(args.root, args.query_graph)
        elif args.rollup:
            res = rollup_federation_state(args.root)
        else:
            res = scan_topology(args.root)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
