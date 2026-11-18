---
name: ase-plugin
description: "Identify, propose, scaffold, validate, and sync project-derived reusable domain plugins that are completely external to ASE (zero ASE references) and portable across similar projects. Use when asked to run /ase-plugin, extract reusable project skills/rules/validators into a plugin, or sync plugins/<slug>/."
---

# `/ase-plugin`

> If the repository's root `AGENTS.md` belongs to the team and is not the ASE rules file, the installer placed the ASE rules in `.agents/AGENTS.md`; every reference to `AGENTS.md` in this skill means that file.

Package domain-specific skills, file-scoped rules, specialist agents, or deterministic validation scripts discovered during a project into a **portable, ASE-external plugin** under `plugins/<plugin-slug>/` (DEC-14).

The resulting plugin **must not depend on ASE** and **must contain zero references to ASE** (`Agentic Software Engineering`, `ASE`, `DCP`, `HAG`, `project-memory/`, `/ase-*`, etc.) so it can be shared with external teams or installed into any Antigravity or VS Code Copilot workspace.

## 1. When to Propose a Plugin Proactively

During `/ase-setup` (P0), `/ase-adopt` (P0-A), `/ase-plan` (P1–P4), or `/ase-review` (P7), proactively propose creating or updating a reusable domain plugin when any of these signals appear:

1. **Multi-Tool Domain Stack:** A specialized stack combination with strict conventions or guardrails (e.g., BigQuery + LookML, React + Corporate Design System, FastAPI + OpenAPI + SQLAlchemy, Terraform + Cloud Run).
2. **Repeated Domain Verification:** A deterministic validation script, schema linter, or reconciliation check is used across 2 or more Features/Waves or could benefit sibling repositories.
3. **Reusable Specialist Workflow:** A domain workflow (e.g., semantic layer auditing, migration safety checks, accessibility auditing) is generalizable beyond the current repository.

Always ask the Human Owner for confirmation before creating `plugins/<plugin-slug>/` and record the architectural decision in `project-memory/adr/` (HAG-02).

## 2. Scaffold and Author the Plugin

1. Open or work within an assigned task (`T-NNNN`) as required by `AGENTS.md`.
2. Run the deterministic helper to scaffold `plugins/<plugin-slug>/`:

   ```sh
   python3 scripts/sync-plugin.py \
     --plugin plugins/<plugin-slug> \
     --scaffold \
     --description "<Concise domain description>"
   ```

3. Author or update the plugin contents under `plugins/<plugin-slug>/`:
   - `plugin.json`: manifest listing `name`, `version`, `description`, `skills`, `rules`, `agents`, and `scripts`.
   - `skills/<skill-name>/SKILL.md`: domain workflow instructions.
   - `rules/<rule-name>.md`: Antigravity rule (`trigger: always_on` or `trigger: glob` with `globs`), automatically converted to `.github/instructions/<rule-name>.instructions.md` for Copilot during workspace sync.
   - `scripts/`: deterministic domain validators (standard library preferred).
   - `README.md`: standalone usage and portability documentation.

## 3. Verify Zero-ASE-Footprint and Sync

1. Validate the manifest and verify that the entire plugin directory contains zero ASE framework references:

   ```sh
   python3 scripts/sync-plugin.py --plugin plugins/<plugin-slug> --check
   python3 scripts/verify-external-clean.py plugins/<plugin-slug>
   ```

2. Sync the plugin into the active workspace (`.agents/` and `.github/`) or globally into Antigravity (`~/.gemini/config/plugins/<plugin-slug>/`) according to the Human Owner's preference:

   ```sh
   # Sync into current repository (.agents/ + .github/)
   python3 scripts/sync-plugin.py --plugin plugins/<plugin-slug> --target .

   # Or install globally for Antigravity across all workspaces
   python3 scripts/sync-plugin.py --plugin plugins/<plugin-slug> --global-antigravity
   ```

3. Record the validation (`PASS`) and synced files in the task execution report.
