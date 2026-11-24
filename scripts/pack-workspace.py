#!/usr/bin/env python3
"""In-place post-work deliverable curator and workspace Explorer cleaner (/ase-pack).

Responsibilities (strictly non-overlapping with /ase-review and /ase-export):
  1. Verifies Step 0 prerequisites via check-prereq.py --command ase-pack.
  2. Curates root deliverables/ (01-discovery .. 05-release-and-handover), migrating
     any legacy .ase/artifacts/ files if present.
  3. Generates deliverables/INDEX.md in first-person singular ("I", zero-ASE-footprint)
     summarizing completed work, run/test commands, deliverable links, and project modules.
  4. Updates .vscode/settings.json (files.exclude) to hide internal ASE harness folders
     and any empty deliverables/0X-* sub-folders so the IDE Explorer shows only real
     project files and populated deliverables.
  5. Verifies deliverables/ with verify-external-clean.py --check-first-person and writes
     state/PACK_STATE.json so /ase-export knows the workspace package is fresh.
"""

from __future__ import annotations

import argparse
from datetime import date
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

LIFECYCLE_DIRS = (
    ("01-discovery", "Discovery & As-Is Baseline"),
    ("02-planning", "Project Plan, Requirements & Roadmap"),
    ("03-architecture", "Architecture & Security Design"),
    ("04-verification", "Verification, Reconciliation & Status Reports"),
    ("05-release-and-handover", "Release Acceptance & Handover Notes"),
)

FORBIDDEN_EXTERNAL_TERMS_RE = re.compile(
    r"\b(?:Agentic Software Engineering|ASE|agentic-dcp-template|dcp-template|"
    r"Development Context Package|DCP|Project Memory|HAG-0[1-7]|"
    r"Human Approval Gate|Iteration Protocol|M0-A|ase-lead)\b"
    r"|(?<![A-Za-z0-9_])/ase-[a-z-]+|project-memory/|\.ase-install\.json",
    re.IGNORECASE,
)
FIRST_PERSON_PLURAL_RE = re.compile(
    r"\b(?:we|we've|we're|we'll|our|ours|us|noi|abbiamo|nostro|nostra|nostri|nostre)\b",
    re.IGNORECASE,
)

INTERNAL_ROOT_DIRS = {
    ".ase",
    ".agents",
    ".github",
    ".vscode",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".git",
    "graphify-out",
    "deliverables",
    "artifacts",
    "handover",
    "project-memory",
    "templates",
    "scripts",
}


def _load_sibling_module(name: str, filename: str):
    path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load helper {filename}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def resolve_memory_dir(root: Path) -> Path:
    encapsulated = root / ".ase" / "project-memory"
    if encapsulated.is_dir():
        return encapsulated
    return root / "project-memory"


def clean_external_text(text: str) -> str:
    cleaned = FORBIDDEN_EXTERNAL_TERMS_RE.sub("", text)
    cleaned = FIRST_PERSON_PLURAL_RE.sub("I", cleaned)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -—:,")
    return cleaned or "Project deliverable"


def parse_agents_settings(root: Path) -> dict[str, str]:
    setting_re = re.compile(r"^\|\s*(?P<name>[^|]+?)\s*\|\s*`(?P<value>[^`]*)`", re.MULTILINE)
    for candidate in (root / "AGENTS.md", root / ".agents" / "AGENTS.md", root / ".ase" / "AGENTS.md"):
        if candidate.is_file():
            settings: dict[str, str] = {}
            for m in setting_re.finditer(candidate.read_text(encoding="utf-8")):
                k = m.group("name").strip().lower()
                v = m.group("value").strip()
                if v and not v.startswith("<"):
                    settings[k] = v
            if settings:
                return settings
    return {}


def migrate_legacy_artifacts(root: Path, deliv_dir: Path) -> None:
    """Copy any non-.gitkeep deliverable files from legacy .ase/artifacts/ or artifacts/ into deliverables/."""
    for legacy in (root / ".ase" / "artifacts", root / "artifacts"):
        if not legacy.is_dir() or legacy.resolve() == deliv_dir.resolve():
            continue
        for folder, _ in LIFECYCLE_DIRS:
            src_sub = legacy / folder
            if not src_sub.is_dir():
                continue
            dst_sub = deliv_dir / folder
            dst_sub.mkdir(parents=True, exist_ok=True)
            for item in src_sub.rglob("*"):
                if item.is_file() and item.name != ".gitkeep":
                    rel = item.relative_to(src_sub)
                    target = dst_sub / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists():
                        shutil.copy2(item, target)


