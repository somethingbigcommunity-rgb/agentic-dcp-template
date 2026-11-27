# ASE v0.4.0

## v0.4.0 — 2026-11-24

Goal: non-overlapping command responsibilities with deterministic Step 0 prerequisite enforcement (`scripts/check-prereq.py`), 3-Zone Workspace separation (visible root `deliverables/` + hidden `.ase/specs/` + automatic `.vscode/settings.json` `files.exclude` Explorer cleanup), in-place post-work deliverable curation (`/ase-pack`), and one-click external stakeholder `.zip` handover export (`/ase-export`).

- **Federated Multi-Project Hierarchy (`orchestrator` vs. `member`), Polymorphic `HANDOFF.json` Protocol, Single-Channel Output Rule & Explicit `/ase-memo`, `/ase-switch`, and `/ase-upgrade` Skills (`scripts/ase-topology.py`, ADR-009)**:
  - **Umbrella Father Orchestrator + Autonomous Child Projects (`scripts/ase-topology.py`):** Auto-detects `standalone`, `orchestrator` (Father Umbrella Root), `member` (Child ASE Project), and `unmanaged_child` subfolders in `< 10ms` (`0` LLM tokens); proactively offers `--onboard-child` for unmanaged sub-projects.
  - **Polymorphic 6-Type & Temporal (`T0..T3`) `HANDOFF.json` Protocol:** Supports `ONBOARD_ADOPT`, `CONTEXT_MEMO_SYNC`, `CONTRACT_AND_PLAN`, `TASK_OR_HOTFIX_EXECUTION`, `INTEGRATION_REVIEW_GATE`, and `DELIVERABLE_PACK_ROLLUP` handoffs with automatic sibling dependency DAG unblocking (`WAITING_DEPENDENCY -> PENDING`), SHA-256 contract drift alerts, and `0`-token `state/FEDERATION_STATE.json` rollups.
  - **Single-Channel Output Rule (`AGENTS.md` §11.4):** Ephemeral answers are written only in chat; persistent documents are written only once to their single canonical file on disk with a 2–4 line clickable pointer in chat (zero duplicate file mirroring across `docs/` and `deliverables/`).
  - **Explicit First-Class `/ase-memo`, `/ase-switch`, and `/ase-upgrade` Skills:** Dedicated `.agents/skills/{ase-memo,ase-switch,ase-upgrade}/SKILL.md` directories for IDE slash-command autocomplete, with `/ase-switch` and `/ase-upgrade` cascading CDC upgrades across all `member` children in an Umbrella workspace.
- **Continuous Project Memory Updates (`/ase-plan` + `/ase-memo` & `/ase-context`), Autonomous 2-Bucket HAG Triage, Graphify Synergy & Reactive Command Chaining (`scripts/sync-inputs.py`, `scripts/check-prereq.py`, ADR-008)**:
  - **Zero Command Bloat (`/ase-memo` & `/ase-context` aliases):** Built into `/ase-plan` (Context & Memory Update Mode) so pasting call notes, teammate messages, or screenshots in chat or dropping files in `inputs/` updates Project Memory with zero `T-NNNN` task ceremony.
  - **Incremental `inputs/` Digest Tracking (`state/INPUTS_STATE.json`):** `scripts/sync-inputs.py` tracks SHA-256 hashes of files in `inputs/` so only newly added or modified files are read, enforces secret-hygiene scanning (`HAG-03`), patches `project-charter.md` row-by-row with `HAG-03`/`04` gate protection, and appends to `state/CONTEXT_LOG.md`.
  - **Graphify Synergy (`--query-graph` & `.graphifyignore`):** Queries `graphify-out/graph.json` locally in `0` tokens to identify God-Node coupling (`HAG-02`) and open-task impact (`T-NNNN`), gates semantic Graphify `--update` runs under `HAG-04`, and excludes internal ASE paths via `.graphifyignore`.
  - **3-Category Approval-Gated Reactive Command Chaining (`check-prereq.py` Step 0 & `--post`):** Replaces dead-end `BLOCKED` errors with upstream `prerequisite_chain` resolution and downstream `--post` cascade triggers, persisting pending chains in `state/NEXT_TASK.md`.
