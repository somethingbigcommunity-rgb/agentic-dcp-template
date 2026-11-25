# Agentic DCP Template

Project template for the **Agentic Software Engineering (ASE) harness**. It contains the Development Context Package (DCP), the Project Memory skeleton and the agentic system (skills, role cards, rules, CI workflows).

> Version: **v0.3.0**. Adds proactive remote- and milestone-aware Git proposals (`scripts/git-advisor.py` with `personal` vs `work` execution rules), WBS-style hierarchical sub-task IDs for roadmap interruptions (`T-0008.1`, `T-0008.1.1`) with the `NEXT_TASK.md` Return Stack, and on-demand daily project situation reports (`/ase-status` + `scripts/project-status.py`), on top of encapsulated `.ase/` local adoption (`--upgrade`, `--verify-layout`), the full native Antigravity + Copilot roster, `/ase-plugin`, stakeholder PDFs (`work` Sopra Steria Group vs `personal`), and `verify-external-clean.py`. See [release notes and validation limits](RELEASE-NOTES.md).

## Use it today on an existing repository (local mode)

Nothing is committed or pushed; the team's Git process is untouched.

```sh
git clone https://github.com/somethingbigcommunity-rgb/agentic-dcp-template.git ~/ase-template
python3 ~/ase-template/install.py /path/to/your/repo   # add --dry-run to preview
```

The installer copies the harness without overwriting any existing file, encapsulates ASE's operational directories inside `.ase/` (`.ase/project-memory/`, `.ase/artifacts/`, `.ase/scripts/`, `.ase/templates/`) while keeping only `.agents/`, `.github/`, and `AGENTS.md` at the root for IDE auto-discovery, and hides every installed path through `.git/info/exclude`. If the repository already has an `AGENTS.md`, it keeps it and installs the ASE rules in `.agents/AGENTS.md` instead. `--upgrade` updates unmodified template files; `--verify-layout` checks `.ase/` encapsulation and detects stray template clones; `--uninstall` removes the files you did not modify; `--versioned` skips the Git exclusion if the team adopts ASE.

Then, in VS Code (Copilot) or Antigravity:

1. Select the **ASE Lead** agent and run `/ase-adopt`: it reads the code, proposes the as-is DCP, stack and test commands, and records the baseline (M0-A) after your approval.
2. For each piece of work: `/ase-plan` (a *quick task* for a bug fix or small change, a plan for a feature), then `/ase-task`.
3. Before opening the team PR: `/ase-review` writes a review report and a ready-to-paste PR description. You commit, push and open the PR yourself.

Check that your organization allows AI assistants on that code first.

## Start a new project (remote mode)

1. Create a repository with **Use this template**.
2. Open it in VS Code and run `/ase-setup`.
3. Once the M0 checklist is complete, run `/ase-plan`, then `/ase-task` for each task and `/ase-review` for each Work Package.

New-project setup supports Lite mode with the `antigravity` or `vscode` engine. Standard/Enterprise and AI Studio are not implemented. Graphify is optional.

`/ase-setup` asks for the stack and real Fast and Gate commands; it does not install dependencies or invent passing checks. It can prepare a project locally, but M0 also requires GitHub connectivity, an existing `accepted` branch, and successful hosted checks. Branch protection is required where available. If GitHub plan or permissions prevent it, only an explicit HAG-06 approval of the procedural HAG-01 fallback recorded in the M0 checklist can substitute; this accepts that direct pushes and early merges cannot be technically blocked. Creating the initial `accepted` branch, changing GitHub settings, pushing, and starting the hosted smoke workflow require explicit permission. An existing `accepted` branch or protection is never overwritten automatically.

GitHub requires the approving reviewer to be a person with suitable access other than the PR author. `/ase-setup` therefore asks for a `Review policy`: `reviewer` (default) requires that reviewer; `solo-owner`, available only in Lite for single-person projects, uses a required PR and Gate but no approving review, and the Human Owner's own merge is the approval. In both cases only the Human Owner decides the merge into `accepted` (HAG-01), and agents never merge it, even though in a personal project they may run with credentials that technically could.

## Layout

