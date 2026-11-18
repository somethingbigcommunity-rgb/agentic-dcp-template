# AGENTS.md

Global rules (prompt level L1) for every agent working in this repository, in any harness (GitHub Copilot, Antigravity). This repository follows the **Agentic Software Engineering (ASE) harness v0.2**.

## Project configuration

Filled in by `/ase-setup` during P0 (new project, `remote` Git mode) or by `/ase-adopt` (existing or local repository, `local` Git mode). In a new project with no local or remote `accepted`, the initial configuration is prepared in a task and integrated into `main` before the Human Owner authorizes the one-time creation of `accepted` from that verified commit. This creation is not a merge. Once `accepted` exists, changing its configuration requires a PR; never overwrite or move an existing `accepted`. Lowering the mode requires HAG-06.

| Setting | Value |
|---------|-------|
| Working mode | `Lite` <!-- Lite | Standard | Enterprise --> |
| Engine | `antigravity` <!-- antigravity | vscode | ai-studio --> |
| Project context | `work` <!-- work | personal --> |
| Git mode | `remote` <!-- remote | local --> |
| Working branch | `main` |
| Accepted branch | `accepted` |
| Review policy | `reviewer` <!-- reviewer | solo-owner (Lite only) --> |
| Stack | _to be defined in P0_ |
| Fast CI command | `scripts/ci/fast.sh` |
| Gate CI command | `scripts/ci/gate.sh` |

## 1. Sources of truth

The project state has exactly three sources:

1. **Project Memory** (`project-memory/`): intent, decisions and state. Authoritative.
2. **GitHub**: versioned code and history. `accepted` holds the accepted version.
3. **Graphify** (if enabled): relationships derived from the code. Never overrides the other two.

External tools (Jira, Confluence, boards) are secondary: they may receive copies, never decide. If Project Memory and code diverge, report it; do not silently "fix" either side.

## 2. Project Memory, `.ase/` Encapsulation, and Lifecycle Artifact Directories

When installed into a repository via `install.py` (Option 1A default), only the required IDE hooks (`.agents/`, `.github/`, and `AGENTS.md` or `.agents/AGENTS.md`) sit at the repository root, while ASE's operational directories are encapsulated inside `.ase/` (`.ase/project-memory/`, `.ase/artifacts/`, `.ase/scripts/`, `.ase/templates/`). In a standalone template repository (`--flat`), they sit at the root. Whenever a skill or rule refers to `project-memory/`, `artifacts/`, `scripts/`, or `templates/`, use `.ase/<folder>/` when `.ase/` is present.

```
.ase/ (or root in --flat mode)
├── project-memory/
│   ├── dcp/     ← design intent (NORMATIVE), sections 00–07 (including waves/, features/, tasks/, user-stories/)
│   ├── adr/     ← one file per decision, ADR-NNN-<slug>.md (NORMATIVE)
│   └── state/   ← current state (DESCRIPTIVE, including state/reviews/)
├── artifacts/   ← generated lifecycle deliverables (verified zero-ASE-footprint)
│   ├── 01-discovery/            ← P0-A as-is-report PDFs & discovery notes
│   ├── 02-planning/             ← P1–P4 project-plan PDFs & roadmaps
│   ├── 03-architecture/         ← P3 architecture-dossier PDFs & diagrams
│   ├── 04-verification/         ← P6–P7 reconciliation reports & test/benchmark evidence
│   ├── 05-release-and-handover/ ← P7–P8 release-report PDFs, PR descriptions & stakeholder messages
│   └── specs/                   ← JSON specs for build-stakeholder-pdf.py
├── scripts/     ← deterministic helpers (next-id.py, append-task-log.py, build-traceability.py, etc.)
└── templates/   ← document and PDF templates
```

