---
name: ase-switch
description: Switch an ongoing project from an older ASE release to a newly cloned ASE release in the workspace root using Change-Data-Capture (CDC) and row-by-row diff-patching (scripts/switch-release.py / install.py --switch), keeping unchanged files/rows untouched, relocating moved paths, and deleting all traces of the old release and cloned folder. Use when asked to run /ase-switch or upgrade ASE mid-project.
---

# `/ase-switch`

> If the repository's root `AGENTS.md` belongs to the team and is not the ASE rules file, the installer placed the ASE rules in `.agents/AGENTS.md`; every reference to `AGENTS.md` in this skill means that file. Always use first-person singular (`"I"`, addressing the Human Owner as `"you"`, never `"we"`).

Switch an ongoing project in-place from an older ASE release to a newly cloned ASE release (`./agentic-dcp-template/`) using deterministic Change-Data-Capture (CDC) and row-by-row diff-patching (`ADR-007`).

## 0. Check prerequisites & discover the cloned release

Run from the repository root:

```sh
python3 scripts/check-prereq.py --command ase-switch   # or python3 .ase/scripts/check-prereq.py --command ase-switch
```

If no cloned release folder is present in the workspace root, tell the Human Owner to clone the new release into the workspace root first (`git clone https://github.com/somethingbigcommunity-rgb/agentic-dcp-template.git`) or supply `--from-release /path/to/template`.

## 1. Execute the deterministic CDC & row-by-row release switch

Run the switcher from the newly cloned release (or from `.ase/scripts/switch-release.py`):

```sh
python3 agentic-dcp-template/install.py . --switch     # or python3 .ase/scripts/switch-release.py
```

What this does deterministically in under 1 second:
1. **Mode A (`UNCHANGED`):** Leaves all unchanged files and all existing project data (`dcp/**`, `adr/**`, `state/**`, `deliverables/**`) in their exact position on disk with `0` writes.
2. **Mode B (`ROW / SECTION PATCH`):**
   - Merges `AGENTS.md` (or `.agents/AGENTS.md`) row-by-row: preserves every configured `<Value>` row in `## Project configuration` and any custom user sections while patching only changed rule rows/sections (`## 1.`..`## 12.`).
   - Patches `state/NEXT_TASK.md` in place: preserves your active task rows (`ID`, `File`, `Status`) and appends `## Inner Sequence Queue & Return Stack` if absent.
   - Auto-synthesizes `dcp/00-project-management/project-charter.md` if absent (marking uncollected `6W+1H` rows as `SKIPPED (auto-migrated from prior release)` so `check-prereq.py` never interrupts you with onboarding questions).
3. **Mode C (`LINE-DIFF UPDATE`):** Updates only the harness skills, agents, rules, scripts, and templates whose SHA-256 changed between releases.
4. **Mode D (`SELECTIVE RELOCATION & ZERO-TRACE CLEANUP`):**
   - Moves only paths whose canonical position changed between releases (`.ase/artifacts/01..05/` → `deliverables/01..05/`, `.ase/artifacts/specs/` → `.ase/specs/`, or legacy `--flat` root `project-memory/` → `.ase/project-memory/`).
   - Deletes retired old-release files, deletes `.ase/artifacts/`, deletes the cloned `./agentic-dcp-template/` directory from the workspace root, and deletes the `/tmp` rollback buffer once verification passes.

## 2. Report the seamless transition

Report the `old_version -> new_version` transition, the count of unchanged files kept in place vs. patched rows/files, any relocated paths, any `HAG-03`/`04`/`05` driver advisories on open tasks, and the current active task in `NEXT_TASK.md` so the Human Owner can continue working immediately.
