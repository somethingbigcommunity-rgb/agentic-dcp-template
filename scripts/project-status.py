#!/usr/bin/env python3
"""Deterministic daily project status, roadmap position, critical insights, and next-step reporter.

Reads Project Memory (.ase/project-memory/ or project-memory/) and Git status to
produce a structured report with:
  1. Roadmap Position & Wave/Feature Progress (including WBS inserted tasks T-NNNN.1)
  2. Active Task, Inner Sequence Queue & Return Stack
  3. Daily / Recent Activity Delta
  4. Critical Insights, Friction & Risks
  5. Next Steps (dedicated paragraph)
  6. Ready-to-Paste Daily Standup / Stakeholder Snippet (strictly "I", zero-ASE-footprint)
  7. Non-automatic proposal to save the report or stakeholder PDF
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

WBS_SUBTASK_RE = re.compile(r"^T-\d{4}(?:\.\d+)+$")
FORBIDDEN_EXTERNAL_TERMS_RE = re.compile(
    r"\b(?:Agentic Software Engineering|ASE|DCP|Development Context Package|"
    r"Project Memory|HAG-0[1-7]|Human Approval Gate|Iteration Protocol|M0-A|ase-lead)\b"
    r"|(?<![A-Za-z0-9_])/ase-[a-z-]+|project-memory/",
    re.IGNORECASE,
)


def resolve_memory_dir(root: Path) -> Path:
    encapsulated = root / ".ase" / "project-memory"
    if encapsulated.is_dir():
        return encapsulated
    return root / "project-memory"


def parse_front_matter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---(?:\s*\n|\Z)", text, re.DOTALL)
    if not match:
        return {}
    fields: dict[str, Any] = {}
    for line in match.group(1).splitlines():
        m = re.match(r"^([a-zA-Z_][\w-]*):\s*(.*)$", line)
        if m:
            k, v = m.group(1), m.group(2).strip().strip("'\"")
            fields[k] = v
    return fields


def extract_title(path: Path, identifier: str = "") -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if m:
            title = m.group(1)
            if identifier:
                title = re.sub(rf"^{re.escape(identifier)}\s+[—-]\s*", "", title)
            return title
    return identifier or path.stem


def clean_external_text(text: str) -> str:
    cleaned = FORBIDDEN_EXTERNAL_TERMS_RE.sub("", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -—:,")
    return cleaned or "project milestone"


def _wbs_sort_key(item: dict[str, Any]) -> tuple[int, ...]:
    nums = re.findall(r"\d+", item["id"])
    return tuple(int(n) for n in nums)


def collect_tasks(memory_dir: Path) -> list[dict[str, Any]]:
    tasks_dir = memory_dir / "dcp" / "04-implementation" / "tasks"
    items: list[dict[str, Any]] = []
    if not tasks_dir.is_dir():
        return items
    for path in sorted(tasks_dir.glob("*.md")):
        fm = parse_front_matter(path)
        t_id = str(fm.get("id", "")).strip()
        if not t_id:
            continue
        title = extract_title(path, t_id)
        status = str(fm.get("status", "TODO")).strip() or "TODO"
        risk = str(fm.get("risk", "low")).strip() or "low"
        parent = str(fm.get("parent", "")).strip()
        cycles_raw = str(fm.get("correction_cycles", "0")).strip()
        cycles = int(cycles_raw) if cycles_raw.isdigit() else 0
        preempted_by = str(fm.get("preempted_by", "")).strip()
        superseded_by = str(fm.get("superseded_by", "")).strip()
        deferred_to = str(fm.get("deferred_to", "")).strip()
        items.append(
            {
                "id": t_id,
                "title": title,
                "status": status,
                "risk": risk,
                "parent": parent,
                "correction_cycles": cycles,
                "is_wbs_inserted": bool(WBS_SUBTASK_RE.match(t_id)),
                "preempted_by": preempted_by,
                "superseded_by": superseded_by,
                "deferred_to": deferred_to,
                "path": path.name,
            }
        )
    items.sort(key=_wbs_sort_key)
    return items


def collect_waves_and_features(memory_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    waves_dir = memory_dir / "dcp" / "04-implementation" / "waves"
    features_dir = memory_dir / "dcp" / "04-implementation" / "features"
    waves: list[dict[str, str]] = []
    features: list[dict[str, str]] = []
    if waves_dir.is_dir():
        for p in sorted(waves_dir.glob("*.md")):
            fm = parse_front_matter(p)
            w_id = str(fm.get("id", "")).strip()
            if w_id:
                waves.append(
                    {
                        "id": w_id,
                        "title": extract_title(p, w_id),
                        "status": str(fm.get("status", "TODO")).strip() or "TODO",
                    }
                )
    if features_dir.is_dir():
        for p in sorted(features_dir.glob("*.md")):
            fm = parse_front_matter(p)
            f_id = str(fm.get("id", "")).strip()
            if f_id:
                features.append(
                    {
                        "id": f_id,
                        "title": extract_title(p, f_id),
                        "parent": str(fm.get("parent", "")).strip(),
                        "status": str(fm.get("status", "TODO")).strip() or "TODO",
                    }
                )
    return waves, features


def parse_task_log(memory_dir: Path) -> list[dict[str, str]]:
    log_path = memory_dir / "state" / "TASK_LOG.md"
    entries: list[dict[str, str]] = []
    if not log_path.is_file():
        return entries
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [c.strip() for c in line.split("|")[1:-1]]
        if len(parts) >= 7 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts[0]):
            entries.append(
                {
                    "date": parts[0],
                    "task": parts[1],
                    "parent": parts[2],
                    "engine": parts[3],
                    "outcome": parts[4],
                    "cycles": parts[5],
                    "note": parts[6],
                }
            )
    return entries


def parse_next_task(memory_dir: Path) -> dict[str, str]:
    path = memory_dir / "state" / "NEXT_TASK.md"
    info = {
        "current_id": "none",
        "current_status": "none",
        "queued_sequence": "none",
        "return_stack": "none",
        "context_alerts": "none",
        "pending_chain": "none",
    }
    if not path.is_file():
        return info
    text = path.read_text(encoding="utf-8")
    m_id = re.search(r"\*\*ID:\*\*\s*`([^`]+)`", text)
    if m_id:
        info["current_id"] = m_id.group(1).strip()
    m_st = re.search(r"\*\*Status:\*\*\s*`([^`]+)`", text)
    if m_st:
        info["current_status"] = m_st.group(1).strip()
    m_q = re.search(r"\*\*Queued next in inner sequence:\*\*\s*([^\n]+)", text)
    if m_q:
        info["queued_sequence"] = m_q.group(1).strip().strip("`")
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


def parse_context_log(memory_dir: Path) -> list[dict[str, str]]:
    log_path = memory_dir / "state" / "CONTEXT_LOG.md"
    entries: list[dict[str, str]] = []
    if not log_path.is_file():
        return entries
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [c.strip() for c in line.split("|")[1:-1]]
        if len(parts) >= 5 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts[0]):
            entries.append(
                {
                    "date": parts[0],
                    "source": parts[1],
                    "summary": parts[2],
                    "updated": parts[3],
                    "hag_status": parts[4],
                }
            )
    return entries


def inspect_graphify_summary(root: Path) -> dict[str, Any]:
    graph_path = root / "graphify-out" / "graph.json"
    cost_path = root / "graphify-out" / "cost.json"
    if not graph_path.is_file():
        return {"enabled": False}
    try:
        gdata = json.loads(graph_path.read_text(encoding="utf-8"))
        nodes = len(gdata.get("nodes", []))
        edges = len(gdata.get("links") or gdata.get("edges") or [])
    except (OSError, json.JSONDecodeError):
        return {"enabled": False}
    in_tok = 0
    out_tok = 0
    if cost_path.is_file():
        try:
            cdata = json.loads(cost_path.read_text(encoding="utf-8"))
            in_tok = int(cdata.get("total_input_tokens", 0))
            out_tok = int(cdata.get("total_output_tokens", 0))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "enabled": True,
        "nodes": nodes,
        "edges": edges,
        "total_input_tokens": in_tok,
        "total_output_tokens": out_tok,
    }


def collect_known_issues(memory_dir: Path) -> list[str]:
    path = memory_dir / "state" / "KNOWN_ISSUES.md"
    if not path.is_file():
        return []
    issues: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and "none" not in stripped.lower():
            issues.append(stripped[2:].strip())
    return issues


def inspect_federation_summary(root: Path, memory_dir: Path) -> dict[str, Any]:
    fed_path = memory_dir / "state" / "FEDERATION_STATE.json"
    ho_path = memory_dir / "state" / "HANDOFF.json"
    if fed_path.is_file():
        try:
            fdata = json.loads(fed_path.read_text(encoding="utf-8"))
            return {
                "role": "orchestrator",
                "member_children": fdata.get("member_children", []),
                "unmanaged_children": fdata.get("unmanaged_children", []),
                "handoffs": fdata.get("handoffs", []),
                "escalations": fdata.get("escalations", []),
                "contract_drift_alerts": fdata.get("contract_drift_alerts", []),
            }
        except (OSError, json.JSONDecodeError):
            pass
    if ho_path.is_file():
        try:
            hdata = json.loads(ho_path.read_text(encoding="utf-8"))
            return {
                "role": "member",
                "parent_root": hdata.get("parent_root"),
                "active_handoff_id": hdata.get("active_handoff_id"),
                "handoffs": hdata.get("handoffs", []),
            }
        except (OSError, json.JSONDecodeError):
            pass
    return {"role": "standalone"}


def build_status_report(root: Path, target_date: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    memory_dir = resolve_memory_dir(root)
    encapsulated = (root / ".ase" / "project-memory").is_dir()
    artifacts_dir = "deliverables/04-verification"

    tasks = collect_tasks(memory_dir)
    waves, features = collect_waves_and_features(memory_dir)
    log_entries = parse_task_log(memory_dir)
    context_entries = parse_context_log(memory_dir)
    next_task = parse_next_task(memory_dir)
    known_issues = collect_known_issues(memory_dir)
    graphify_info = inspect_graphify_summary(root)
    federation_info = inspect_federation_summary(root, memory_dir)

    counts: dict[str, int] = {
        "DONE": 0,
        "IN_PROGRESS": 0,
        "IN_REVIEW": 0,
        "PAUSED": 0,
        "TODO": 0,
        "BLOCKED": 0,
        "DEFERRED": 0,
        "SUPERSEDED": 0,
    }
    for t in tasks:
        st = t["status"]
        counts[st] = counts.get(st, 0) + 1

    active_total = sum(
        counts[k] for k in ("DONE", "IN_PROGRESS", "IN_REVIEW", "PAUSED", "TODO", "BLOCKED")
    )
    completion_pct = round((counts["DONE"] / active_total) * 100) if active_total > 0 else 0

    wbs_inserted_tasks = [t for t in tasks if t["is_wbs_inserted"]]
    paused_tasks = [t for t in tasks if t["status"] == "PAUSED"]
    blocked_tasks = [t for t in tasks if t["status"] == "BLOCKED"]
    superseded_tasks = [t for t in tasks if t["status"] == "SUPERSEDED"]
    deferred_tasks = [t for t in tasks if t["status"] == "DEFERRED"]
    friction_tasks = [t for t in tasks if t["correction_cycles"] > 0]
    high_risk_open = [
        t
        for t in tasks
        if t["risk"] == "high" and t["status"] in ("TODO", "IN_PROGRESS", "IN_REVIEW", "PAUSED")
    ]

    active_date = target_date or (log_entries[-1]["date"] if log_entries else "today")
    daily_entries = [e for e in log_entries if e["date"] == active_date]

    git_res = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    dirty_files = (
        len([ln for ln in git_res.stdout.splitlines() if ln.strip()])
        if git_res.returncode == 0
        else 0
    )

    insights: list[str] = []
    if blocked_tasks:
        ids = ", ".join(t["id"] for t in blocked_tasks)
        insights.append(f"BLOCKED tasks requiring human decision: {ids}.")
    if wbs_inserted_tasks:
        ids = ", ".join(f"{t['id']} ({t['status']})" for t in wbs_inserted_tasks)
        insights.append(
            f"Roadmap detours / inner WBS sequences detected ({len(wbs_inserted_tasks)} inserted task(s)): {ids}."
        )
    if paused_tasks:
        ids = ", ".join(t["id"] for t in paused_tasks)
        insights.append(f"Paused task(s) on the Return Stack awaiting inner sequence completion: {ids}.")
    if superseded_tasks or deferred_tasks:
        insights.append(
            f"Roadmap pivot adjustments: {len(superseded_tasks)} superseded, {len(deferred_tasks)} deferred."
        )
    if friction_tasks:
        ids = ", ".join(f"{t['id']} ({t['correction_cycles']} cycle(s))" for t in friction_tasks)
        insights.append(f"Verification friction hotspots: {ids}.")
    if high_risk_open:
        ids = ", ".join(t["id"] for t in high_risk_open)
        insights.append(f"Open high-risk task(s) requiring extra verification controls: {ids}.")
    if known_issues:
        insights.append(f"Known issues recorded ({len(known_issues)}): {known_issues[0]}")
    if next_task.get("context_alerts", "none") not in ("none", ""):
        insights.append(f"Active Context Alert on `NEXT_TASK.md`: {next_task['context_alerts']}")
    if next_task.get("pending_chain", "none") not in ("none", ""):
        insights.append(f"Pending Command Chain awaiting approval: {next_task['pending_chain']}")
    if graphify_info.get("enabled"):
        insights.append(
            f"Graphify Knowledge Graph active: {graphify_info['nodes']} nodes, {graphify_info['edges']} edges "
            f"(cumulative tokens: {graphify_info['total_input_tokens']} in / {graphify_info['total_output_tokens']} out)."
        )
    if federation_info.get("role") == "orchestrator":
        m_cnt = len(federation_info.get("member_children", []))
        u_cnt = len(federation_info.get("unmanaged_children", []))
        esc = federation_info.get("escalations", [])
        insights.append(
            f"Federated Umbrella Orchestrator active: {m_cnt} member child project(s), {u_cnt} unmanaged child folder(s), {len(esc)} escalation(s)."
        )
    elif federation_info.get("role") == "member" and federation_info.get("active_handoff_id"):
        insights.append(
            f"Federated Child Member active handoff from Parent: `{federation_info['active_handoff_id']}`."
        )
    if not insights:
        insights.append(
            "Execution is on track with zero blocked tasks, zero verification friction cycles, and no unplanned drift."
        )

    cur_id = next_task["current_id"]
    cur_status = next_task["current_status"]
    queued_seq = next_task["queued_sequence"]
    ret_stack = next_task["return_stack"]

    if cur_id != "none" and cur_status == "IN_REVIEW":
        next_steps_paragraph = (
            f"Review and accept the diff for `{cur_id}` (`IN_REVIEW`) so it can be marked `DONE` and logged. "
            + (
                f"Once `{cur_id}` closes, the next queued inner-sequence task is `{queued_seq}`."
                if queued_seq != "none"
                else (
                    f"Once `{cur_id}` closes, resume `{ret_stack}` from the Return Stack."
                    if ret_stack != "none"
                    else "After closing the task, run `/ase-plan` for the next increment or `/ase-review` if the Work Package is complete."
                )
            )
        )
    elif cur_id != "none" and cur_status in ("TODO", "IN_PROGRESS"):
        next_steps_paragraph = (
            f"Run `/ase-task` to complete `{cur_id}` (`{cur_status}`). "
            + (
                f"After `{cur_id}`, complete queued inner step `{queued_seq}`"
                + (f" and then resume `{ret_stack}` from the Return Stack." if ret_stack != "none" else ".")
                if queued_seq != "none"
                else (
                    f"After `{cur_id}` finishes, pop the Return Stack and resume `{ret_stack}`."
                    if ret_stack != "none"
                    else "Once verified, proceed to the next planned backlog item."
                )
            )
        )
    elif paused_tasks:
        p_id = paused_tasks[0]["id"]
        next_steps_paragraph = (
            f"Resume paused task `{p_id}` via `/ase-task` or insert any remaining prerequisite step via `/ase-plan`."
        )
    else:
        todo_list = [t["id"] for t in tasks if t["status"] == "TODO"]
        if todo_list:
            next_steps_paragraph = (
                f"Assign `{todo_list[0]}` in `NEXT_TASK.md` and execute it with `/ase-task`."
            )
        else:
            next_steps_paragraph = (
                "All currently planned tasks are complete. Run `/ase-review` to close and package the delivery, "
                "or run `/ase-plan` to plan the next Wave or Feature."
            )

    done_titles = [
        f"{t['id']} ({clean_external_text(t['title'])})"
        for t in tasks
        if t["status"] == "DONE"
    ]
    active_tasks = [
        f"{t['id']} ({clean_external_text(t['title'])})"
        for t in tasks
        if t["status"] in ("IN_PROGRESS", "IN_REVIEW", "TODO")
    ]
    standup_completed = (
        ", ".join(done_titles[-3:]) if done_titles else "initial project baseline setup"
    )
    standup_current = (
        ", ".join(active_tasks[:2])
        if active_tasks
        else "final verification and delivery handover"
    )
    standup_insight = (
        f"I inserted {len(wbs_inserted_tasks)} targeted sub-task(s) ({', '.join(t['id'] for t in wbs_inserted_tasks)}) to resolve intermediate findings cleanly before resuming the main roadmap."
        if wbs_inserted_tasks
        else "All planned deliverables are progressing on schedule with no blocking issues."
    )
    standup_snippet = (
        f"- **Completed:** I completed {standup_completed} ({completion_pct}% of planned scope done).\n"
        f"- **Current Focus & Next Steps:** I am currently working on {standup_current}, after which I will proceed with the next scheduled milestone.\n"
        f"- **Key Insights & Risks:** {standup_insight}"
    )

    return {
        "date": active_date,
        "encapsulated": encapsulated,
        "artifacts_dir": artifacts_dir,
        "counts": counts,
        "active_total": active_total,
        "completion_pct": completion_pct,
        "waves": waves,
        "features": features,
        "tasks": tasks,
        "wbs_inserted_tasks": [t["id"] for t in wbs_inserted_tasks],
        "next_task": next_task,
        "daily_entries": daily_entries,
        "context_entries": context_entries[-5:],
        "graphify": graphify_info,
        "federation": federation_info,
        "dirty_files": dirty_files,
        "insights": insights,
        "next_steps": next_steps_paragraph,
        "standup_snippet": standup_snippet,
    }


def format_markdown(report: dict[str, Any]) -> str:
    c = report["counts"]
    nt = report["next_task"]
    lines = [
        f"# Daily Project Situation Report ({report['date']})",
        "",
        "## 1. Roadmap Position & Progress",
        "",
        f"- **Overall Task Completion:** **{report['completion_pct']}%** "
        f"(`{c['DONE']}/{report['active_total']}` active tasks `DONE`)",
        f"- **Status Breakdown:** `DONE: {c['DONE']}` | `IN_PROGRESS: {c['IN_PROGRESS']}` | "
        f"`IN_REVIEW: {c['IN_REVIEW']}` | `PAUSED: {c['PAUSED']}` | `TODO: {c['TODO']}` | "
        f"`BLOCKED: {c['BLOCKED']}` | `DEFERRED: {c['DEFERRED']}` | `SUPERSEDED: {c['SUPERSEDED']}`",
        f"- **Inserted WBS Sub-Tasks (`T-NNNN.1`):** "
        + (
            ", ".join(f"`{tid}`" for tid in report["wbs_inserted_tasks"])
            if report["wbs_inserted_tasks"]
            else "`none` (roadmap matches initial task sequence)"
        ),
    ]
    if report["waves"]:
        lines.append(
            "- **Waves:** "
            + ", ".join(f"`{w['id']}` ({w['title']} — `{w['status']}`)" for w in report["waves"])
        )
    if report["features"]:
        lines.append(
            "- **Features / Work Packages:** "
            + ", ".join(f"`{f['id']}` ({f['title']} — `{f['status']}`)" for f in report["features"])
        )

    lines.extend(
        [
            "",
            "## 2. Active Task, Inner Sequence Queue & Return Stack",
            "",
            f"- **Active Task:** `{nt['current_id']}` (`{nt['current_status']}`)",
            f"- **Queued Next in Inner Sequence:** `{nt['queued_sequence']}`",
            f"- **Return Stack (`PAUSED` tasks to resume):** `{nt['return_stack']}`",
            f"- **Context Alerts:** `{nt.get('context_alerts', 'none')}`",
            f"- **Pending Command Chain:** `{nt.get('pending_chain', 'none')}`",
            "",
            "## 3. Daily / Recent Activity Delta",
            "",
            f"- **Working Tree Uncommitted Files:** `{report['dirty_files']}`",
        ]
    )
    if report["daily_entries"]:
        for entry in report["daily_entries"]:
            lines.append(
                f"- **`{entry['date']}` — `{entry['task']}` (`{entry['outcome']}`, "
                f"cycles: `{entry['cycles']}`):** {entry['note']}"
            )
    else:
        lines.append("- No closed task log entries recorded for this date yet.")

    lines.extend(["", "## 4. Critical Insights, Friction & Risks", ""])
    for insight in report["insights"]:
        lines.append(f"- {insight}")

    lines.extend(
        [
            "",
            "## 5. Next Steps",
            "",
            report["next_steps"],
            "",
            "## 6. Daily Standup / Stakeholder Update (First-Person Singular `\"I\"`)",
            "",
            report["standup_snippet"],
            "",
            "---",
            f"*Optional deliverable proposal:* Do you want me to save this report to "
            f"`{report['artifacts_dir']}/status-{report['date']}.md` or generate an executive "
            f"stakeholder PDF via `build-stakeholder-pdf.py`?",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: current directory).",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Optional YYYY-MM-DD date filter for the daily activity delta.",
    )
    parser.add_argument(
        "--write-report",
        type=Path,
        default=None,
        help="Explicitly write the Markdown report to this path (use only after Human Owner confirmation).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON.",
    )
    args = parser.parse_args()

    report = build_status_report(args.root, args.date)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        md = format_markdown(report)
        if args.write_report is not None:
            out_path = (
                args.write_report
                if args.write_report.is_absolute()
                else args.root.resolve() / args.write_report
            )
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(md + "\n", encoding="utf-8")
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