- **Normative** files (`dcp/`, `adr/`) change only through human approval (HAG-02 for architecture). Exception: the `status` and `correction_cycles` fields of task files in `dcp/04-implementation/tasks/` are descriptive.
- **Descriptive** files (`state/`) are updated by agents at step 7 of the Iteration Protocol without approval.
- `state/TASK_LOG.md` is append-only. `state/TRACEABILITY.md` is generated; never edit it by hand.
- Read only what the current task needs. Start from `state/NEXT_TASK.md` and the task file.

## 3. Git model

- `main` is the working branch. CI runs on every push when automation is configured; in a local-only project without CI automation, run the declared Fast CI command on `main` and record it as local gate evidence, not hosted CI.
- Agents in VS Code work on short branches `task/<ID>` and merge into `main` after the preliminary check with green CI.
- `accepted` must be protected where GitHub supports it: require a PR from `main`, the `gate / gate` check, and the configured review policy. **No agent ever merges into `accepted`** (HAG-01). With `Review policy` `reviewer`, the PR needs an approval from an eligible human other than its author; with `solo-owner` (Lite only, for single-person projects), no approving review is required, and the Human Owner's own merge after reading the PR is the HAG-01 approval.
- If repository plan or permissions make branch protection unavailable, the Human Owner may explicitly approve a procedural fallback under HAG-06, recorded in `project-memory/state/M0_CHECKLIST.md`. The procedure still requires a PR from `main`, a successful `gate / gate` run before the Human Owner merges, and a post-merge `bash scripts/verify-accepted.sh <PR-number>` audit. No agent merges into `accepted`. This fallback cannot technically prevent direct pushes or an early merge; record and accept that residual risk explicitly. If a distinct eligible reviewer is required by the configured `Review policy`, the fallback does not waive that requirement.
- One engine at a time writes to `main`.
- One Work Package is open on `main` at a time; its PR is opened when the WP is complete.
- Commit messages start with the task ID (`T-0117: ...`). PR titles start with the WP ID (`F-021: Upload PDF`).

### Local Git mode

With `Git mode` `local` (set by `/ase-adopt`), ASE runs on the Human Owner's machine inside a repository whose Git process belongs to someone else (team, company). The ASE files are usually excluded from Git through `.git/info/exclude`.

- `Working branch` is the branch the Human Owner works on; `Accepted branch` is `none`. The team's own branch, PR, review and CI rules apply unchanged.
- Agents **never commit, push, rebase, switch or create branches, open PRs, or change remote settings**. They leave changes in the working tree; the Human Owner reviews the diff and commits. Read-only Git commands are allowed.
- `Fast CI command` and `Gate CI command` are the repository's existing commands (for example `npm test`, `mvn -q verify`), recorded by `/ase-adopt`. If a command is `none`, say so; never claim a check passed.
- A task becomes `DONE` when its criteria have evidence, the declared Fast command passes locally, and the Human Owner accepts the diff (HAG-01 in local mode). Until then it stays `IN_REVIEW`.
- Never put ASE IDs, Project Memory content or internal notes into code, commit messages or PRs unless the Human Owner asks.
- Sections about `main`, `accepted`, task branches and hosted workflows apply only to `remote` mode.

## 4. Work hierarchy and IDs

Project → Wave → Feature → User Story → Task. Every Work Package (usually a Feature) maps to exactly one PR.

| Type | Format | Type | Format |
|------|--------|------|--------|
| Requirement | `REQ-NNN` | User Story | `US-NNN` |
| Wave | `W-NN` | Task | `T-NNNN` |
| Feature | `F-NNN` | ADR | `ADR-NNN` |
| Other WP | `WP-NNN` | Defect | `BUG-NNN` |

IDs are flat, stable, sequential per type and never reused. Hierarchy lives in the `parent` front matter field, external keys in `external`. Test names cite the `US-NNN` or `REQ-NNN` they verify.

For persistent application records, do not reuse identifiers while stale references could still target a replacement record. Prefer UUIDs or a database-supported non-reusing key (for SQLite integer keys, `INTEGER PRIMARY KEY AUTOINCREMENT`); test that a stale delete/update cannot affect a later record after deletion or clear-all.

