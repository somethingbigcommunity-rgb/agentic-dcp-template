#!/usr/bin/env python3
"""Scaffold, validate, and sync a project-derived, ASE-external reusable plugin.

Features:
- Scaffolds a portable Antigravity / Copilot plugin under `plugins/<slug>/` (`--scaffold`).
- Validates `plugin.json` and enforces zero ASE framework references via `verify-external-clean.py`.
- Syncs plugin skills, rules, and agents into:
  1) Local workspace (`.agents/` for Antigravity and `.github/` for VS Code Copilot), or
  2) Global Antigravity user plugin directory (`~/.gemini/config/plugins/<slug>/`).

Usage:
  python3 scripts/sync-plugin.py --plugin plugins/my-domain-plugin --scaffold --description "Domain guardrails"
  python3 scripts/sync-plugin.py --plugin plugins/my-domain-plugin --check
  python3 scripts/sync-plugin.py --plugin plugins/my-domain-plugin --target .
  python3 scripts/sync-plugin.py --plugin plugins/my-domain-plugin --global-antigravity
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path


def load_cleaner():
    cleaner_path = Path(__file__).resolve().parent / "verify-external-clean.py"
    spec = importlib.util.spec_from_file_location("verify_external_clean", cleaner_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {cleaner_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scaffold_plugin(plugin_dir: Path, description: str) -> int:
    slug = plugin_dir.name
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        print(f"error: plugin directory name '{slug}' must be kebab-case", file=sys.stderr)
        return 1
    plugin_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("skills", "rules", "agents", "scripts"):
        (plugin_dir / sub).mkdir(parents=True, exist_ok=True)

    skill_rel = f"skills/{slug}-workflow/SKILL.md"
    rule_rel = f"rules/{slug}-guardrails.md"
    manifest = {
        "name": slug,
        "version": "0.1.0",
        "description": description or f"Reusable domain plugin for {slug}.",
        "skills": [skill_rel],
        "rules": [rule_rel],
        "agents": [],
        "scripts": [],
    }
    manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.exists():
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    skill_path = plugin_dir / skill_rel
    if not skill_path.exists():
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(
            f"---\n"
            f"name: {slug}-workflow\n"
            f"description: \"Domain workflow and verification checks for {slug}.\"\n"
            f"---\n\n"
            f"# {slug} Workflow\n\n"
            f"Use this skill when working on `{slug}` components, schemas, or validations.\n",
            encoding="utf-8",
        )

    rule_path = plugin_dir / rule_rel
    if not rule_path.exists():
        rule_path.parent.mkdir(parents=True, exist_ok=True)
        rule_path.write_text(
            f"---\n"
            f"trigger: always_on\n"
            f"description: \"Core domain guardrails for {slug}.\"\n"
            f"---\n\n"
            f"# {slug} Guardrails\n\n"
            f"- Follow the domain conventions and run deterministic validation scripts before completion.\n",
            encoding="utf-8",
        )

    readme_path = plugin_dir / "README.md"
    if not readme_path.exists():
        readme_path.write_text(
            f"# {slug}\n\n"
            f"{manifest['description']}\n\n"
            f"## Portability\n\n"
            f"This plugin is self-contained and has zero dependency on any meta-framework.\n"
            f"It can be installed in any Antigravity or VS Code Copilot repository.\n",
            encoding="utf-8",
        )

    print(f"Scaffolded plugin '{slug}' at {plugin_dir}")
    return 0


def validate_plugin(plugin_dir: Path) -> tuple[dict, list[str]]:
    errors: list[str] = []
    manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.is_file():
        return {}, [f"{manifest_path}: missing plugin.json"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [f"{manifest_path}: invalid JSON: {exc}"]

    for req_key in ("name", "version", "description"):
        if not isinstance(manifest.get(req_key), str) or not manifest[req_key].strip():
            errors.append(f"{manifest_path}: missing or empty '{req_key}'")

    for section in ("skills", "rules", "agents", "scripts"):
        items = manifest.get(section, [])
        if not isinstance(items, list):
            errors.append(f"{manifest_path}: '{section}' must be a list")
            continue
        for rel in items:
            target = plugin_dir / rel
            if not target.is_file():
                errors.append(f"{manifest_path}: referenced {section} file '{rel}' does not exist")

    cleaner = load_cleaner()
    clean_findings = cleaner.scan_paths([plugin_dir])
    errors.extend(clean_findings)
    return manifest, errors


def _convert_rule_to_copilot(rule_text: str) -> str:
    """Convert Antigravity rule frontmatter (trigger/globs) into Copilot instructions frontmatter."""
    if not rule_text.startswith("---\n"):
        return "---\napplyTo: \"**\"\n---\n\n" + rule_text
    parts = rule_text.split("---\n", 2)
    if len(parts) < 3:
        return rule_text
    fm_lines = parts[1].splitlines()
    body = parts[2]
    desc = "Domain rule"
    globs = "**"
    for line in fm_lines:
        if line.startswith("description:"):
            desc = line.partition(":")[2].strip().strip('"')
        elif line.startswith("globs:"):
            globs = line.partition(":")[2].strip().strip('"')
    return f'---\ndescription: "{desc}"\napplyTo: "{globs}"\n---\n{body}'


def sync_to_workspace(plugin_dir: Path, manifest: dict, target_root: Path) -> list[str]:
    copied: list[str] = []
    # 1. Skills -> .agents/skills/<skill-folder>/SKILL.md
    for rel in manifest.get("skills", []):
        src = plugin_dir / rel
        skill_folder_name = src.parent.name
        dst = target_root / ".agents" / "skills" / skill_folder_name / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(str(dst.relative_to(target_root)))

    # 2. Rules -> .agents/rules/<name>.md and .github/instructions/<name>.instructions.md
    for rel in manifest.get("rules", []):
        src = plugin_dir / rel
        dst_agy = target_root / ".agents" / "rules" / src.name
        dst_agy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst_agy)
        copied.append(str(dst_agy.relative_to(target_root)))

        stem = src.stem
        dst_cop = target_root / ".github" / "instructions" / f"{stem}.instructions.md"
        dst_cop.parent.mkdir(parents=True, exist_ok=True)
        dst_cop.write_text(_convert_rule_to_copilot(src.read_text(encoding="utf-8")), encoding="utf-8")
        copied.append(str(dst_cop.relative_to(target_root)))

    # 3. Agents -> .agents/agents/<name>.md
    for rel in manifest.get("agents", []):
        src = plugin_dir / rel
        dst_agy = target_root / ".agents" / "agents" / src.name
        dst_agy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst_agy)
        copied.append(str(dst_agy.relative_to(target_root)))

    return copied


def sync_to_global(plugin_dir: Path, manifest: dict, global_base: Path) -> Path:
    dest_dir = global_base / manifest["name"]
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.copytree(plugin_dir, dest_dir)
    return dest_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plugin", required=True, type=Path, help="Path to plugin folder (e.g. plugins/my-plugin)")
    parser.add_argument("--scaffold", action="store_true", help="Create initial plugin skeleton if missing")
    parser.add_argument("--description", default="", help="Plugin description when using --scaffold")
    parser.add_argument("--check", action="store_true", help="Validate manifest and zero-ASE-footprint only")
    parser.add_argument("--target", type=Path, default=Path("."), help="Target repository root for workspace sync")
    parser.add_argument("--global-antigravity", action="store_true", help="Install into ~/.gemini/config/plugins/<name>")
    parser.add_argument("--global-dir", type=Path, default=Path.home() / ".gemini" / "config" / "plugins",
                        help="Override global plugins base directory")
    args = parser.parse_args(argv)

    plugin_dir = args.plugin.resolve()
    if args.scaffold:
        rc = scaffold_plugin(plugin_dir, args.description)
        if rc != 0:
            return rc

    manifest, errors = validate_plugin(plugin_dir)
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        print(f"FAIL: plugin '{plugin_dir.name}' failed validation ({len(errors)} error(s)).", file=sys.stderr)
        return 1

    if args.check or args.scaffold:
        print(f"PASS: plugin '{manifest['name']}' v{manifest['version']} is valid and free of ASE references.")
        return 0

    if args.global_antigravity:
        dest = sync_to_global(plugin_dir, manifest, args.global_dir.resolve())
        print(f"Synced plugin '{manifest['name']}' to global Antigravity plugins: {dest}")
        return 0

    target_root = args.target.resolve()
    copied = sync_to_workspace(plugin_dir, manifest, target_root)
    for rel in copied:
        print(f"  + {rel}")
    print(f"Synced {len(copied)} file(s) from plugin '{manifest['name']}' v{manifest['version']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
