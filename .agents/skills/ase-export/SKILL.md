---
name: ase-export
description: Bundle all clean project source files (project-files/) and already-packed deliverables (deliverables/) into a standalone handover/<project>-handover-YYYY-MM-DD/ folder and .zip archive for one-click stakeholder sharing. Requires an up-to-date /ase-pack. Use when asked to run /ase-export or create a portable zip/folder handover package for a stakeholder.
---

# `/ase-export`

> If the repository's root `AGENTS.md` belongs to the team and is not the ASE rules file, the installer placed the ASE rules in `.agents/AGENTS.md`; every reference to `AGENTS.md` in this skill means that file. When `.ase/` encapsulation is present, `project-memory/`, `specs/`, `scripts/`, and `templates/` resolve under `.ase/`. Always use first-person singular (`"I"`, addressing the Human Owner as `"you"`, never `"we"`).

Export a standalone, zero-ASE-footprint folder and `.zip` archive (`handover/<project>-handover-YYYY-MM-DD/` and `.zip`) containing all project source files plus `deliverables/` for one-click sharing with an external stakeholder.

## 0. Check command prerequisites (`ase-pack` dependency enforced)

Run from the repository root:

```sh
python3 scripts/check-prereq.py --command ase-export   # or python3 .ase/scripts/check-prereq.py --command ase-export
```

`/ase-export` strictly depends on an up-to-date `/ase-pack` (`deliverables/INDEX.md` and `state/PACK_STATE.json` matching the current workspace digest). If `check-prereq.py` exits with `1`, **stop immediately** and tell the Human Owner:

> *"Dependency check failed: `/ase-export` requires an up-to-date `/ase-pack` first (`deliverables/INDEX.md` is missing or files changed since the last pack). Run `/ase-pack` first, or confirm and I will run `/ase-pack` followed by `/ase-export`."*

## 1. Run the deterministic handover exporter

Once `check-prereq.py --command ase-export` passes, run:

```sh
python3 scripts/export-handover.py                     # or python3 .ase/scripts/export-handover.py
```

This generates zero new Markdown summaries or PDFs; it reuses the curated `deliverables/` directory from `/ase-pack`, copies all clean project files into `project-files/` (stripping `.ase/`, `.agents/`, `.github/agents/`, `.github/instructions/`, `.vscode/`, `.venv/`, `node_modules/`, `.git/`, `graphify-out/`, and ASE-owned `AGENTS.md`), verifies the entire bundle with `scripts/verify-external-clean.py`, and creates `handover/<project>-handover-YYYY-MM-DD.zip`.

## 2. Report the one-click handover paths

Report the clickable paths to `handover/<project>-handover-YYYY-MM-DD/` and `handover/<project>-handover-YYYY-MM-DD.zip` and the `verify-external-clean.py` `PASS` confirmation.