## 5. Task execution

- Execute **one task at a time** with the Iteration Protocol (`dcp/04-implementation/iteration-protocol.md`): input, pre-implementation, planning, implementation, verification, reporting, state update, stop.
- Implement only the assigned task. No unrelated changes, no future tasks.
- **No change outside a task.** Every change to the repository (code, dependencies, configuration, documentation) happens inside a task file. If asked for a change with no assigned task, do not perform it: propose the task (goal, risk, criteria), create it with `/ase-plan` or the template, and wait until it is assigned. There are no exceptions, commands included: each run of `/ase-setup` or `/ase-plan` first opens its own task file (e.g. `T-0001: P0 setup`, `T-0012: plan W-02`), writes only within that task and logs it in `TASK_LOG.md` when closed. Creating a task file in `TODO` is how a task starts, so it is not a change outside a task. Read-only questions and analysis need no task.
- Task states: `TODO → IN_PROGRESS → IN_REVIEW → DONE`, or `BLOCKED`.
- Each failed verification increments `correction_cycles`. **At the third failure the task becomes `BLOCKED`** and a human decides. In a local-only project without CI automation, a passing declared Fast CI command on `main` is the local gate evidence required for `DONE`; never describe it as hosted CI.
- On `DONE` or `BLOCKED`, append one line to `state/TASK_LOG.md`.
- If the task conflicts with an ADR or the architecture, stop and report: do not decide alone.

## 6. Risk class

Every task has `risk: low | medium | high`.

| Class | Typical scope | Extra controls |
|-------|---------------|----------------|
| low | UI, copy, local refactoring covered by tests | Standard PR checks |
| medium | New business logic, new APIs, shared components | Integration tests, review by the relevant specialist |
| high | Auth, data model, migrations, dependencies, cost or latency | Relevant security/performance tests, Security Reviewer or Solution Architect, matching HAGs. For record deletion, include stale-reference tests where applicable. |

## 7. Human Approval Gates

Decisions reserved to the human owner. Active gates depend on the working mode.

| ID | Decision | Lite | Standard | Enterprise |
|----|----------|:----:|:--------:|:----------:|
| HAG-01 | Human merge of a `main → accepted` PR after Gate/review checks (`remote`), or human acceptance and commit of the task diff (`local`); procedural fallback requires HAG-06 | ✓ | ✓ | ✓ |
| HAG-02 | ADRs, architectural changes, "as-is" baseline (M0-A) | ✓ | ✓ | ✓ |
| HAG-03 | Auth, authorization, data model, destructive migrations | ✓ | ✓ | ✓ |
| HAG-04 | Exceeding cost, latency or usage thresholds set in P0 | – | ✓ | ✓ |
| HAG-05 | New external dependencies or licenses | – | ✓ | ✓ |
| HAG-06 | Waiver of a quality gate or a harness rule | ✓ | ✓ | ✓ |
| HAG-07 | Milestones M3, M7, M8 and releases | – | ✓ | ✓ |

When an active gate applies, stop and ask; record approved architectural decisions as ADRs.

## 8. Commands

| Command | Purpose |
|---------|---------|
| `/ase-setup` | Lite P0 for a new GitHub project (`remote` Git mode): mode, engine, stack, branches, Project Memory, and the M0 checklist |
| `/ase-adopt` | P0-A Lite for an existing or local-only repository (`local` Git mode): read the code, rebuild the minimal DCP, record the as-is baseline (M0-A, HAG-02) |
| `/ase-plan` | Propose an MVP and create or update an approved, traceable Lite backlog; assign the first ready task in `NEXT_TASK.md` |
| `/ase-task` | Run the next task with the Iteration Protocol |
| `/ase-review` | Preliminary check, traceability matrix, PR of the WP to `accepted` with DoD evidence (`remote`), or a review report and PR description draft for the human (`local`) |
| `/ase-plugin` | Scaffold, validate, and sync project-derived reusable domain plugins (`plugins/<slug>/`) with zero ASE dependency |

