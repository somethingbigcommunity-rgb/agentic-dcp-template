#!/usr/bin/env python3
"""Deterministic Change-Data-Capture (CDC) & Row-by-Row In-Flight Release Switcher (/ase-switch).

Upgrades an ongoing project from an older ASE release to a newly cloned ASE release
in the workspace root without destroying and recreating unchanged files:
  1. Auto-discovers the cloned ASE release directory in the workspace root (or --from-release).
  2. Stages only files slated for modification/relocation in a temporary /tmp rollback buffer.
  3. Applies 4-Mode CDC:
     - Mode A (UNCHANGED): 0 disk writes (inode & mtime preserved).
     - Mode B (ROW / SECTION PATCH): updates AGENTS.md row-by-row (preserving Project
       configuration values and custom user sections), patches NEXT_TASK.md in place
       (preserving the active task while adding Return Stack rows if missing), and
       synthesizes project-charter.md if absent (marking uncollected rows SKIPPED).
     - Mode C (LINE-DIFF UPDATE): patches only changed harness scripts/skills/agents/templates.
     - Mode D (SELECTIVE RELOCATION & GHOST PURGE): moves only paths whose canonical
       location changed (.ase/artifacts/01..05 -> deliverables/01..05, .ase/artifacts/specs
       -> .ase/specs, or legacy --flat root project-memory/ -> .ase/project-memory/),
       deletes retired manifest files and empty legacy directories, and deletes the
       cloned release folder + /tmp buffer once verification passes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

LIFECYCLE_FOLDERS = (
    "01-discovery",
    "02-planning",
    "03-architecture",
    "04-verification",
    "05-release-and-handover",
)
SETTING_ROW_RE = re.compile(
    r"^(?P<prefix>\|\s*(?P<name>[^|]+?)\s*\|\s*)(?:`(?P<value>[^`]*)`|(?P<placeholder>_to be defined in P0_))(?P<suffix>.*)$"
)
VERSION_RE = re.compile(r"\bv?(\d+\.\d+\.\d+)\b")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_release_version(source_dir: Path) -> str:
    for rel in ("RELEASE-NOTES.md", "README.md"):
        p = source_dir / rel
        if p.is_file():
            m = VERSION_RE.search(p.read_text(encoding="utf-8", errors="ignore"))
            if m:
                return f"v{m.group(1)}"
    return "v0.4.0"


def is_valid_release_dir(cand: Path) -> bool:
    return (
        cand.is_dir()
        and (cand / "install.py").is_file()
        and (cand / "AGENTS.md").is_file()
        and (cand / ".agents" / "skills").is_dir()
        and (cand / "project-memory").is_dir()
    )


def discover_cloned_release(root: Path, explicit_source: Path | None = None) -> Path | None:
    root = root.resolve()
    if explicit_source is not None:
        resolved = explicit_source.resolve()
        if is_valid_release_dir(resolved):
            return resolved
        raise ValueError(f"Supplied --from-release is not a valid ASE template directory: {resolved}")

    # Check direct subdirectories first, then nested subdirectories (excluding .ase/project-memory and implementazione/dcp-template)
    candidates: list[Path] = []
    for install_py in sorted(root.rglob("install.py")):
        cand = install_py.parent.resolve()
        if cand == root:
            continue
        rel = cand.relative_to(root).as_posix()
        if rel == "implementazione/dcp-template":
            continue
        if is_valid_release_dir(cand):
            candidates.append(cand)
    return candidates[0] if candidates else None


def _split_markdown_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Split markdown into (preamble_before_first_h2, [(h2_heading_line, section_body), ...])."""
    lines = text.splitlines(keepends=True)
    preamble: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    current_heading: str | None = None
    current_body: list[str] = []

    for ln in lines:
        if ln.startswith("## "):
            if current_heading is not None:
                sections.append((current_heading, current_body))
            current_heading = ln.strip()
            current_body = [ln]
        else:
            if current_heading is None:
                preamble.append(ln)
            else:
                current_body.append(ln)
    if current_heading is not None:
        sections.append((current_heading, current_body))

    return "".join(preamble), [(h, "".join(b)) for h, b in sections]


