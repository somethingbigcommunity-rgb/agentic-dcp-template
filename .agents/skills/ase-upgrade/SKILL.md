---
name: ase-upgrade
description: Upgrade or switch an ongoing project (or an entire multi-project Umbrella Father + Child hierarchy) from an older ASE release to a newly cloned ASE release in the workspace root using Change-Data-Capture (CDC) and row-by-row diff-patching (scripts/switch-release.py / install.py --switch / --upgrade), keeping unchanged files/rows untouched and deleting all traces of the old release and cloned folder. Use when asked to run /ase-upgrade or /ase-switch.
---

# `/ase-upgrade` (Interchangeable with `/ase-switch`)

> If the repository's root `AGENTS.md` belongs to the team and is not the ASE rules file, the installer placed the ASE rules in `.agents/AGENTS.md`; every reference to `AGENTS.md` in this skill means that file. Always use first-person singular (`"I"`, addressing the Human Owner as `"you"`, never `"we"`), and follow the **Single-Channel Output Rule** (`AGENTS.md` §11.4).

Upgrade an ongoing project (and all `member` child projects when run in a Father Umbrella workspace) in-place from an older ASE release to a newly cloned ASE release (`./agentic-dcp-template/`) using deterministic Change-Data-Capture (CDC) and row-by-row diff-patching (`ADR-007`, `ADR-009`).

## 0. Check prerequisites & discover the cloned release

Run from the repository root:

```sh
python3 scripts/check-prereq.py --command ase-upgrade  # or python3 .ase/scripts/check-prereq.py --command ase-upgrade
```

If no cloned release folder is present in the workspace root, tell the Human Owner to clone the new release into the workspace root first (`git clone https://github.com/somethingbigcommunity-rgb/agentic-dcp-template.git`) or supply `--from-release /path/to/template`.

## 1. Execute the deterministic CDC & row-by-row release upgrade

Run the switcher from the newly cloned release (or from `.ase/scripts/switch-release.py`):

```sh
python3 agentic-dcp-template/install.py . --switch     # or python3 .ase/scripts/switch-release.py
```

What this does deterministically in under 1 second:
1. **Mode A (`UNCHANGED`):** Leaves all unchanged files and all existing project data (`dcp/**`, `adr/**`, `state/**`, `deliverables/**`, `HANDOFF.json`, `FEDERATION_STATE.json`) in their exact position on disk with `0` writes.
2. **Mode B (`ROW / SECTION PATCH`):** Merges `AGENTS.md` and `state/NEXT_TASK.md` row-by-row while keeping your project configuration and active task untouched, and auto-synthesizes `project-charter.md` if absent.
3. **Mode C (`LINE-DIFF UPDATE`):** Updates only the harness skills, agents, rules, scripts, and templates whose SHA-256 changed between releases.
4. **Mode D (`FEDERATED CHILD CASCADE & ZERO-TRACE CLEANUP`):**
   - If the workspace is a Father Umbrella Root (`role: orchestrator`), automatically cascades the CDC upgrade across every `member` child project (`<child>/.ase/`) before removing the cloned `./agentic-dcp-template/` directory!
   - Relocates moved paths (`.ase/artifacts/` → `deliverables/`), deletes retired old-release files, and deletes the cloned `./agentic-dcp-template/` folder.

## 2. Report the transition

Run `python3 scripts/check-prereq.py --post --command ase-upgrade` and report the `old_version -> new_version` transition, the count of unchanged vs. patched files (including any upgraded child projects), and the next recommended command.
