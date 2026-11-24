---
name: ase-pack
description: Curate deliverables/ in-place inside the workspace after completing a milestone or project, generate deliverables/INDEX.md in first-person singular ("I"), hide internal ASE folders and empty lifecycle folders via .vscode/settings.json (files.exclude), verify zero-ASE-footprint, and record state/PACK_STATE.json. Use when asked to run /ase-pack or organize completed project work in the workspace.
---

# `/ase-pack`

> If the repository's root `AGENTS.md` belongs to the team and is not the ASE rules file, the installer placed the ASE rules in `.agents/AGENTS.md`; every reference to `AGENTS.md` in this skill means that file. When `.ase/` encapsulation is present, `project-memory/`, `specs/`, `scripts/`, and `templates/` resolve under `.ase/`, while `deliverables/` sits visibly at the repository root. Always use first-person singular (`"I"`, addressing the Human Owner as `"you"`, never `"we"`).

Curate `deliverables/` and clean the IDE Explorer view **in-place inside the workspace** without duplicating project source files or creating `.zip` archives.

## 0. Check command prerequisites

Run from the repository root:

```sh
python3 scripts/check-prereq.py --command ase-pack     # or python3 .ase/scripts/check-prereq.py --command ase-pack
```

If `check-prereq.py` exits with `1` (for example, because a task is still `IN_PROGRESS`, `IN_REVIEW`, `BLOCKED`, or `PAUSED` on the Return Stack, or `M0`/`M0-A` is incomplete), stop immediately and remind the Human Owner which prerequisite command (`/ase-task`, `/ase-adopt`, `/ase-setup`) to run first. If `check-prereq.py` emits a warning that `/ase-review` has not yet been run for the completed Work Package, mention it and ask if the Human Owner wants to run `/ase-review` first or proceed with `/ase-pack`.

## 1. Optional Stakeholder PDF Generation (from `.ase/specs/`)

Before running the pack script, check whether the Human Owner wants to generate or update an executive stakeholder PDF (such as `deliverables/05-release-and-handover/release-report.pdf` or `deliverables/02-planning/project-plan.pdf`) from a spec in `.ase/specs/` (or `specs/`) via `scripts/build-stakeholder-pdf.py` (using the repository's `work` Sopra Steria Group profile or `personal` profile).

## 2. Run the deterministic in-place workspace packer

Run:

```sh
python3 scripts/pack-workspace.py                      # or python3 .ase/scripts/pack-workspace.py
```

This deterministically:
1. Curates root `deliverables/` (`01-discovery/` .. `05-release-and-handover/`), migrating any legacy files from `.ase/artifacts/`.
2. Generates/updates `deliverables/INDEX.md` in the Human Owner's first-person singular voice (`"I"`, zero ASE references) with the executive summary of completed work, run/test commands, deliverable links, and project modules.
3. Updates `.vscode/settings.json` (`files.exclude`) to hide internal ASE harness folders (`.ase`, `.agents`, `.github/agents`, `.github/instructions`, `.vscode`, `.venv`, `.mcp.json`, `graphify-out`, and ASE-owned `AGENTS.md`) plus any empty `deliverables/0X-*` folders so the Explorer sidebar shows only real project files and populated deliverables.
4. Verifies `deliverables/` with `scripts/verify-external-clean.py --check-first-person` and writes `state/PACK_STATE.json`.

## 3. Report and ask whether a `.zip` handover archive is needed

Report the curated `deliverables/INDEX.md` and Explorer cleanup, and end by asking:

> *"Your workspace and `deliverables/` are packed and clean. Do you also need a `.zip` bundle (`<project>-handover-YYYY-MM-DD.zip`) to send to a stakeholder? If yes, confirm and I will run `/ase-export` (`python3 scripts/export-handover.py`)."*