def _extract_config_values(section_text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in section_text.splitlines():
        m = SETTING_ROW_RE.match(line)
        if m:
            key = m.group("name").strip().lower()
            val = (m.group("value") or "").strip()
            if val and not val.startswith("_to be defined"):
                values[key] = val
    return values


def _patch_config_section_rows(new_section_text: str, user_values: dict[str, str]) -> tuple[str, int]:
    patched_lines: list[str] = []
    preserved_count = 0
    for line in new_section_text.splitlines(keepends=True):
        ending = "\n" if line.endswith("\n") else ""
        stripped = line.rstrip("\r\n")
        m = SETTING_ROW_RE.match(stripped)
        if m:
            key = m.group("name").strip().lower()
            if key in user_values:
                user_val = user_values[key]
                patched_lines.append(
                    f"{m.group('prefix')}`{user_val}`{m.group('suffix')}{ending}"
                )
                preserved_count += 1
                continue
        patched_lines.append(line)
    return "".join(patched_lines), preserved_count


def merge_agents_md_row_by_row(current_text: str, new_template_text: str) -> tuple[str, dict[str, int]]:
    """Surgically merge current AGENTS.md with new release AGENTS.md row-by-row and section-by-section."""
    _, cur_sections = _split_markdown_sections(current_text)
    new_preamble, new_sections = _split_markdown_sections(new_template_text)

    cur_by_num: dict[str, tuple[str, str]] = {}
    cur_config_body = ""
    custom_sections: list[str] = []

    for heading, body in cur_sections:
        if heading.lower().startswith("## project configuration"):
            cur_config_body = body
            continue
        m_num = re.match(r"^##\s+(\d+)\.", heading)
        if m_num:
            cur_by_num[m_num.group(1)] = (heading, body)
        else:
            custom_sections.append(body)

    user_config_values = _extract_config_values(cur_config_body)
    preserved_config_rows = 0
    unchanged_sections = 0
    patched_sections = 0
    added_sections = 0

    merged_parts: list[str] = [new_preamble]
    for new_heading, new_body in new_sections:
        if new_heading.lower().startswith("## project configuration"):
            patched_cfg, preserved_config_rows = _patch_config_section_rows(
                new_body, user_config_values
            )
            merged_parts.append(patched_cfg)
            continue

        m_num = re.match(r"^##\s+(\d+)\.", new_heading)
        if m_num:
            sec_num = m_num.group(1)
            if sec_num in cur_by_num:
                _, old_body = cur_by_num[sec_num]
                if old_body == new_body:
                    merged_parts.append(old_body)
                    unchanged_sections += 1
                else:
                    merged_parts.append(new_body)
                    patched_sections += 1
            else:
                merged_parts.append(new_body)
                added_sections += 1
        else:
            merged_parts.append(new_body)

    for custom_body in custom_sections:
        if not merged_parts[-1].endswith("\n\n"):
            merged_parts.append("\n")
        merged_parts.append(custom_body)

    merged_text = "".join(merged_parts)
    stats = {
        "preserved_config_rows": preserved_config_rows,
        "unchanged_sections": unchanged_sections,
        "patched_sections": patched_sections,
        "added_sections": added_sections,
        "preserved_custom_sections": len(custom_sections),
    }
    return merged_text, stats


def patch_next_task_md_in_place(next_task_path: Path) -> bool:
    """Keep active task rows untouched in place; append Return Stack and Context/Chain blocks only if missing."""
    if not next_task_path.is_file():
        return False
    text = next_task_path.read_text(encoding="utf-8")
    changed = False
    if "Inner Sequence Queue & Return Stack" not in text:
        text = text.rstrip("\n") + (
            "\n\n## Inner Sequence Queue & Return Stack\n\n"
            "- **Queued next in inner sequence:** `none`\n"
            "- **Return Stack (PAUSED tasks to resume):** `none`\n"
        )
        changed = True
    if "Context Alerts & Pending Command Chain" not in text:
        text = text.rstrip("\n") + (
            "\n\n## Context Alerts & Pending Command Chain\n\n"
            "- **Context Alerts:** `none`\n"
            "- **Pending Command Chain:** `none`\n"
        )
        changed = True
    if changed:
        next_task_path.write_text(text, encoding="utf-8")
    return changed


def synthesize_project_charter_if_needed(
    root: Path, memory_dir: Path, template_charter_src: Path, config_values: dict[str, str]
) -> bool:
    """Create project-charter.md if absent, auto-filling known rows and marking uncollected rows SKIPPED."""
    charter_dst = memory_dir / "dcp" / "00-project-management" / "project-charter.md"
    if charter_dst.is_file():
        return False

    ctx = config_values.get("project context", "personal") or "personal"
    stack = config_values.get("stack", "SKIPPED (auto-migrated from prior release)")
    fast_cmd = config_values.get("fast ci command", "none")
    gate_cmd = config_values.get("gate ci command", "none")
    branch = config_values.get("working branch", "main")

    pm_readme = memory_dir / "dcp" / "00-project-management" / "README.md"
    purpose_hint = "SKIPPED (auto-migrated from prior release)"
    if pm_readme.is_file():
        for ln in pm_readme.read_text(encoding="utf-8").splitlines():
            stripped = ln.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("-"):
                purpose_hint = stripped
                break

    charter_dst.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f"---\ncontext_profile: {ctx}\nstatus: APPROVED\ndate: auto-migrated\n---\n"
        "# Project Charter & `6W+1H` Context Dossier\n\n"
        "> Auto-synthesized during `/ase-switch` from existing Project Memory. Uncollected rows are marked `SKIPPED (auto-migrated from prior release)`.\n\n"
        "## 1. CHI — Stakeholders, Governance & Authorship\n\n"
        f"- **Project Context Profile:** `{ctx}`\n"
        "- **Author & Role (for `\"I\"` deliverables):** `SKIPPED (auto-migrated from prior release)`\n"
        "- **Client / Target Users:** `SKIPPED (auto-migrated from prior release)`\n\n"
        "## 2. PERCHÉ — Business Context, Objectives & Drivers\n\n"
        f"- **Problem Statement & Purpose:** {purpose_hint}\n"
        "- **Ranked Optimization Drivers:** `Security (HAG-03) > Correctness (HAG-01) > Usability & Simplicity (HAG-05) > Cost & Speed (HAG-04)`\n\n"
        "## 3. COSA — Scope, Deliverables & Untouchable Boundaries\n\n"
        "- **In-Scope Deliverables:** `deliverables/` and active backlog tasks\n"
        "- **Strict Out-of-Scope (Untouchable Perimeter):** `SKIPPED (auto-migrated from prior release)`\n\n"
        "## 4. DOVE — System Landscape, Environments & Trackers\n\n"
        f"- **Git Working Branch:** `{branch}`\n\n"
        "## 5. QUANDO — Timeline, Milestones & Reporting Cadence\n\n"
        "- **Reporting Cadence:** On-demand via `/ase-status`\n\n"
        "## 6. QUANTO — Volumetry, SLAs & FinOps Guardrails (`HAG-04`)\n\n"
        "- **Cloud / Query / Token Cost Ceiling (`HAG-04`):** `SKIPPED (auto-migrated from prior release)`\n\n"
        "## 7. COME — Stack, Security/GDPR & Quality Gates (`HAG-03`, `HAG-05`)\n\n"
        f"- **Tech Stack & Dependency Policy (`HAG-05`):** `{stack}`\n"
        f"- **Verification & Acceptance Criteria:** Fast CI: `{fast_cmd}` | Gate CI: `{gate_cmd}`\n"
    )
    charter_dst.write_text(content, encoding="utf-8")
    return True


