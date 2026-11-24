#!/usr/bin/env python3
"""Read-only stakeholder handover folder and .zip archive bundler (/ase-export).

Responsibilities (strictly non-overlapping with /ase-pack):
  1. Enforces Step 0 prerequisite via check-prereq.py --command ase-export:
     fails immediately if /ase-pack has not been run or ifPACK_STATE.json is stale,
     reminding the Human Owner to run /ase-pack first.
  2. Generates zero new Markdown summaries or PDFs; reuses deliverables/ curated by /ase-pack.
  3. Bundles clean project source files (project-files/) + populated deliverables/ into
     handover/<project>-handover-YYYY-MM-DD/ and handover/<project>-handover-YYYY-MM-DD.zip,
     stripping all internal ASE (.ase/, .agents/, .github/agents/, .vscode/, etc.) and build caches.
  4. Runs verify-external-clean.py --check-first-person on the exported handover directory
     before creating the .zip archive.
"""

from __future__ import annotations

import argparse
from datetime import date
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
import zipfile

EXCLUDED_ROOT_NAMES = {
    ".ase",
    ".agents",
    ".vscode",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".git",
    ".mcp.json",
    "graphify-out",
    "deliverables",
    "artifacts",
    "handover",
    "project-memory",
    "templates",
}


def _load_prereq_module():
    path = Path(__file__).resolve().parent / "check-prereq.py"
    spec = importlib.util.spec_from_file_location("check_prereq", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load check-prereq.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _is_ase_installed_path(rel_posix: str, installed_files: dict[str, Any], root: Path) -> bool:
    if rel_posix in installed_files:
        return True
    if rel_posix in (".github/instructions/ase.instructions.md", ".agents/rules/ase.md"):
        return True
    if rel_posix.startswith((".github/agents/", ".github/instructions/", ".agents/", ".ase/")):
        return True
    if rel_posix == "AGENTS.md":
        text = (root / "AGENTS.md").read_text(encoding="utf-8", errors="ignore")
        if "Agentic Software Engineering" in text:
            return True
    if rel_posix.startswith(("scripts/", "templates/", "project-memory/", "artifacts/")):
        if (root / "scripts" / "next-id.py").is_file() and rel_posix.startswith("scripts/"):
            return True
    return False


def export_handover(root: Path, output_dir: Path | None = None, target_date: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    prereq_mod = _load_prereq_module()
    prereq_res = prereq_mod.evaluate_prerequisites(root, "ase-export")
    if not prereq_res["ok"]:
        raise RuntimeError(prereq_mod.format_report(prereq_res))

    manifest_path = root / ".agents" / ".ase-install.json"
    installed_files: dict[str, Any] = {}
    if manifest_path.is_file():
        try:
            installed_files = json.loads(manifest_path.read_text(encoding="utf-8")).get("files", {})
        except (OSError, json.JSONDecodeError):
            installed_files = {}

    today_str = target_date or date.today().isoformat()
    base_out = output_dir.resolve() if output_dir else (root / "handover")
    bundle_name = f"{root.name}-handover-{today_str}"
    bundle_dir = base_out / bundle_name
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    deliv_src = root / "deliverables"
    index_src = deliv_src / "INDEX.md"
    if index_src.is_file():
        shutil.copy2(index_src, bundle_dir / "INDEX.md")

    deliv_dst = bundle_dir / "deliverables"
    deliv_dst.mkdir(parents=True, exist_ok=True)
    copied_deliverables: list[str] = []
    for item in sorted(deliv_src.rglob("*")):
        if not item.is_file() or item.name == ".gitkeep":
            continue
        rel = item.relative_to(deliv_src)
        target = deliv_dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        copied_deliverables.append(rel.as_posix())

    proj_dst = bundle_dir / "project-files"
    proj_dst.mkdir(parents=True, exist_ok=True)
    copied_project_files: list[str] = []
    for item in sorted(root.rglob("*")):
        if not item.is_file():
            continue
        rel_parts = item.relative_to(root).parts
        if not rel_parts or rel_parts[0] in EXCLUDED_ROOT_NAMES:
            continue
        if any(p in ("__pycache__", "node_modules", ".venv", "venv", ".git") for p in rel_parts):
            continue
        rel_posix = item.relative_to(root).as_posix()
        if _is_ase_installed_path(rel_posix, installed_files, root):
            continue
        target = proj_dst / rel_posix
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        copied_project_files.append(rel_posix)

    clean_script = Path(__file__).resolve().parent / "verify-external-clean.py"
    clean_res = subprocess.run(
        [sys.executable, str(clean_script), "--check-first-person", str(deliv_dst)],
        capture_output=True,
        text=True,
        check=False,
    )
    if clean_res.returncode != 0:
        raise RuntimeError(
            f"External-clean verification failed on exported deliverables:\n{clean_res.stderr or clean_res.stdout}"
        )

    clean_proj_res = subprocess.run(
        [sys.executable, str(clean_script), str(proj_dst)],
        capture_output=True,
        text=True,
        check=False,
    )
    if clean_proj_res.returncode != 0:
        raise RuntimeError(
            f"External-clean verification failed on exported project-files:\n{clean_proj_res.stderr or clean_proj_res.stdout}"
        )

    zip_path = base_out / f"{bundle_name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(bundle_dir.rglob("*")):
            if file_path.is_file():
                arcname = file_path.relative_to(base_out).as_posix()
                zf.write(file_path, arcname)

    return {
        "bundle_dir": str(bundle_dir),
        "zip_path": str(zip_path),
        "deliverables_count": len(copied_deliverables),
        "project_files_count": len(copied_project_files),
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
        "--output-dir",
        type=Path,
        default=None,
        help="Output parent directory for the handover bundle (default: <root>/handover).",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Optional YYYY-MM-DD date suffix.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON.",
    )
    args = parser.parse_args()

    try:
        res = export_handover(args.root, args.output_dir, args.date)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(
            f"PASS: Stakeholder handover bundle exported and verified clean:\n"
            f"  - Folder: {res['bundle_dir']}\n"
            f"  - Archive: {res['zip_path']}\n"
            f"  - Included: {res['project_files_count']} project file(s) and {res['deliverables_count']} deliverable(s)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
