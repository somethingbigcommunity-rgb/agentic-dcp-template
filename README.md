# Agentic DCP Template

Project template for the **Agentic Software Engineering (ASE) harness**. It contains the Development Context Package (DCP), the Project Memory skeleton and the agentic system (skills, role cards, agents, rules, CI workflows) shared by GitHub Copilot and Antigravity.

> Status: v0.1 under development. Skills are added increment by increment; see the CHANGELOG of the source repository.

## Start a new project

1. Create a repository with **Use this template**.
2. Open it in VS Code and run `/ase-setup`.
3. Once the M0 checklist is complete, run `/ase-plan`, then `/ase-task` for each task and `/ase-review` for each Work Package.

The v0.1 setup supports new projects in Lite mode with the `vscode` engine. Other modes, AI Studio, and adoption of existing repositories are not implemented. Graphify is optional.

`/ase-setup` asks for the stack and real Fast and Gate commands; it does not install dependencies or invent passing checks. It can prepare a project locally, but M0 also requires GitHub connectivity, protected `accepted`, and successful hosted checks. Creating the initial `accepted` branch, changing GitHub settings, pushing, and starting the hosted smoke workflow require explicit permission. An existing `accepted` branch or protection is never overwritten automatically.

GitHub requires the approving reviewer to be a person with suitable access other than the PR author. `/ase-setup` therefore asks for a `Review policy`: `reviewer` (default) requires that reviewer; `solo-owner`, available only in Lite for single-person projects, protects `accepted` with a required PR and Gate but no approving review, and the Human Owner's own merge is the approval. In both cases only the Human Owner decides the merge into `accepted` (HAG-01), and agents never merge it, even though in a personal project they may run with credentials that technically could.

## Layout

| Path | Content |
|------|---------|
| `AGENTS.md` | Global rules for every agent (both harnesses) |
| `.agents/skills/` | `ase-*` skills, the single source for both harnesses; role cards in `ase-roles/references/` |
| `.agents/agents/`, `.agents/rules/` | Antigravity-specific agents and rules |
| `.github/agents/`, `.github/instructions/` | Copilot-specific agents and instructions |
| `.github/workflows/` | CI: fast checks on `main`, binding gate on PRs to `accepted`, and an explicitly started M0 Gate smoke test |
| `project-memory/` | DCP (`dcp/`), ADRs (`adr/`) and initialized state (`state/`) |
| `scripts/` | Deterministic helpers for M0 verification, next-ID allocation, task logging and traceability; opt-in `accepted` branch protection |
| `templates/` | MVP, requirement, Wave, Feature, User Story, task and ADR templates, plus the minimal correction prompt |

`/ase-setup` configures the project's stack-specific `scripts/ci/fast.sh` and `scripts/ci/gate.sh`. The included GitHub Actions workflows call those commands. The M0 smoke test runs the Gate command on Actions but is not a PR gate. `scripts/protect-accepted.sh --apply` is opt-in and refuses to replace detected existing protection.

`python3 scripts/verify-m0.py --local` runs the approved local checks and reports local readiness only. `/ase-setup` uses its `--hosted` mode to verify GitHub branches, protection, and workflow evidence; it does not change remote settings.