def scan_open_tasks_for_driver_advisories(memory_dir: Path) -> list[str]:
    tasks_dir = memory_dir / "dcp" / "04-implementation" / "tasks"
    advisories: list[str] = []
    if not tasks_dir.is_dir():
        return advisories
    for p in sorted(tasks_dir.glob("*.md")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        m_id = re.search(r"^id:\s*(T-[0-9.]+)", text, re.MULTILINE)
        m_st = re.search(r"^status:\s*([A-Z_]+)", text, re.MULTILINE)
        if not m_id or not m_st:
            continue
        tid, status = m_id.group(1), m_st.group(1)
        if status not in ("TODO", "IN_PROGRESS", "PAUSED"):
            continue
        lower = text.lower()
        flags: list[str] = []
        if any(w in lower for w in ("auth", "permission", "migration", "schema", "secret", "gdpr")):
            flags.append("HAG-03 (Security/Data)")
        if any(w in lower for w in ("query", "bigquery", "latency", "performance", "cost", "quota")):
            flags.append("HAG-04 (Cost/Latency)")
        if any(w in lower for w in ("dependency", "package", "library", "sdk", "install")):
            flags.append("HAG-05 (External Dependency)")
        if flags:
            advisories.append(f"`{tid}` (`{status}`): monitor {', '.join(flags)}")
    return advisories


def relocate_legacy_paths(root: Path, encapsulated: bool) -> list[str]:
    """Relocate only paths whose canonical position changed between releases; delete empty legacy dirs."""
    relocated: list[str] = []

    # 1. If migrating from a legacy flat install to encapsulated .ase/
    if encapsulated and (root / "project-memory").is_dir() and not (root / ".ase" / "project-memory").is_dir():
        target_pm = root / ".ase" / "project-memory"
        target_pm.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(root / "project-memory"), str(target_pm))
        relocated.append("project-memory/ -> .ase/project-memory/")
        if (root / "templates").is_dir() and not (root / ".ase" / "templates").is_dir():
            shutil.move(str(root / "templates"), str(root / ".ase" / "templates"))
            relocated.append("templates/ -> .ase/templates/")
        if (root / "scripts" / "next-id.py").is_file():
            shutil.rmtree(root / "scripts", ignore_errors=True)
            relocated.append("removed legacy root scripts/ (moved to .ase/scripts/)")

    # 2. Relocate .ase/artifacts/ or root artifacts/ -> root deliverables/ and .ase/specs/
    deliv_root = root / "deliverables"
    specs_root = (root / ".ase" / "specs") if encapsulated else (root / "specs")
    for legacy_art in (root / ".ase" / "artifacts", root / "artifacts"):
        if not legacy_art.is_dir():
            continue
        for folder in LIFECYCLE_FOLDERS:
            src_sub = legacy_art / folder
            if src_sub.is_dir():
                dst_sub = deliv_root / folder
                dst_sub.mkdir(parents=True, exist_ok=True)
                for item in sorted(src_sub.rglob("*")):
                    if item.is_file() and item.name != ".gitkeep":
                        rel = item.relative_to(src_sub)
                        target = dst_sub / rel
                        target.parent.mkdir(parents=True, exist_ok=True)
                        if not target.exists():
                            shutil.move(str(item), str(target))
                            relocated.append(
                                f"{legacy_art.relative_to(root)}/{folder}/{rel.as_posix()} -> deliverables/{folder}/{rel.as_posix()}"
                            )
        legacy_specs = legacy_art / "specs"
        if legacy_specs.is_dir():
            specs_root.mkdir(parents=True, exist_ok=True)
            for item in sorted(legacy_specs.rglob("*")):
                if item.is_file() and item.name != ".gitkeep":
                    rel = item.relative_to(legacy_specs)
                    target = specs_root / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists():
                        shutil.move(str(item), str(target))
                        relocated.append(
                            f"{legacy_art.relative_to(root)}/specs/{rel.as_posix()} -> {specs_root.relative_to(root)}/{rel.as_posix()}"
                        )
        shutil.rmtree(legacy_art, ignore_errors=True)
        relocated.append(f"purged obsolete directory {legacy_art.relative_to(root)}/")

    return relocated


