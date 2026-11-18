---
name: ase-adopt
description: "Adopt ASE Lite in an existing or local-only repository (P0-A, local Git mode): read the code, rebuild a minimal as-is DCP, record stack and test commands, and get the as-is baseline approved (M0-A). Use when asked to run /ase-adopt, use ASE on an existing/work repository, or onboard ASE without changing the team's Git process."
---

# `/ase-adopt`

> If the repository's root `AGENTS.md` belongs to the team and is not the ASE rules file, the installer placed the ASE rules in `.agents/AGENTS.md`; every reference to `AGENTS.md` in this skill means that file. When installed in encapsulated mode (Option 1A default), `project-memory/`, `artifacts/`, `scripts/`, and `templates/` live inside `.ase/` (`.ase/project-memory/`, `.ase/artifacts/`, `.ase/scripts/`, `.ase/templates/`).

Prepare ASE Lite in `local` Git mode on a repository that already exists (or that the Human Owner will not connect to the ASE GitHub workflow). The goal is a small, verified **as-is baseline** that lets `/ase-plan` and `/ase-task` work immediately. Do not redesign, refactor, or fix the application here. Always communicate in first-person singular (`"I"`, addressing the Human Owner as `"you"`, never `"we"`).

Never commit, push, create or switch branches, open PRs, install dependencies, or change CI, remote settings or application code. Do not read or record secrets (`.env`, credentials, tokens, private keys); describe them only as "configuration present".

## 1. Check the starting point and verify `.ase/` encapsulation

1. **Verify `.ase/` encapsulation and check for stray template clones before proceeding:**
   - Confirm that the workspace uses the encapsulated `.ase/` layout (`.ase/project-memory/`, `.ase/artifacts/`, `.ase/scripts/`, `.ase/templates/`) with only `.agents/`, `.github/`, and `AGENTS.md` at the repository root (run `python3 <template>/install.py . --verify-layout` if available, or check the folders directly).
   - Check whether a raw clone of `agentic-dcp-template` (e.g., `ase-tool/agentic-dcp-template/` or `agentic-dcp-template/`) is sitting inside the project workspace outside `.ase/template/`. If found, stop and warn the Human Owner so it can be moved into `.ase/template/` or outside the project workspace and excluded from Git before proceeding.
2. Read `AGENTS.md`, `.ase/project-memory/state/PROJECT_STATE.md` (or `project-memory/state/PROJECT_STATE.md` in `--flat` mode) and existing adoption tasks in `dcp/04-implementation/tasks/`.
3. If `PROJECT_STATE.md` already records `M0-A | PASS` and no update was requested, report the baseline read-only and stop.
4. Confirm with the Human Owner: that ASE files stay encapsulated in `.ase/` and local (default) or are versioned, the branch they work on, whether AI assistant (Antigravity / Copilot) use on this code is permitted by their organization, and whether Graphify may be used locally. Do not proceed without the organizational confirmation.
5. Create (or resume) one task `<ID>-adopt-<slug>.md` with `python3 .ase/scripts/next-id.py --type task` (or `scripts/next-id.py`) and `.ase/templates/task-template.md`: empty `parent`, `risk: medium`, `engine: antigravity` (or `vscode`), `status: IN_PROGRESS`, `correction_cycles: 0`. Load the Solution Architect and Technical Lead perspectives; no other roles are needed.

## 2. Discover the as-is system (read-only)

Inspect only what is needed, starting from the cheapest sources: `README*`, build manifests (`package.json`, `pom.xml`, `build.gradle*`, `pyproject.toml`, `requirements*.txt`, `go.mod`, `*.csproj`, `Cargo.toml`, `Dockerfile`, `docker-compose*`), CI definitions (`.github/workflows`, `.gitlab-ci.yml`, `Jenkinsfile`, `azure-pipelines.yml`), existing agent instructions (`GEMINI.md`, `.github/copilot-instructions.md`, `AGENTS.md`, `CONTRIBUTING*`), the top-level layout, entry points, and test folders. Use `git log --oneline -20` and `git branch --show-current` for context.

If Graphify is permitted and installed (via the `graphify` skill in Antigravity), you may build a local graph (`graphify-out/` stays local) to find modules, god nodes and dependencies. Graphify is derived knowledge: cite it, never let it override the code.

Record facts with their source file. Mark anything inferred as `ASSUMPTION` and anything unknown as `UNKNOWN`; do not invent architecture.

## 3. Propose the baseline

Show the Human Owner a concise proposal, then wait for explicit approval (HAG-02):

- **Configuration** for the `AGENTS.md` table: `Lite`, `antigravity` (or `vscode`), `Project context` (`work` or `personal`), `Git mode` `local`, `Working branch` (current branch), `Accepted branch` `none`, `Review policy` (`solo-owner` unless a reviewer exists), `Stack`, `Fast CI command` and `Gate CI command` taken from the repository's existing scripts/CI (or `none`).
- **As-is DCP** (short, facts first):
  - `dcp/00-project-management/README.md`: purpose of the system as stated in the repo, owner/team if stated, and how the Human Owner receives work (tickets, requests).
  - `dcp/02-architecture/as-is.md`: components and modules, entry points, data stores, external integrations, deployment hints, and a small Mermaid diagram if useful.
  - `dcp/03-design/conventions.md`: language versions, frameworks, code style, folder conventions, error handling, test conventions observed in the code.
  - `dcp/05-verification-validation/README.md`: how to build, run and test locally; which checks the team CI runs.
  - `state/KNOWN_ISSUES.md`: risks noticed (missing tests, outdated dependencies, TODO hot spots) without fixing them.
- Requirements, User Stories and an MVP are **not** reconstructed now; they are created later only for the work actually assigned.

## 4. Apply and verify

After approval:

1. Fill the `AGENTS.md` configuration table and write the approved DCP files and state. Keep each file short; link to repository files instead of copying them.
2. Run the declared Fast command once, unchanged, and record the exact command and result. A failure is recorded as the as-is baseline condition in `KNOWN_ISSUES.md`, not fixed and not hidden. If the command cannot run (missing tool or service), record `NOT RUN` and why.
3. Run `python3 scripts/build-traceability.py --mode lite` and confirm it executes.
4. Confirm the ASE files are not staged or tracked unless the Human Owner chose to version them: `git status --short` must not list them in `local` footprint.
5. Set `PROJECT_STATE.md` to `M0-A | PASS` with the approval date, stack, and baseline summary; leave `M0` as `NOT APPLICABLE (local Git mode)`. Set the task `DONE` and append one row with `scripts/append-task-log.py`.

## 5. Hand off

Report the configuration, files written, Fast result, known issues, and how to continue:

- one bounded change → `/ase-plan` quick task, then `/ase-task`;
- a larger feature → `/ase-plan` with the feature description;
- before the team PR → `/ase-review` in local mode for a review report and PR draft;
- **proactive plugin proposal (if applicable):** if discovery revealed domain-specific guardrails, multi-tool conventions, or reusable verification scripts that could benefit similar projects, proactively ask whether the Human Owner wants to package them into an ASE-external plugin via `/ase-plugin` (`plugins/<slug>/`);
- **optional stakeholder PDF proposal:** ask whether the Human Owner wants to generate an optional stakeholder-level **As-Is Discovery & Architecture Baseline PDF** (`doc_type: "as-is-report"`, saved to `.ase/artifacts/01-discovery/` with its spec in `.ase/artifacts/specs/`, using the configured `work` Sopra Steria Group profile or `personal` project-suited profile) via `build-stakeholder-pdf.py`.

Stop; do not start product work.
