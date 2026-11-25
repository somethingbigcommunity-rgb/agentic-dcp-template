#!/usr/bin/env python3
"""Deterministic Incremental Context Inbox (inputs/), Charter Patcher, Secret Guard, and Graphify Blast-Radius Helper.

Supports `/ase-memo`, `/ase-context`, and `/ase-plan` (Context & Memory Update Mode, ADR-008):
  1. Incremental SHA-256 digest tracking (`state/INPUTS_STATE.json`) so only NEW or MODIFIED files in `inputs/` are read.
  2. Secret-hygiene scanning (`HAG-03`) to prevent accidental credential/token leaks into Project Memory.
  3. Row-by-row patching of `dcp/00-project-management/project-charter.md` with automatic `HAG-03` / `HAG-04` gate protection.
  4. Append-only logging to `state/CONTEXT_LOG.md` and `Context Alerts` / `Pending Command Chain` updates in `state/NEXT_TASK.md`.
  5. Zero-token local blast-radius & God-Node lookup on `graphify-out/graph.json` (`--query-graph`) and `.graphifyignore` maintenance.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Private Key Block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("GitHub Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("OpenAI / API Secret Key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("AWS Access Key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API Key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    (
        "Inline Credential Assignment",
        re.compile(
            r"(?i)\b(?:password|passwd|secret_key|api_key|access_token|private_key)\s*[:=]\s*['\"]?[A-Za-z0-9_\-/.@#]{10,}['\"]?"
        ),
    ),
]

HAG03_CHARTER_KEYWORDS = (
    "security",
    "gdpr",
    "privacy",
    "pii",
    "auth",
    "authentication",
    "authorization",
    "data model",
    "trust boundary",
    "compliance",
)

HAG04_CHARTER_KEYWORDS = (
    "quanto",
    "cost",
    "finops",
    "budget",
    "latency",
    "sla",
    "ceiling",
    "volumetry",
    "quota",
    "token",
)

GRAPHIFY_HARNESS_EXCLUDES = [
    ".ase/templates/",
    ".ase/scripts/",
    ".ase/specs/",
    ".agents/",
    ".github/",
    "handover/",
    ".vscode/",
    "graphify-out/",
]


def resolve_memory_dir(root: Path) -> Path:
    encapsulated = root / ".ase" / "project-memory"
    if encapsulated.is_dir():
        return encapsulated
    return root / "project-memory"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scan_text_for_secrets(text: str) -> list[str]:
    findings: list[str] = []
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(label)
    return findings


def redact_secrets(text: str) -> tuple[str, list[str]]:
    redacted = text
    findings: list[str] = []
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(redacted):
            findings.append(label)
            redacted = pattern.sub("[REDACTED_SECRET]", redacted)
    return redacted, findings


def load_inputs_state(memory_dir: Path) -> dict[str, Any]:
    state_path = memory_dir / "state" / "INPUTS_STATE.json"
    if not state_path.is_file():
        return {"files": {}}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("files"), dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"files": {}}


def save_inputs_state(memory_dir: Path, data: dict[str, Any]) -> Path:
    state_path = memory_dir / "state" / "INPUTS_STATE.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return state_path


def evaluate_inputs_status(root: Path) -> dict[str, Any]:
    root = root.resolve()
    memory_dir = resolve_memory_dir(root)
    inputs_dir = root / "inputs"
    state = load_inputs_state(memory_dir)
    recorded: dict[str, Any] = state.get("files", {})

    new_files: list[str] = []
    modified_files: list[str] = []
    unchanged_files: list[str] = []
    secret_warnings: dict[str, list[str]] = {}
    current_map: dict[str, dict[str, Any]] = {}

    if inputs_dir.is_dir():
        for p in sorted(inputs_dir.rglob("*")):
            if not p.is_file() or p.name in (".gitkeep", "README.md"):
                continue
            rel = p.relative_to(inputs_dir).as_posix()
            digest = sha256_file(p)
            size = p.stat().st_size
            current_map[rel] = {"sha256": digest, "size": size}
            prev = recorded.get(rel)
            if prev is None:
                new_files.append(rel)
            elif prev.get("sha256") != digest:
                modified_files.append(rel)
            else:
                unchanged_files.append(rel)

            if rel in new_files or rel in modified_files:
                if p.suffix.lower() in (".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".env", ".py", ".sh"):
                    try:
                        txt = p.read_text(encoding="utf-8", errors="ignore")
                        sec = scan_text_for_secrets(txt)
                        if sec:
                            secret_warnings[rel] = sec
                    except OSError:
                        pass

    removed_files = sorted(set(recorded.keys()) - set(current_map.keys()))
    return {
        "inputs_dir": str(inputs_dir),
        "new_files": new_files,
        "modified_files": modified_files,
        "unchanged_files": unchanged_files,
        "removed_files": removed_files,
        "pending_count": len(new_files) + len(modified_files),
        "secret_warnings": secret_warnings,
        "_current_map": current_map,
    }


def mark_inputs_ingested(root: Path, specific_files: list[str] | None = None) -> dict[str, Any]:
    root = root.resolve()
    memory_dir = resolve_memory_dir(root)
    status = evaluate_inputs_status(root)
    current_map: dict[str, dict[str, Any]] = status["_current_map"]
    state = load_inputs_state(memory_dir)
    files_state: dict[str, Any] = dict(state.get("files", {}))
    today_str = date.today().isoformat()

    if not specific_files:
        new_files_state: dict[str, Any] = {}
        for rel, meta in current_map.items():
            prev = files_state.get(rel, {})
            new_files_state[rel] = {
                "sha256": meta["sha256"],
                "size": meta["size"],
                "ingested_at": prev.get("ingested_at", today_str)
                if prev.get("sha256") == meta["sha256"]
                else today_str,
            }
        files_state = new_files_state
        marked = sorted(current_map.keys())
    else:
        marked = []
        for item in specific_files:
            norm = item.removeprefix("inputs/").strip("/")
            if norm in current_map:
                files_state[norm] = {
                    "sha256": current_map[norm]["sha256"],
                    "size": current_map[norm]["size"],
                    "ingested_at": today_str,
                }
                marked.append(norm)

    save_inputs_state(memory_dir, {"files": files_state})
    return {"marked_ingested": marked, "total_tracked": len(files_state)}


def check_charter_key_hag(key: str) -> str | None:
    lower = key.lower()
    if any(k in lower for k in HAG03_CHARTER_KEYWORDS):
        return "HAG-03"
    if any(k in lower for k in HAG04_CHARTER_KEYWORDS):
        return "HAG-04"
    return None


def patch_charter_row_by_row(
    root: Path, patches: list[str], hag_approved: bool = False
) -> dict[str, Any]:
    root = root.resolve()
    memory_dir = resolve_memory_dir(root)
    charter_path = memory_dir / "dcp" / "00-project-management" / "project-charter.md"
    if not charter_path.is_file():
        raise FileNotFoundError(f"Charter file not found: {charter_path}")

    parsed_patches: list[tuple[str, str]] = []
    for item in patches:
        if "=" not in item:
            raise ValueError(f"Invalid --patch-charter format '{item}'; expected 'Key=Value'")
        k, v = item.split("=", 1)
        k, v = k.strip(), v.strip()
        sec = scan_text_for_secrets(v)
        if sec:
            raise ValueError(f"Blocked by HAG-03 secret-hygiene guard: value for '{k}' contains {', '.join(sec)}")
        req_hag = check_charter_key_hag(k)
        if req_hag and not hag_approved:
            raise PermissionError(
                f"BLOCKED by {req_hag}: patching charter row '{k}' modifies a protected {req_hag} constraint. "
                f"Ask the Human Owner for {req_hag} approval first, then re-run with --hag-approved."
            )
        parsed_patches.append((k, v))

    lines = charter_path.read_text(encoding="utf-8").splitlines(keepends=True)
    updated_keys: list[str] = []

    for key, val in parsed_patches:
        key_lower = key.lower()
        matched = False
        for idx, line in enumerate(lines):
            # Match table row: | **Key** | Old | or | Key | Old |
            m_tbl = re.match(r"^(\|\s*(?:\*\*)?([^|*]+?)(?:\*\*)?\s*\|\s*)([^|]*?)(\s*\|.*)$", line)
            if m_tbl and key_lower in m_tbl.group(2).strip().lower():
                ending = "\n" if line.endswith("\n") else ""
                tail = m_tbl.group(4).rstrip("\r\n")
                lines[idx] = f"{m_tbl.group(1)}{val}{tail}{ending}"
                matched = True
                updated_keys.append(key)
                break
            # Match bullet row: - **Key:** Old
            m_bul = re.match(r"^(-\s*\*\*([^*]+?)(?::)?\*\*:?\s*)(.*)$", line)
            if m_bul and key_lower in m_bul.group(2).strip().lower():
                ending = "\n" if line.endswith("\n") else ""
                lines[idx] = f"{m_bul.group(1)}{val}{ending}"
                matched = True
                updated_keys.append(key)
                break
        if not matched:
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
            lines.append(f"- **{key}:** {val}\n")
            updated_keys.append(key)

    charter_path.write_text("".join(lines), encoding="utf-8")
    return {"charter_path": str(charter_path), "updated_keys": updated_keys}


def ensure_next_task_context_section(next_task_path: Path) -> str:
    if not next_task_path.is_file():
        content = (
            "# Next Task\n\n"
            "## Current task\n\n"
            "- **ID:** `none`\n"
            "- **File:** `none`\n"
            "- **Status:** `none`\n\n"
            "## Inner Sequence Queue & Return Stack\n\n"
            "- **Queued next in inner sequence:** `none`\n"
            "- **Return Stack (PAUSED tasks to resume):** `none`\n\n"
            "## Context Alerts & Pending Command Chain\n\n"
            "- **Context Alerts:** `none`\n"
            "- **Pending Command Chain:** `none`\n"
        )
        next_task_path.parent.mkdir(parents=True, exist_ok=True)
        next_task_path.write_text(content, encoding="utf-8")
        return content

    text = next_task_path.read_text(encoding="utf-8")
    if "Inner Sequence Queue & Return Stack" not in text:
        text = text.rstrip("\n") + (
            "\n\n## Inner Sequence Queue & Return Stack\n\n"
            "- **Queued next in inner sequence:** `none`\n"
            "- **Return Stack (PAUSED tasks to resume):** `none`\n"
        )
    if "Context Alerts & Pending Command Chain" not in text:
        text = text.rstrip("\n") + (
            "\n\n## Context Alerts & Pending Command Chain\n\n"
            "- **Context Alerts:** `none`\n"
            "- **Pending Command Chain:** `none`\n"
        )
    next_task_path.write_text(text, encoding="utf-8")
    return text


def update_next_task_field(root: Path, field_label: str, new_value: str) -> Path:
    memory_dir = resolve_memory_dir(root.resolve())
    nt_path = memory_dir / "state" / "NEXT_TASK.md"
    text = ensure_next_task_context_section(nt_path)
    formatted_val = f"`{new_value}`" if not new_value.startswith("`") else new_value
    pattern = re.compile(rf"^(-\s*\*\*{re.escape(field_label)}:\*\*\s*).*$", re.MULTILINE)
    if pattern.search(text):
        text = pattern.sub(rf"\g<1>{formatted_val}", text)
    else:
        text = text.rstrip("\n") + f"\n- **{field_label}:** {formatted_val}\n"
    nt_path.write_text(text, encoding="utf-8")
    return nt_path


def append_context_log(
    root: Path,
    source: str,
    summary: str,
    updated_targets: str = "state/CONTEXT_LOG.md",
    hag_status: str = "NONE (Bucket 1 auto-applied)",
    alert_next_task: str | None = None,
    entry_date: str | None = None,
    strict_secrets: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    memory_dir = resolve_memory_dir(root)
    log_path = memory_dir / "state" / "CONTEXT_LOG.md"

    sec_findings = scan_text_for_secrets(summary) + scan_text_for_secrets(alert_next_task or "")
    if sec_findings and strict_secrets:
        raise ValueError(
            f"Blocked by HAG-03 secret-hygiene guard: input contains {', '.join(sorted(set(sec_findings)))}"
        )

    clean_summary, red_sum = redact_secrets(summary)
    clean_alert, red_alt = redact_secrets(alert_next_task or "")
    redacted_types = sorted(set(red_sum + red_alt))

    if not log_path.is_file():
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            "# Context & Memory Update Log\n\n"
            "Append-only chronological log of mid-project context updates (calls, teammate notes, screenshots, and `inputs/` files) processed via `/ase-memo`, `/ase-context`, `/ase-plan`, or natural chat.\n\n"
            "| Date | Source | Summary | Updated Targets | HAG / Chain Status |\n"
            "|------|--------|---------|-----------------|--------------------|\n",
            encoding="utf-8",
        )

    row_date = entry_date or date.today().isoformat()
    safe_source = source.replace("|", "/").strip()
    safe_summary = clean_summary.replace("|", "/").replace("\n", " ").strip()
    safe_updated = updated_targets.replace("|", "/").strip()
    safe_hag = hag_status.replace("|", "/").strip()

    row = f"| {row_date} | {safe_source} | {safe_summary} | {safe_updated} | {safe_hag} |\n"
    existing = log_path.read_text(encoding="utf-8")
    if not existing.endswith("\n"):
        existing += "\n"
    log_path.write_text(existing + row, encoding="utf-8")

    if clean_alert:
        update_next_task_field(root, "Context Alerts", clean_alert)

    return {
        "log_path": str(log_path),
        "date": row_date,
        "redacted_secrets": redacted_types,
        "alert_set": bool(clean_alert),
    }


def ensure_graphify_excludes(root: Path) -> Path:
    root = root.resolve()
    ignore_path = root / ".graphifyignore"
    existing_lines: list[str] = []
    if ignore_path.is_file():
        existing_lines = ignore_path.read_text(encoding="utf-8").splitlines()
    existing_set = {ln.strip() for ln in existing_lines if ln.strip()}
    added = False
    for item in GRAPHIFY_HARNESS_EXCLUDES:
        if item not in existing_set:
            existing_lines.append(item)
            existing_set.add(item)
            added = True
    if added or not ignore_path.is_file():
        ignore_path.write_text("\n".join(existing_lines).rstrip("\n") + "\n", encoding="utf-8")
    return ignore_path


def query_graphify_blast_radius(root: Path, term: str) -> dict[str, Any]:
    """Inspect graphify-out/graph.json locally in 0 LLM tokens to find impacted files, God Nodes, and open tasks."""
    root = root.resolve()
    memory_dir = resolve_memory_dir(root)
    graph_path = root / "graphify-out" / "graph.json"
    analysis_path = root / "graphify-out" / ".graphify_analysis.json"

    if not graph_path.is_file():
        return {
            "graph_present": False,
            "term": term,
            "matched_nodes": [],
            "neighbor_files": [],
            "god_node_hit": False,
            "applicable_hag": "",
            "impacted_tasks": [],
        }

    try:
        graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "graph_present": False,
            "term": term,
            "matched_nodes": [],
            "neighbor_files": [],
            "god_node_hit": False,
            "applicable_hag": "",
            "impacted_tasks": [],
        }

    nodes: list[dict[str, Any]] = graph_data.get("nodes", [])
    edges: list[dict[str, Any]] = graph_data.get("links") or graph_data.get("edges") or []

    degree: dict[str, int] = {}
    adj: dict[str, set[str]] = {}
    node_by_id: dict[str, dict[str, Any]] = {}
    for n in nodes:
        nid = str(n.get("id", ""))
        if nid:
            node_by_id[nid] = n
            degree[nid] = 0
            adj[nid] = set()

    for e in edges:
        src = str(e.get("source", ""))
        tgt = str(e.get("target", ""))
        if src in adj and tgt in adj:
            adj[src].add(tgt)
            adj[tgt].add(src)
            degree[src] = degree.get(src, 0) + 1
            degree[tgt] = degree.get(tgt, 0) + 1

    recorded_gods: set[str] = set()
    if analysis_path.is_file():
        try:
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
            for g in analysis.get("gods", []):
                if isinstance(g, dict) and g.get("id"):
                    recorded_gods.add(str(g["id"]))
                elif isinstance(g, str):
                    recorded_gods.add(g)
        except (OSError, json.JSONDecodeError):
            pass

    q_lower = term.lower().strip()
    matched_ids: set[str] = set()
    for nid, n in node_by_id.items():
        hay = f"{nid} {n.get('label', '')} {n.get('source_file', '')} {n.get('community_name', '')}".lower()
        if q_lower and q_lower in hay:
            matched_ids.add(nid)

    neighbor_ids: set[str] = set()
    for mid in matched_ids:
        neighbor_ids.update(adj.get(mid, set()))

    all_hit_ids = matched_ids | neighbor_ids
    god_node_hit = any(
        (nid in recorded_gods) or (degree.get(nid, 0) >= 5) for nid in matched_ids
    )

    neighbor_files: set[str] = set()
    for nid in all_hit_ids:
        sf = str(node_by_id.get(nid, {}).get("source_file", "")).strip()
        if sf:
            neighbor_files.add(sf)

    # Cross-reference with open tasks in dcp/04-implementation/tasks/
    impacted_tasks: list[str] = []
    tasks_dir = memory_dir / "dcp" / "04-implementation" / "tasks"
    if tasks_dir.is_dir():
        search_tokens = {q_lower}
        for sf in neighbor_files:
            search_tokens.add(Path(sf).name.lower())
            search_tokens.add(Path(sf).stem.lower())
        search_tokens.discard("")
        for tpath in sorted(tasks_dir.glob("*.md")):
            txt = tpath.read_text(encoding="utf-8", errors="ignore")
            m_id = re.search(r"^id:\s*(T-[0-9.]+)", txt, re.MULTILINE)
            m_st = re.search(r"^status:\s*([A-Z_]+)", txt, re.MULTILINE)
            if not m_id or not m_st:
                continue
            tid, st = m_id.group(1), m_st.group(1)
            if st not in ("TODO", "IN_PROGRESS", "PAUSED"):
                continue
            txt_lower = txt.lower()
            if any(tok in txt_lower for tok in search_tokens if len(tok) >= 3):
                impacted_tasks.append(f"{tid} ({st})")

    return {
        "graph_present": True,
        "term": term,
        "matched_nodes": sorted(matched_ids),
        "neighbor_files": sorted(neighbor_files),
        "god_node_hit": god_node_hit,
        "applicable_hag": "HAG-02" if god_node_hit else "",
        "impacted_tasks": impacted_tasks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root directory.")
    parser.add_argument("--status", action="store_true", help="Report incremental SHA-256 status of inputs/.")
    parser.add_argument(
        "--mark-ingested",
        nargs="*",
        default=None,
        help="Mark specified inputs/ files (or all current inputs/ files if no args) as ingested in INPUTS_STATE.json.",
    )
    parser.add_argument(
        "--patch-charter",
        action="append",
        default=[],
        help="Patch a row/bullet in project-charter.md ('Key=Value'). Repeatable.",
    )
    parser.add_argument(
        "--hag-approved",
        action="store_true",
        help="Confirm Human Owner approval when patching HAG-03 or HAG-04 protected charter rows.",
    )
    parser.add_argument("--append-log", action="store_true", help="Append an entry to state/CONTEXT_LOG.md.")
    parser.add_argument("--source", default="chat-note", help="Source for --append-log (e.g. call, screenshot, inputs/file.md).")
    parser.add_argument("--summary", default="", help="Summary text for --append-log.")
    parser.add_argument("--updated", default="state/CONTEXT_LOG.md", help="Updated target files/rows for --append-log.")
    parser.add_argument("--hag-status", default="NONE (Bucket 1 auto-applied)", help="HAG status for --append-log.")
    parser.add_argument("--alert-next-task", default=None, help="Set Context Alerts in state/NEXT_TASK.md.")
    parser.add_argument("--strict-secrets", action="store_true", help="Fail instead of redacting if secrets are detected.")
    parser.add_argument("--set-chain", default=None, help="Set Pending Command Chain in state/NEXT_TASK.md.")
    parser.add_argument("--clear-chain", action="store_true", help="Reset Pending Command Chain to `none` in state/NEXT_TASK.md.")
    parser.add_argument("--clear-alerts", action="store_true", help="Reset Context Alerts to `none` in state/NEXT_TASK.md.")
    parser.add_argument("--query-graph", default=None, help="Query graphify-out/graph.json in 0 tokens for blast radius.")
    parser.add_argument("--ensure-graphifyignore", action="store_true", help="Ensure .graphifyignore excludes internal ASE paths.")
    parser.add_argument("--json", action="store_true", help="Output JSON.")
    args = parser.parse_args()

    out: dict[str, Any] = {}
    try:
        if args.ensure_graphifyignore:
            ig = ensure_graphify_excludes(args.root)
            out["graphifyignore"] = str(ig)

        if args.patch_charter:
            out["charter_patch"] = patch_charter_row_by_row(
                args.root, args.patch_charter, hag_approved=args.hag_approved
            )

        if args.append_log:
            if not args.summary:
                sys.exit("error: --append-log requires --summary")
            out["context_log"] = append_context_log(
                args.root,
                source=args.source,
                summary=args.summary,
                updated_targets=args.updated,
                hag_status=args.hag_status,
                alert_next_task=args.alert_next_task,
                strict_secrets=args.strict_secrets,
            )

        if args.set_chain is not None:
            nt = update_next_task_field(args.root, "Pending Command Chain", args.set_chain)
            out["pending_command_chain"] = args.set_chain
            out["next_task_path"] = str(nt)

        if args.clear_chain:
            nt = update_next_task_field(args.root, "Pending Command Chain", "none")
            out["pending_command_chain"] = "none"
            out["next_task_path"] = str(nt)

        if args.clear_alerts:
            nt = update_next_task_field(args.root, "Context Alerts", "none")
            out["context_alerts"] = "none"
            out["next_task_path"] = str(nt)

        if args.mark_ingested is not None:
            out["mark_ingested"] = mark_inputs_ingested(args.root, args.mark_ingested)

        if args.query_graph is not None:
            out["graph_query"] = query_graphify_blast_radius(args.root, args.query_graph)

        if args.status or not out:
            st = evaluate_inputs_status(args.root)
            st.pop("_current_map", None)
            out["inputs_status"] = st

    except PermissionError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        for k, v in out.items():
            print(f"{k}: {json.dumps(v)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