The full agent roster (DEC-05) is installed natively for both harnesses: `.github/agents/*.agent.md` for GitHub Copilot and `.agents/agents/*.md` for Antigravity. Start from `ASE Lead`; it delegates to specialists only when the task needs them. Skills live in `.agents/skills/` (read natively by both); file-scoped rules are in `.github/instructions/` (Copilot) and `.agents/rules/` (Antigravity). Agents follow this file; they do not add authority.

If the skill for a command is not installed, say so instead of improvising its behavior.

## 9. Language

Harness files (skills, role cards, agents, rules, templates, this file) are in English.

## 10. External-facing artifacts, stakeholder PDFs, and reusable domain plugins

1. **Zero ASE footprint on external-facing artifacts (`scripts/verify-external-clean.py`):**
   - Every artifact potentially shared with external people or systems (stakeholder PDFs `*.pdf`, exported domain plugins `plugins/**`, application code/schemas/queries, external documentation `docs/**`, and local-mode PR drafts `project-memory/state/reviews/*.md`) must be verified free of references to the ASE framework (`Agentic Software Engineering`, `ASE`, `agentic-dcp-template`, `dcp-template`, `Development Context Package`, `DCP`, `Project Memory`, `project-memory/`, `HAG-01`..`HAG-07`, `Human Approval Gate`, `Iteration Protocol`, `/ase-*`, `M0-A`, `.ase-install.json`, `ase-lead`).
   - Standard planning and requirement identifiers (`W-01`, `T-001`, `T-0001`, `REQ-001`, `F-001`, `US-001`, `WP-001`, `ADR-001`) are allowed in plans and stakeholder PDFs.
   - Run `python3 scripts/verify-external-clean.py <paths>` before marking a task `IN_REVIEW`/`DONE` or handing off an external deliverable, and record the `PASS` output.
2. **Optional stakeholder-level PDF documentation (`scripts/build-stakeholder-pdf.py`):**
   - At key milestones — P0-A adoption (`as-is-report`), P1–P4 planning (`project-plan`), P3 architecture (`architecture-dossier`), and P7/P8 review/release (`release-report`) — proactively offer to generate an optional stakeholder-level PDF using `templates/stakeholder-pdf-template.json` and `python3 scripts/build-stakeholder-pdf.py --spec <spec.json> --output <file.pdf>`.
   - Use `context_profile: "work"` (when `Project context` is `work`, applying the **Sopra Steria Group** brand color palette and corporate metadata) or `context_profile: "personal"` (when `Project context` is `personal`, selecting the palette preset best suited to the project domain).
3. **Proactive ASE-external reusable domain plugins (`/ase-plugin` & `scripts/sync-plugin.py`):**
   - When the project uses domain-specific guardrails, multi-tool stack conventions, or deterministic validators that could be reused across similar projects, proactively propose packaging them into `plugins/<plugin-slug>/` (HAG-02) via `/ase-plugin`, completely decoupled from ASE.

## 11. Communication voice and authorship — strictly "I", never "We"

1. **ASE has no voice or co-authorship:** ASE is an internal engineering harness, never a speaker or team member.
2. **In direct conversation with the Human Owner:** Address the Human Owner as `"you"` (`"tu"`) and refer to your own agent actions in first-person singular (`"I"` / `"Io"`). **Never** use collaborative first-person plural (`"we"`, `"us"`, `"our"`, `"noi"`, `"abbiamo"`) to describe work done in the project.
3. **In all drafted messages, answers, emails, commit messages, PR descriptions, review summaries, and stakeholder documents proposed for the Human Owner:** Write strictly in the **Human Owner's first-person singular voice (`"I"` / `"Io"` / `"Ho..."`)** — never `"we"` / `"noi"` / `"abbiamo"`. Verify drafted handover/review files with `python3 scripts/verify-external-clean.py --check-first-person <paths>` (automatically enforced on `05-release-and-handover/` and `state/reviews/`).