def update_vscode_excludes(root: Path, empty_deliv_subdirs: list[str], hide_harness: bool = True) -> Path:
    vscode_dir = root / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    settings_path = vscode_dir / "settings.json"
    data: dict[str, Any] = {}
    if settings_path.is_file():
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}

    excludes: dict[str, bool] = dict(data.get("files.exclude", {}))
    manifest_path = root / ".agents" / ".ase-install.json"
    installed_files: dict[str, Any] = {}
    if manifest_path.is_file():
        try:
            installed_files = json.loads(manifest_path.read_text(encoding="utf-8")).get("files", {})
        except (OSError, json.JSONDecodeError):
            installed_files = {}

    harness_keys = [
        ".ase",
        ".agents",
        ".github/agents",
        ".github/instructions",
        ".vscode",
        ".venv",
        ".mcp.json",
        "graphify-out",
    ]
    if "AGENTS.md" in installed_files or not (root / ".agents" / "AGENTS.md").is_file():
        harness_keys.append("AGENTS.md")
    if (root / "project-memory").is_dir():
        harness_keys.append("project-memory")
    if (root / "templates").is_dir():
        harness_keys.append("templates")
    if (root / "scripts" / "next-id.py").is_file():
        harness_keys.append("scripts")
    if (root / "artifacts").is_dir():
        harness_keys.append("artifacts")

    for k in harness_keys:
        if hide_harness:
            excludes[k] = True
        else:
            excludes.pop(k, None)

    for folder, _ in LIFECYCLE_DIRS:
        key = f"deliverables/{folder}"
        if folder in empty_deliv_subdirs and hide_harness:
            excludes[key] = True
        else:
            excludes.pop(key, None)

    data["files.exclude"] = excludes
    settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return settings_path


def collect_project_modules(root: Path) -> list[str]:
    modules: list[str] = []
    for item in sorted(root.iterdir()):
        if item.name.startswith(".") or item.name in INTERNAL_ROOT_DIRS:
            continue
        if item.is_dir():
            modules.append(f"`{item.name}/`")
        elif item.is_file():
            modules.append(f"`{item.name}`")
    return modules


