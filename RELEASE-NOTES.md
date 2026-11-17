# ASE v0.1.0

## v0.2.0-alpha — 2026-11-17

Goal: use ASE today, locally, on existing work repositories.

- **Local Git mode** (`Git mode: local` in `AGENTS.md`): agents never commit, push, switch branches or open PRs; the Human Owner accepts the diff (HAG-01 local). Team branch, PR and CI rules stay unchanged.
- **`install.py`**: installs into any Git repository without overwriting files, excludes ASE files from Git by default, keeps a team `AGENTS.md` (ASE rules go to `.agents/AGENTS.md`), supports `--dry-run`, `--versioned`, `--uninstall`.
- **`/ase-adopt`** (P0-A Lite): reconstructs a minimal as-is DCP from the code, records stack and existing test commands, M0-A baseline under HAG-02. Optional local Graphify.
- **Quick task** in `/ase-plan` for bug fixes and small changes; local variants of `/ase-task` and `/ase-review` (review report + PR draft).
- **Full agent roster** (DEC-05, 18 roles + `ASE Lead`) generated natively for both harnesses: `.github/agents/*.agent.md` (Copilot) and `.agents/agents/*.md` (Antigravity); glob rules in `.github/instructions/` and `.agents/rules/`. Skills stay in `.agents/skills/`, which both read natively.

Limits: alpha, validated by automated tests (installer, parity of generated files) but not yet on a real work repository. Antigravity agent `tools` use only documented tool names (`view_file`, `grep_search`, `run_command`, `replace_file_content`); creating new files from an Antigravity subagent may need an adjusted tool list. Remote-mode limits of v0.1.0 below still apply.

Initial reusable release, authorized by the Human Owner on 2026-11-17.

## Supported scope

- New projects, Lite mode, GitHub Copilot in VS Code.
- `/ase-setup`, `/ase-plan`, `/ase-task`, and `/ase-review`.
- Project Memory, stable IDs, task logging, derived traceability, role cards, and stack-independent CI workflows.
- Human-owned `main -> accepted` PRs, with protected branches where available or an explicitly approved HAG-06 procedural fallback.

## Pilot lessons included

- Planning tasks have no backlog parent; Wave/Feature context belongs in their notes.
- Persistent record IDs should not be reused when stale references could target replacement records.
- An unavailable specialist review is `UNAVAILABLE`, not an independent review pass.
- Procedural gates cannot technically block direct pushes or premature merges. A passing PR Gate, human merge, and post-merge audit are still required.

## Validation and release exception

The source implementation has focused automated tests for the deterministic helpers, traceability, setup verification, branch policies, and post-merge audit. Copilot scenarios and a personal pilot exercised setup, planning, and implementation. Hosted pilot Fast and M0 Gate smoke runs succeeded; a smoke run is not the binding PR Gate.

On 2026-11-17 the Human Owner explicitly approved publishing v0.1.0 without completing the pilot product or all deferred scenarios. The following remain **NOT VERIFIED**, not passed:

- The complete agent-driven `/ase-review` flow through a real PR, successful binding Gate, human merge, and post-merge audit (S-005 and pilot closure).
- Hosted rejection of a real PR with a failing Gate (S-007).
- The full hosted S-008 scenario, including its branch-policy verification contract; partial pilot smoke evidence is not a full scenario pass.
- Remaining Antigravity scenarios, including S-003/S-004, and a complete pre-release scenario rerun.

These checks are deferred to v0.2. This is a release-validation exception, not permission to bypass M0, task criteria, PR checks, or human approval in projects created from the template. Do not treat this release as production certification.

## Limits

- Existing-repository adoption, Standard/Enterprise modes, AI Studio, and Antigravity certification are not supported by this release.
- Stack-specific checks must be configured during setup. This unconfigured skeleton does not contain project Fast/Gate scripts.
- The procedural post-merge audit verifies only the current `accepted` tip against a named merged PR; it cannot prove the absence of earlier direct writes.
- Pilot task logs do not measure every human interaction; no exact human-effort or productivity improvement is claimed.