- **Change-Data-Capture (CDC) & Row-by-Row In-Flight Release Switcher (`/ase-switch`, `scripts/switch-release.py`, `install.py --switch`, ADR-007)**: clone the new ASE release into the workspace root and run `/ase-switch` (or `python3 agentic-dcp-template/install.py . --switch`); leaves unchanged files/rows untouched (`0` writes), patches `AGENTS.md` and `NEXT_TASK.md` row-by-row, auto-synthesizes `project-charter.md`, relocates moved paths (`.ase/artifacts/` → `deliverables/`), and deletes all traces of the old release and the cloned template folder.
- **Root `inputs/` Initial Context Inbox, 3-Tier Discovery Order & Adaptive `work`/`personal` `6W+1H` Profiles (ADR-006)**: pre-creates `inputs/` at the workspace root so `/ase-adopt`, `/ase-setup`, and `/ase-plan` read your briefs/notes/PDFs **first** before scanning repo metadata or asking questions; applies a complete Enterprise `6W+1H` profile (`project-charter.md`) for `work` projects vs. a lean 6-item profile for `personal` projects, with every question/section skippable (`SKIPPED — not relevant`).
- **10 Optimization Drivers, HAG Correlation (`HAG-04` & `HAG-05` in Lite) & Command Priorities (ADR-005)**: embeds the 5 Factors to Reduce (*Cost, Time/Latency, Cognitive Load, Blast Radius/Rework, Debt/Coupling*) and 5 Factors to Augment (*Quality/Determinism, Security/Privacy, Usability UX/DX, Reusability, Traceability/Clarity*) across `AGENTS.md` §12, role cards, and skills, and activates `HAG-04` (cost/latency) and `HAG-05` (new external dependencies) in `Lite` mode.
- **Deterministic Command Prerequisite Guard (`scripts/check-prereq.py`, ADR-004)**: enforced as Step 0 of all 9 `/ase-*` commands; blocks out-of-order invocations (such as `/ase-export` before `/ase-pack`, or `/ase-review` / `/ase-pack` while a task is `IN_PROGRESS` or `PAUSED` on the Return Stack) and tells the Human Owner which command to run first.
- **3-Zone Workspace Layout & Automatic IDE Explorer Cleanup (`deliverables/` + `.vscode/settings.json`, ADR-004)**: stakeholder deliverables (`01-discovery/` .. `05-release-and-handover/`) live visibly in `deliverables/` at the repository root while internal PDF JSON specs move to `.ase/specs/`, and `install.py` configures `.vscode/settings.json` (`files.exclude`) to hide internal ASE folders from the Explorer sidebar (`--show-harness` / `--hide-harness`).
- **In-Place Post-Work Curation (`/ase-pack` & `scripts/pack-workspace.py`, ADR-004)**: curates `deliverables/`, generates `deliverables/INDEX.md` in first-person singular (`"I"`), hides empty `01..05` folders in `.vscode/settings.json`, verifies zero-ASE-footprint, records `state/PACK_STATE.json`, and offers `/ase-export`.
- **One-Click Stakeholder Handover Bundle (`/ase-export` & `scripts/export-handover.py`, ADR-004)**: requires a fresh `/ase-pack` and bundles clean `project-files/` + `deliverables/` into `handover/<project>-handover-YYYY-MM-DD/` and `.zip`.

## v0.3.0 — 2026-11-23

Goal: proactive remote- and milestone-aware Git proposals (`scripts/git-advisor.py`), unified WBS roadmap interruption sequences (`T-NNNN.1`, `T-NNNN.1.1`) with the `NEXT_TASK.md` Return Stack and pivot states (`PAUSED`, `DEFERRED`, `SUPERSEDED`), and read-only daily project situation reports (`/ase-status` + `scripts/project-status.py`).

## v0.2.0 — 2026-11-18

Goal: full Antigravity & Copilot parity, existing-repository adoption (`--upgrade`), proactive ASE-external reusable plugins, optional stakeholder-level PDF deliverables (`work` Sopra Steria Group vs `personal` palettes), and mandatory zero-ASE-footprint verification on external artifacts.