| Path | Content |
|------|---------|
| `AGENTS.md` | Global rules for every agent (both harnesses, including `Project context`: `work` \| `personal` and external artifact rules) |
| `.agents/skills/` | `ase-*` skills (`/ase-setup`, `/ase-adopt`, `/ase-plan` with `/ase-memo` & `/ase-context` aliases, `/ase-task`, `/ase-review`, `/ase-pack`, `/ase-export`, `/ase-switch`, `/ase-status`, `/ase-roles`, `/ase-plugin`), read natively by both Copilot and Antigravity; role cards in `ase-roles/references/` |
| `.agents/agents/`, `.agents/rules/` | Antigravity agents (19, DEC-05 roster + `ase-lead` with `subagent`/`mainAgent` and native tool arrays) and glob rules |
| `.github/agents/`, `.github/instructions/` | The same agents and rules in Copilot's native format |
| `install.py` | Installer and upgrader (`--switch`, `--upgrade`, `--verify-layout`, `--show-harness`, `--hide-harness`, `--flat`, `--versioned`, `--no-git`, `--uninstall`) for existing repositories |
| `.github/workflows/` | CI: fast checks on `main`, binding gate on PRs to `accepted`, and an explicitly started M0 Gate smoke test |
| `project-memory/` (`.ase/project-memory/` when installed) | DCP (`dcp/`, including `00-project-management/project-charter.md`), ADRs (`adr/`) and initialized state (`state/`, `state/reviews/`, `state/PACK_STATE.json`) |
| `inputs/` (visible at root until `/ase-pack`) | Initial Context Inbox: drop briefs, RFPs, notes, PDFs, or schemas here so `/ase-adopt`, `/ase-setup`, and `/ase-plan` inspect them **first** (3-Tier Discovery Order) |
| `deliverables/` (visible at root) | Pre-created stakeholder deliverable directories (`01-discovery/`, `02-planning/`, `03-architecture/`, `04-verification/`, `05-release-and-handover/`, plus `INDEX.md` generated by `/ase-pack`) |
| `specs/` (`.ase/specs/` when installed) | Internal JSON input specs for `build-stakeholder-pdf.py` |
| `scripts/` (`.ase/scripts/` when installed) | Deterministic helpers: `check-prereq.py` (Step 0 + `--post` reactive chaining), `sync-inputs.py` (incremental `inputs/` SHA-256 + Graphify `--query-graph`), `switch-release.py`, `verify-m0.py`, `verify-accepted.sh`, `next-id.py` (including `--under` for WBS `T-NNNN.1`), `append-task-log.py`, `build-traceability.py`, `verify-external-clean.py`, `sync-plugin.py`, `build-stakeholder-pdf.py`, `git-advisor.py`, `project-status.py`, `pack-workspace.py`, `export-handover.py`, `protect-accepted.sh` |
| `templates/` (`.ase/templates/` when installed) | MVP, requirement, Wave, Feature, User Story, task, ADR, and `stakeholder-pdf-template.json` templates, plus the minimal correction prompt |

`/ase-setup` configures the project's stack-specific `scripts/ci/fast.sh` and `scripts/ci/gate.sh`. The included GitHub Actions workflows call those commands. The M0 smoke test runs the Gate command on Actions but is not a PR gate. `scripts/protect-accepted.sh --apply` is opt-in and refuses to replace detected existing protection.

`python3 scripts/verify-m0.py --local` runs the approved local checks and reports local readiness only. `/ase-setup` uses its `--hosted` mode to verify GitHub branches, protection (or the explicitly approved procedural fallback), and workflow evidence; it does not change remote settings. Under the fallback, `bash scripts/verify-accepted.sh <PR-number>` checks that the current remote `accepted` tip is the merge commit of that merged `main → accepted` PR.

The template intentionally has no project-specific `scripts/ci/fast.sh` or `scripts/ci/gate.sh`: `/ase-setup` creates them after stack and command approval. A workflow run on the unconfigured template fails at that prerequisite; it is not evidence that project M0 or the Gate passed.
The template intentionally has no project-specific `scripts/ci/fast.sh` or `scripts/ci/gate.sh`: `/ase-setup` creates them after stack and command approval. On `somethingbigcommunity-rgb/agentic-dcp-template` itself, `fast.yml` runs a template syntax self-check (`py_compile` + `bash -n`); in any repository created from the template, a workflow run before `/ase-setup` fails at the `test -f scripts/ci/fast.sh` prerequisite so unconfigured projects never report a false M0 pass.