def pack_workspace(root: Path, skip_prereq: bool = False) -> dict[str, Any]:
    root = root.resolve()
    prereq_mod = _load_sibling_module("check_prereq", "check-prereq.py")
    if not skip_prereq:
        prereq_res = prereq_mod.evaluate_prerequisites(root, "ase-pack")
        if not prereq_res["ok"]:
            raise RuntimeError(prereq_mod.format_report(prereq_res))

    memory_dir = resolve_memory_dir(root)
    deliv_dir = root / "deliverables"
    deliv_dir.mkdir(parents=True, exist_ok=True)
    for folder, _ in LIFECYCLE_DIRS:
        sub = deliv_dir / folder
        sub.mkdir(parents=True, exist_ok=True)
        gitkeep = sub / ".gitkeep"
        if not any(sub.iterdir()):
            gitkeep.write_text("", encoding="utf-8")

    migrate_legacy_artifacts(root, deliv_dir)

    populated_sections: list[tuple[str, str, list[Path]]] = []
    empty_subdirs: list[str] = []
    for folder, label in LIFECYCLE_DIRS:
        sub = deliv_dir / folder
        files = sorted(
            p for p in sub.rglob("*") if p.is_file() and p.name != ".gitkeep"
        )
        if files:
            populated_sections.append((folder, label, files))
        else:
            empty_subdirs.append(folder)

    tasks_dir = memory_dir / "dcp" / "04-implementation" / "tasks"
    completed_items: list[tuple[str, str]] = []
    if tasks_dir.is_dir():
        for p in sorted(tasks_dir.glob("*.md")):
            fm = prereq_mod.parse_front_matter(p)
            tid = fm.get("id", "").strip()
            st = fm.get("status", "").strip()
            if tid and st == "DONE":
                title = tid
                for ln in p.read_text(encoding="utf-8").splitlines():
                    m = re.match(r"^#{1,6}\s+(.+?)\s*$", ln)
                    if m:
                        raw_title = re.sub(rf"^{re.escape(tid)}\s+[—-]\s*", "", m.group(1))
                        title = clean_external_text(raw_title)
                        break
                completed_items.append((tid, title))

    settings = parse_agents_settings(root)
    stack = clean_external_text(settings.get("stack", "Standard project stack"))
    fast_cmd = settings.get("fast ci command", "none")

    modules = collect_project_modules(root)
    today_str = date.today().isoformat()

    lines = [
        f"# Project Deliverables & Work Overview — `{root.name}`",
        "",
        f"*Prepared on {today_str}.*",
        "",
        "## 1. Executive Summary of Completed Work",
        "",
        f"I completed and verified the planned work packages for `{root.name}` using `{stack}`.",
        "",
    ]
    if completed_items:
        for tid, title in completed_items:
            lines.append(f"- **`{tid}`:** I implemented and verified *{title}*.")
    else:
        lines.append("- I completed the initial baseline and project verification.")

    lines.extend(
        [
            "",
            "## 2. How to Run & Verify the Project",
            "",
            f"- **Technology Stack:** `{stack}`",
            f"- **Verification / Test Command:** `{fast_cmd}`",
            "",
            "## 3. Lifecycle Deliverables (`deliverables/`)",
            "",
        ]
    )
    if populated_sections:
        for folder, label, files in populated_sections:
            lines.append(f"### `{folder}/` — {label}")
            for fpath in files:
                rel = fpath.relative_to(deliv_dir).as_posix()
                lines.append(f"- [{fpath.name}]({rel})")
            lines.append("")
    else:
        lines.append(
            "- No standalone reports or PDFs have been generated in `01-discovery/` .. `05-release-and-handover/` yet."
        )
        lines.append("")

    lines.extend(["## 4. Project Workspace Modules", ""])
    if modules:
        lines.append("- **Top-level project files & directories:** " + ", ".join(modules))
    else:
        lines.append("- See the root repository tree for project source files.")

    index_path = deliv_dir / "INDEX.md"
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    settings_path = update_vscode_excludes(root, empty_subdirs, hide_harness=True)

    clean_script = Path(__file__).resolve().parent / "verify-external-clean.py"
    clean_res = subprocess.run(
        [sys.executable, str(clean_script), "--check-first-person", str(deliv_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if clean_res.returncode != 0:
        raise RuntimeError(
            f"External-clean verification failed on deliverables/:\n{clean_res.stderr or clean_res.stdout}"
        )

    digest = prereq_mod.compute_workspace_pack_digest(root, memory_dir)
    pack_state = {
        "packed_at": today_str,
        "project": root.name,
        "workspace_digest": digest,
        "deliverables_dir": "deliverables",
        "index_file": "deliverables/INDEX.md",
        "populated_folders": [f for f, _, _ in populated_sections],
        "hidden_empty_folders": empty_subdirs,
    }
    state_dir = memory_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    pack_state_path = state_dir / "PACK_STATE.json"
    pack_state_path.write_text(json.dumps(pack_state, indent=2) + "\n", encoding="utf-8")

    return {
        **pack_state,
        "vscode_settings": str(settings_path.relative_to(root)),
        "completed_tasks_count": len(completed_items),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: current directory).",
    )
    parser.add_argument(
        "--skip-prereq",
        action="store_true",
        help="Skip Step 0 check-prereq validation.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON.",
    )
    args = parser.parse_args()

    try:
        result = pack_workspace(args.root, skip_prereq=args.skip_prereq)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(
            f"PASS: Workspace packed in-place (`deliverables/INDEX.md`, `{result['vscode_settings']}`, "
            "and `state/PACK_STATE.json` updated; zero-ASE-footprint verified).\n\n"
            "Your workspace and `deliverables/` are packed and clean. "
            "Do you also need a `.zip` bundle to send to a stakeholder? "
            "If yes, confirm and I will run `/ase-export` (`python3 scripts/export-handover.py`)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