- **Local Git mode & Proactive Milestone Git Advisor (`scripts/git-advisor.py`, ADR-002)**: at every milestone (`m0`, `plan`, `task`, `review`, `release`), `git-advisor.py` inspects remote connectivity (`no-remote` vs `github-remote`), branch tracking, and `.ase-install.json` versioned state to propose exact Git/GitHub commands. In `Project context: personal`, agents offer to execute the proposed commit, push, tag, PR, or release commands upon confirmation (`HAG-01`); in `Project context: work`, agents present the commands for manual execution only and never run Git mutations themselves.
- **`install.py` & Encapsulated `.ase/` Layout (Option 1A)**: installs into any Git repository without overwriting files, encapsulates `.ase/project-memory/`, `.ase/artifacts/`, `.ase/scripts/`, and `.ase/templates/` while keeping `.agents/`, `.github/`, and `AGENTS.md` at the root, excludes ASE files from Git by default, keeps a team `AGENTS.md` (ASE rules go to `.agents/AGENTS.md` with `.agents/rules/ase.md` and `.github/instructions/ase.instructions.md` pointers), and supports `--upgrade`, `--verify-layout`, `--flat`, `--no-git`, `--dry-run`, `--versioned`, `--uninstall`.
- **Lifecycle Artifact Directories (`artifacts/01-discovery/`..`05-release-and-handover/` & `specs/`)**: pre-created folders for every lifecycle deliverable (`as-is-report`, `project-plan`, `architecture-dossier`, reconciliation/verification evidence, `release-report`, and ready-to-paste PR descriptions), plus all DCP folders (`waves/`, `features/`, `state/reviews/`).
- **Strictly First-Person Singular (`"I"`, Never `"We"`) Voice Rule (`AGENTS.md` §11 & `--check-first-person`)**: agents never use `"we"` / `"noi"` when speaking to the Human Owner or drafting messages/commits/PRs; `verify-external-clean.py --check-first-person` enforces first-person singular on handover and review drafts.
- **`/ase-adopt`** (P0-A Lite): reconstructs a minimal as-is DCP from the code, records stack and existing test commands, M0-A baseline under HAG-02. Optional local Graphify.
- **Proactive ASE-External Reusable Plugins (`/ase-plugin` & `scripts/sync-plugin.py`)**: identifies repeatable domain skills, rules, and validators, scaffolds them under `plugins/<slug>/` with zero ASE dependency, and syncs them locally (`.agents/` + `.github/`) or globally (`~/.gemini/config/plugins/<slug>/`).
- **Optional Stakeholder-Level PDF Documentation (`scripts/build-stakeholder-pdf.py` & `templates/stakeholder-pdf-template.json`)**: pure-Python Type1 PDF generator with Adobe AFM metrics, native HD vector diagrams (Work Hierarchy & PERT/CPM Critical Path), and formalized `context_profile` modes (`work` = Sopra Steria Group palette & corporate metadata; `personal` = project-suited palette & metadata).
- **Mandatory Zero-ASE-Footprint Verification (`scripts/verify-external-clean.py`)**: inspects text files and `.pdf` streams to block ASE framework references (`Agentic Software Engineering`, `ASE`, `DCP`, `HAG-01..07`, `M0-A`, `/ase-*`, `project-memory/`, `.ase-install.json`, `ase-lead`) while allowing standard project/requirement IDs (`W-01`, `T-001`, `REQ-001`).
- **WBS Roadmap Interruption Sequences (`T-NNNN.1`, `T-NNNN.1.1`), Return Stack & Pivots (ADR-003)**: `next-id.py --type task --under <T-ID>` allocates WBS-style dotted sub-task IDs (`T-0008 -> T-0008.1 -> T-0008.1.1`) for mid-roadmap inner sequences while pausing the interrupted task (`PAUSED`) on the `NEXT_TASK.md` Return Stack; supports `DEFERRED` and `SUPERSEDED` states for roadmap pivots.
- **Daily Project Situation Report (`/ase-status` & `scripts/project-status.py`, ADR-003)**: read-only daily pulse for multi-week projects covering roadmap position, WBS detour visibility, Return Stack status, daily delta, critical insights/risks, a dedicated `Next Steps` paragraph, a ready-to-paste first-person singular (`"I"`) standup snippet, and a non-automatic proposal to save a Markdown report or stakeholder PDF.
- **Quick task** in `/ase-plan` for bug fixes and small changes; local variants of `/ase-task` and `/ase-review` (review report + PR draft).
- **Full agent roster** (DEC-05, 18 roles + `ASE Lead`) generated natively for both harnesses: `.github/agents/*.agent.md` (Copilot) and `.agents/agents/*.md` (Antigravity); glob rules in `.github/instructions/` and `.agents/rules/`. Skills stay in `.agents/skills/`, which both read natively.

Limits: alpha, validated by automated tests (installer, parity of generated files) and adapted for Google Antigravity native `.agents` (`read_file`, `edit_file`, `write_file`, `run_command`, `manage_task`, `invoke_subagent`, `send_message`, `manage_subagents`, `ask_question`, `search_web`, `subagent`/`mainAgent` frontmatter, and `**/`-prefixed rule globs). Remote-mode limits of v0.1.0 below still apply.

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
