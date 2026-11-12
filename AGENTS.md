# AGENTS.md

Global rules (prompt level L1) for every agent working in this repository, in any harness (GitHub Copilot, Antigravity). This repository follows the **Agentic Software Engineering (ASE) harness v0.1**.

## Project configuration

Filled in by `/ase-setup` during P0. Changing it requires a PR to `accepted`; lowering the mode requires HAG-06.

| Setting | Value |
|---------|-------|
| Working mode | `Lite` <!-- Lite | Standard | Enterprise --> |
| Engine | `vscode` <!-- vscode | ai-studio --> |
| Working branch | `main` |
| Accepted branch | `accepted` |
| Stack | _to be defined in P0_ |
| Fast CI command | `scripts/ci/fast.sh` |
| Gate CI command | `scripts/ci/gate.sh` |

## 1. Sources of truth

The project state has exactly three sources:

1. **Project Memory** (`project-memory/`): intent, decisions and state. Authoritative.
2. **GitHub**: versioned code and history. `accepted` holds the accepted version.
3. **Graphify** (if enabled): relationships derived from the code. Never overrides the other two.

External tools (Jira, Confluence, boards) are secondary: they may receive copies, never decide. If Project Memory and code diverge, report it; do not silently "fix" either side.

## 2. Project Memory

```
project-memory/
├── dcp/     ← design intent (NORMATIVE), sections 00–07
├── adr/     ← one file per decision, ADR-NNN-<slug>.md (NORMATIVE)
└── state/   ← current state (DESCRIPTIVE)
```

- **Normative** files (`dcp/`, `adr/`) change only through human approval (HAG-02 for architecture). Exception: the `status` and `correction_cycles` fields of task files in `dcp/04-implementation/tasks/` are descriptive.
- **Descriptive** files (`state/`) are updated by agents at step 7 of the Iteration Protocol without approval.
- `state/TASK_LOG.md` is append-only. `state/TRACEABILITY.md` is generated; never edit it by hand.
- Read only what the current task needs. Start from `state/NEXT_TASK.md` and the task file.

## 3. Git model

- `main` is the working branch. CI runs on every push when automation is configured; in a local-only project without CI automation, run the declared Fast CI command on `main` and record it as local gate evidence, not hosted CI.
- Agents in VS Code work on short branches `task/<ID>` and merge into `main` after the preliminary check with green CI.
- `accepted` is protected. It changes only through a PR `main → accepted`, whose CI is the binding gate. **No agent ever merges into `accepted`** (HAG-01).
- One engine at a time writes to `main`.
- One Work Package is open on `main` at a time; its PR is opened when the WP is complete.
- Commit messages start with the task ID (`T-0117: ...`). PR titles start with the WP ID (`F-021: Upload PDF`).

## 4. Work hierarchy and IDs

Project → Wave → Feature → User Story → Task. Every Work Package (usually a Feature) maps to exactly one PR.

| Type | Format | Type | Format |
|------|--------|------|--------|
| Requirement | `REQ-NNN` | User Story | `US-NNN` |
| Wave | `W-NN` | Task | `T-NNNN` |
| Feature | `F-NNN` | ADR | `ADR-NNN` |
| Other WP | `WP-NNN` | Defect | `BUG-NNN` |

IDs are flat, stable, sequential per type and never reused. Hierarchy lives in the `parent` front matter field, external keys in `external`. Test names cite the `US-NNN` or `REQ-NNN` they verify.

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
| high | Auth, data model, migrations, dependencies, cost or latency | Relevant security/performance tests, Security Reviewer or Solution Architect, matching HAGs |

## 7. Human Approval Gates

Decisions reserved to the human owner. Active gates depend on the working mode.

| ID | Decision | Lite | Standard | Enterprise |
|----|----------|:----:|:--------:|:----------:|
| HAG-01 | Merge of a PR into `accepted` | ✓ | ✓ | ✓ |
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
| `/ase-setup` | P0 (new project) or P0-A (existing repository): mode, engine, branches, Project Memory |
| `/ase-plan` | Propose an MVP and create or update an approved, traceable Lite backlog; assign the first ready task in `NEXT_TASK.md` |
| `/ase-task` | Run the next task with the Iteration Protocol |
| `/ase-review` | Preliminary check, traceability matrix, PR of the WP to `accepted` with DoD evidence |

If the skill for a command is not installed, say so instead of improvising its behavior.

## 9. Language

Harness files (skills, role cards, agents, rules, templates, this file) are in English.
