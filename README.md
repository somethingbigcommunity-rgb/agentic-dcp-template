# Agentic DCP Template

Project template for the **Agentic Software Engineering (ASE) harness**. It contains the Development Context Package (DCP), the Project Memory skeleton and the agentic system (skills, role cards, agents, rules, CI workflows) shared by GitHub Copilot and Antigravity.

> Status: v0.1 under development. Skills are added increment by increment; see the CHANGELOG of the source repository.

## Start a new project

1. Create a repository with **Use this template**.
2. Open it in VS Code and run `/ase-setup`.
3. Run `/ase-plan`, then `/ase-task` for each task and `/ase-review` for each Work Package.

## Layout

| Path | Content |
|------|---------|
| `AGENTS.md` | Global rules for every agent (both harnesses) |
| `.agents/skills/` | `ase-*` skills, the single source for both harnesses; role cards in `ase-roles/references/` |
| `.agents/agents/`, `.agents/rules/` | Antigravity-specific agents and rules |
| `.github/agents/`, `.github/instructions/` | Copilot-specific agents and instructions |
| `.github/workflows/` | CI: fast checks on `main`, binding gate on PRs to `accepted` |
| `project-memory/` | DCP (`dcp/`), ADRs (`adr/`) and state (`state/`) |
| `templates/` | Templates for waves, features, user stories, tasks, requirements, ADRs |