def switch_release(
    root: Path,
    explicit_source: Path | None = None,
    keep_source: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    cloned_source = discover_cloned_release(root, explicit_source)
    if cloned_source is None:
        raise RuntimeError(
            "No cloned ASE release directory found in the workspace. "
            "Clone the new release into the workspace root (e.g. `git clone .../agentic-dcp-template`) "
            "or pass `--from-release /path/to/template`."
        )

    # Load the new release's install.py module so INCLUDE and helper logic come from the NEW release
    spec = importlib.util.spec_from_file_location("new_installer", cloned_source / "install.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load install.py from {cloned_source}")
    new_inst = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(new_inst)

    manifest_path = root / ".agents" / ".ase-install.json"
    old_manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.is_file()
        else {"files": {}, "versioned": False, "encapsulated": True}
    )
    old_version = old_manifest.get("version", "v0.2.0-or-earlier")
    new_version = parse_release_version(cloned_source)
    versioned = bool(old_manifest.get("versioned", False))
    encapsulated = bool(old_manifest.get("encapsulated", True))
    if not manifest_path.is_file() and (root / "project-memory").is_dir() and not (root / ".ase" / "project-memory").is_dir():
        encapsulated = True  # Migrate legacy flat install into clean 3-Zone encapsulated layout

    # Create transactional rollback staging directory in /tmp
    staging_dir = Path(tempfile.mkdtemp(prefix="ase-switch-rollback-"))
    backup_archive = staging_dir / "workspace_state"
    backup_archive.mkdir(parents=True, exist_ok=True)
    for item_name in (".ase", ".agents", ".github", ".vscode", "AGENTS.md", "deliverables", "artifacts", "project-memory"):
        cand = root / item_name
        if cand.exists():
            dst = backup_archive / item_name
            if cand.is_dir():
                shutil.copytree(cand, dst)
            else:
                shutil.copy2(cand, dst)

    try:
        relocated_paths = relocate_legacy_paths(root, encapsulated)
        memory_dir = (root / ".ase" / "project-memory") if encapsulated else (root / "project-memory")

        # Determine which AGENTS.md holds ASE rules
        rules_rel = (
            ".agents/AGENTS.md"
            if (root / ".agents" / "AGENTS.md").is_file()
            else "AGENTS.md"
        )
        rules_path = root / rules_rel
        new_agents_text = (cloned_source / "AGENTS.md").read_text(encoding="utf-8")
        agents_stats: dict[str, int] = {}
        if rules_path.is_file():
            cur_agents_text = rules_path.read_text(encoding="utf-8")
            merged_agents, agents_stats = merge_agents_md_row_by_row(
                cur_agents_text, new_agents_text
            )
            if merged_agents != cur_agents_text:
                rules_path.write_text(merged_agents, encoding="utf-8")
        else:
            rules_path.parent.mkdir(parents=True, exist_ok=True)
            rules_path.write_text(new_agents_text, encoding="utf-8")

        config_values = _extract_config_values(rules_path.read_text(encoding="utf-8"))

        # CDC sync of all files in the new release
        unchanged_files: list[str] = []
        patched_files: list[str] = []
        created_files: list[str] = []
        kept_project_data_files: list[str] = []
        new_installed: dict[str, str] = {}

        for rel in new_inst.source_files():
            dest_rel = new_inst.map_dest_rel(rel, encapsulated)
            if dest_rel == "AGENTS.md":
                dest_rel = rules_rel
                new_installed[dest_rel] = _sha256(root / dest_rel)
                if agents_stats.get("patched_sections", 0) > 0 or agents_stats.get("added_sections", 0) > 0:
                    patched_files.append(dest_rel)
                else:
                    unchanged_files.append(dest_rel)
                continue

            dest = root / dest_rel
            src_file = cloned_source / rel
            is_project_memory_data = (
                "project-memory/" in dest_rel
                or dest_rel.startswith(("deliverables/", "inputs/"))
            )

            if dest.exists():
                if is_project_memory_data and dest.name != ".gitkeep":
                    # Never overwrite user project data; keep in place with 0 writes
                    kept_project_data_files.append(dest_rel)
                    new_installed[dest_rel] = old_manifest.get("files", {}).get(
                        dest_rel, _sha256(dest)
                    )
                    continue

                cur_sha = _sha256(dest)
                new_sha = _sha256(src_file)
                if cur_sha == new_sha:
                    # Mode A: UNCHANGED -> 0 disk writes (inode & mtime preserved)
                    unchanged_files.append(dest_rel)
                    new_installed[dest_rel] = cur_sha
                    continue

                # Mode C: LINE-DIFF UPDATE on changed harness file
                dest.write_bytes(src_file.read_bytes())
                dest.chmod(src_file.stat().st_mode)
                new_installed[dest_rel] = new_sha
                patched_files.append(dest_rel)
            else:
                if dest_rel.endswith("dcp/00-project-management/project-charter.md"):
                    synthesize_project_charter_if_needed(
                        root, memory_dir, src_file, config_values
                    )
                    new_installed[dest_rel] = _sha256(dest)
                    created_files.append(dest_rel)
                    continue

                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(src_file.read_bytes())
                dest.chmod(src_file.stat().st_mode)
                new_installed[dest_rel] = _sha256(dest)
                created_files.append(dest_rel)

        # Patch state/NEXT_TASK.md in-place (preserving active task)
        next_task_path = memory_dir / "state" / "NEXT_TASK.md"
        next_task_patched = patch_next_task_md_in_place(next_task_path)
        if next_task_patched:
            patched_files.append(str(next_task_path.relative_to(root)))

        # Purge retired harness files from old manifest that no longer exist in new release
        purged_files: list[str] = []
        for old_rel in old_manifest.get("files", {}):
            if old_rel in (".agents/.ase-install.json", ".vscode/settings.json"):
                continue
            if old_rel not in new_installed:
                if "project-memory/" in old_rel or old_rel.startswith(("deliverables/", "inputs/")):
                    continue
                old_p = root / old_rel
                if old_p.is_file():
                    old_p.unlink()
                    purged_files.append(old_rel)
                    parent_d = old_p.parent
                    while parent_d != root and parent_d.is_dir() and not any(parent_d.iterdir()):
                        parent_d.rmdir()
                        parent_d = parent_d.parent

        # Update .vscode/settings.json (removing stale keys & hiding internal ASE paths)
        new_inst.configure_vscode_excludes(root, new_installed, encapsulated, hide=True)
        vscode_path = root / ".vscode" / "settings.json"
        if vscode_path.is_file():
            vs_data = json.loads(vscode_path.read_text(encoding="utf-8"))
            if "files.exclude" in vs_data:
                vs_data["files.exclude"].pop("artifacts", None)
                vs_data["files.exclude"].pop(".ase/artifacts", None)
                vscode_path.write_text(json.dumps(vs_data, indent=2) + "\n", encoding="utf-8")
            new_installed[".vscode/settings.json"] = _sha256(vscode_path)

        # Write updated .agents/.ase-install.json manifest
        new_installed[".agents/.ase-install.json"] = ""
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "version": new_version,
                    "versioned": versioned,
                    "encapsulated": encapsulated,
                    "files": new_installed,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        # Update .git/info/exclude if unversioned Git repo
        _, has_git = new_inst.git_root(root, allow_no_git=True)
        if not versioned and has_git:
            exclude_entries = ["/" + p for p in new_installed]
            exclude_entries.extend(["/inputs/", "/deliverables/", "/handover/"])
            if encapsulated:
                exclude_entries.append("/.ase/")
            new_inst.write_exclude(root, exclude_entries)

        # Cascade CDC switch to any member child ASE projects inside an Umbrella Father root
        upgraded_children: list[str] = []
        for child_dir in sorted(root.iterdir()):
            if not child_dir.is_dir() or child_dir.name.startswith(".") or child_dir.resolve() == cloned_source:
                continue
            if child_dir.name in ("implementazione", "paradigma", "deliverables", "handover", "inputs", "plugins", "graphify-out"):
                continue
            has_child_ase = (
                (child_dir / ".ase" / "project-memory" / "state" / "PROJECT_STATE.md").is_file()
                or (child_dir / "project-memory" / "state" / "PROJECT_STATE.md").is_file()
                or (child_dir / ".agents" / ".ase-install.json").is_file()
            )
            if has_child_ase:
                switch_release(child_dir, explicit_source=cloned_source, keep_source=True)
                upgraded_children.append(child_dir.name)

        # Self-delete the cloned release directory if it sits inside root
        deleted_clone_dir: str | None = None
        if not keep_source and cloned_source != root and root in cloned_source.parents:
            rel_clone = cloned_source.relative_to(root).as_posix()
            shutil.rmtree(cloned_source)
            deleted_clone_dir = rel_clone
            # If parent folder (e.g. ase-tool/) is now empty, remove it too
            parent_c = cloned_source.parent
            while parent_c != root and parent_c.is_dir() and not any(parent_c.iterdir()):
                parent_c.rmdir()
                parent_c = parent_c.parent

        # Verify layout after switch
        if new_inst.verify_layout(root) != 0:
            raise RuntimeError("Post-switch layout verification failed")

        driver_advisories = scan_open_tasks_for_driver_advisories(memory_dir)

    except Exception:
        # Roll back from /tmp staging buffer on any error
        for item in backup_archive.iterdir():
            target = root / item.name
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target, ignore_errors=True)
                else:
                    target.unlink()
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise

    # Success: delete the /tmp rollback staging buffer so zero trace remains
    shutil.rmtree(staging_dir, ignore_errors=True)

    return {
        "old_version": old_version,
        "new_version": new_version,
        "encapsulated": encapsulated,
        "agents_md_stats": agents_stats,
        "unchanged_count": len(unchanged_files),
        "patched_count": len(patched_files),
        "created_count": len(created_files),
        "kept_project_data_count": len(kept_project_data_files),
        "relocated_paths": relocated_paths,
        "purged_files": purged_files,
        "upgraded_children": upgraded_children,
        "deleted_clone_dir": deleted_clone_dir,
        "driver_advisories": driver_advisories,
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
        "--from-release",
        type=Path,
        default=None,
        help="Optional path to the new ASE release directory (auto-discovered in workspace if omitted).",
    )
    parser.add_argument(
        "--keep-source",
        action="store_true",
        help="Do not delete the cloned release directory after switching.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON.",
    )
    args = parser.parse_args()

    try:
        res = switch_release(args.root, args.from_release, args.keep_source)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        lines = [
            f"PASS: Switched ASE release `{res['old_version']} -> {res['new_version']}` in-place via CDC diff-patching.",
            f"  - Unchanged files kept in place (0 writes): {res['unchanged_count']}",
            f"  - Project data files preserved in place: {res['kept_project_data_count']}",
            f"  - Patched files (row/line delta): {res['patched_count']}",
            f"  - Created new release files: {res['created_count']}",
            f"  - AGENTS.md config rows preserved: {res['agents_md_stats'].get('preserved_config_rows', 0)}",
        ]
        if res["relocated_paths"]:
            lines.append("  - Relocated paths: " + ", ".join(res["relocated_paths"]))
        if res["deleted_clone_dir"]:
            lines.append(f"  - Deleted cloned release folder: `{res['deleted_clone_dir']}/`")
        if res["driver_advisories"]:
            lines.append("  - Driver / HAG advisories on open tasks: " + "; ".join(res["driver_advisories"]))
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
