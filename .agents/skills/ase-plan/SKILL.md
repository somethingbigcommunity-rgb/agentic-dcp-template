---
name: ase-plan
description: Turn an approved one-page project idea into a minimal Lite MVP specification and traceable backlog of Waves, Features, User Stories, requirements, and tasks. Use when asked to run /ase-plan, create a project plan, or re-plan existing ASE work.
---

# `/ase-plan`

> If the repository's root `AGENTS.md` belongs to the team and is not the ASE rules file, the installer placed the ASE rules in `.agents/AGENTS.md`; every reference to `AGENTS.md` in this skill means that file. When `.ase/` encapsulation is present, `project-memory/`, `artifacts/`, `scripts/`, and `templates/` resolve under `.ase/`. Always use first-person singular (`"I"`, addressing the Human Owner as `"you"`, never `"we"`).

Create or update one Lite planning increment. Follow `AGENTS.md`, the Project Memory operating rules, and the DCP templates. Design-decision documents may not be copied into a project repository; if a referenced source decision is unavailable, do not claim to have read it or infer additional rules from it. Do not execute implementation tasks.

## 1. Check project and input

1. Read `AGENTS.md`, `project-memory/state/PROJECT_STATE.md`, `IMPLEMENTATION_STATUS.md`, `NEXT_TASK.md`, the relevant DCP requirements and implementation files, and applicable ADRs.
2. Proceed only when `/ase-setup` has completed, `PROJECT_STATE.md` records `M0 | PASS`, the M0 checklist has the required evidence, and the project mode is Lite. If setup is incomplete, evidence is missing, or the mode is not Lite, stop and explain the prerequisite.
3. Use the user's supplied idea or planning change. If none is provided, ask for it; do not invent product scope.
4. Load only relevant role cards from `.agents/skills/ase-roles/SKILL.md`. Consult the Product & Project Manager and Solution Architect cards; involve other roles only when the scope or risk requires them.

## 2. Open the planning task

1. If the user supplies a planning-task ID, resume that task only if its status is `IN_REVIEW` and it has pending approval or post-approval work; switch to its `task/<ID>` branch without discarding changes. Otherwise, when exactly one planning task is `IN_REVIEW`, resume it and its branch. If there are multiple pending planning tasks and no ID was supplied, ask which to resume. Do not create a duplicate task for an open plan.
2. If there is no planning task to resume, allocate an ID with `python3 scripts/next-id.py --type task`, then create or switch to `task/<ID>` from `main` without discarding existing work.
3. Create `project-memory/dcp/04-implementation/tasks/<ID>-plan-<slug>.md` from `templates/task-template.md`. Leave `parent` empty: a planning task is not an implementation task in the backlog, and the traceability matrix only links implementation tasks under a User Story or Work Package. Record the Wave or Feature being planned in the task's notes and report instead. Use the configured engine, `risk: medium`, `status: IN_PROGRESS`, and `correction_cycles: 0`.
4. Give this planning task criteria covering the approved plan, stable IDs, updated state files, and validation of all generated references. Record the request and a concise proposal in its execution report.
5. Do not set `NEXT_TASK.md` to the planning task; it is a separate, bounded planning operation.

## 3. Prepare the Lite plan proposal

1. Read the relevant DCP sections and current backlog before proposing changes. For a new project, prepare:
   - `project-memory/dcp/01-requirements/mvp-specification.md`;
   - `functional-requirements.md` entries using `REQ-NNN`;
   - one or more Wave specifications using `W-NN`;
   - Feature specifications (`F-NNN`, or `WP-NNN` for non-functional Work Packages);
   - User Story files (`US-NNN`);
   - execution-ready task files (`T-NNNN`) with explicit risk and observable criteria.
2. Use the document templates in `templates/`. Keep Lite planning proportional: plan only the approved MVP and avoid detailed artifacts that will be stale before they are needed.
3. Map each requirement to at least one User Story, each User Story to a Feature, and each Feature to a Wave. Each implementation task has a parent User Story or Work Package and at least one verifiable criterion.
4. Set task risk to `low`, `medium`, or `high` based on impact. Do not downgrade risk to avoid a gate. Identify active HAGs and unresolved architecture decisions; stop and ask the Human Owner where approval is required.
5. Before any normative DCP or backlog file is written or changed, show the proposed MVP scope, requirements, hierarchy, IDs, risks, criteria, and file changes to the Human Owner and ask for explicit approval. The command invocation alone is not approval of generated scope.
6. For an approved decision governed by an HAG, create an `ADR-NNN` record from `templates/adr-template.md` after the Human Owner approves it. Do not record an unapproved proposal as an accepted ADR.

If approval is pending, set the planning task to `IN_REVIEW`, record the proposal on `task/<ID>` and wait. Do not modify the normative backlog or `NEXT_TASK.md`. The Human Owner can approve or revise the proposal in the current conversation, or resume it with `/ase-plan <T-NNNN>` in a later conversation. If the Human Owner rejects the proposal, set the planning task to `BLOCKED`, record the decision and append exactly one `BLOCKED` row through `scripts/append-task-log.py` on the task branch, then stop without merging.

## 4. Allocate IDs and apply the approved plan

After explicit approval:

1. Allocate every new ID with `scripts/next-id.py` (`requirement`, `wave`, `feature`, `work-package`, `user-story`, `task`, or `adr`). Never reuse a gap or renumber an existing item. Re-check the next ID immediately before creating each artifact.
2. Write approved requirements in `functional-requirements.md`; create User Stories under `project-memory/dcp/01-requirements/user-stories/`; create Wave, Feature and Task files in their corresponding `project-memory/dcp/04-implementation/` folders.
3. For re-planning, preserve each item's ID and filename. Update `parent` and affected links when moving an item between Waves. Do not delete, silently rewrite, or re-number existing approved scope; present material changes for approval first.
4. Update `mvp-specification.md` with the approved scope and approval date. It links to requirements and stories instead of duplicating them.
5. Update `IMPLEMENTATION_STATUS.md` with the approved MVP, planned Waves/Features, and task status. Set `NEXT_TASK.md` to the first approved, ready `TODO` implementation task; do not replace an existing active assignment without human approval. If no task is ready, state why and leave it unassigned.

## 5. Validate and close the planning task

1. Verify IDs are unique, each parent/reference resolves, all criteria are observable, risk and engine values are valid, and `NEXT_TASK.md` points to an existing `TODO` implementation task (or clearly states why none is assigned).
2. Record changed files, approval evidence, validation results, and remaining issues in the planning task's execution report.
3. Set the planning task to `IN_REVIEW`; inspect the full diff, run the declared preliminary checks, commit with a `T-NNNN:` message, and follow the repository's authorized merge procedure into `main`. Never merge into `accepted`.
4. Run the configured CI on `main`, or the declared Fast CI command as local gate evidence when hosted CI is not configured. If a check fails, count one correction cycle, make only a bounded plan correction, and rerun the relevant checks. At three failed cycles, set `BLOCKED`, record the impact, and stop without merging the blocked branch.
5. Set the planning task to `DONE` only after the approved artifacts and state updates pass validation and the applicable gate passes on `main`. For `DONE` or `BLOCKED`, append exactly one task-log entry using `scripts/append-task-log.py`; never hand-edit the log.
6. Stop after reporting the plan and the next assigned implementation task, and proactively offer two optional follow-ups when relevant:
   - **Optional Stakeholder PDF (`project-plan` / `architecture-dossier`):** Offer to generate a stakeholder-level executive PDF (`build-stakeholder-pdf.py` from `templates/stakeholder-pdf-template.json`, saving the spec in `artifacts/specs/` and the PDF in `artifacts/02-planning/` or `artifacts/03-architecture/`, using `context_profile: "work"` with Sopra Steria Group palette/metadata or `"personal"` with a project-suited palette, verified clean via `verify-external-clean.py`).
   - **Proactive Reusable Domain Plugin (`/ase-plugin`):** If 2 or more planned Features/Waves share domain-specific guardrails or deterministic validation scripts that are reusable across similar projects, propose packaging them into an ASE-external plugin under `plugins/<slug>/` (HAG-02).
   - **Git Milestone Proposal (`plan`):** Run `python3 scripts/git-advisor.py --milestone plan --task-id <ID>` (or `.ase/scripts/git-advisor.py`) and include the milestone Git proposal based on remote connectivity (`no-remote` vs `github-remote`), `.ase-install.json` versioned state, and `Project context` (`personal`: offer to execute upon confirmation; `work`: provide commands for manual execution only).
   Do not run `/ase-task`.

## Identifier helper

Run from the project root:

```sh
python3 scripts/next-id.py --type requirement
python3 scripts/next-id.py --type wave
python3 scripts/next-id.py --type feature
python3 scripts/next-id.py --type work-package
python3 scripts/next-id.py --type user-story
python3 scripts/next-id.py --type task
python3 scripts/next-id.py --type task --under T-0008      # WBS sub-task T-0008.1, T-0008.2
python3 scripts/next-id.py --type task --under T-0008.1    # Nested WBS sub-task T-0008.1.1
python3 scripts/next-id.py --type adr
```

The helper scans only canonical artifact locations and the append-only task log. If it fails, surface the error and do not guess an ID.

## Roadmap Interruptions (`WBS T-NNNN.1` & Return Stack) and Pivots

When mid-project findings, urgent defects, or pivots interrupt the planned roadmap, use one of these two structured patterns (after Human Owner approval):

1. **Task Interruption & Return Stack (`PAUSED` in `NEXT_TASK.md` — covers both Inner Micro-Sequences and Urgent Hotfixes):**
   - Mechanically, an **Inner Micro-Sequence (Detour)** and an **Urgent Hotfix** use the **exact same pause-and-resume mechanism**: set the interrupted task (e.g. `T-0008`) to `status: PAUSED`, place `T-0008` on the `Return Stack (PAUSED tasks to resume)` in `state/NEXT_TASK.md`, queue the 1..N interrupting tasks in `NEXT_TASK.md`, and automatically pop `T-0008` from the Return Stack when the interruption finishes.
   - Choose the ID and `parent` based only on **whether the interruption belongs to the paused task's scope**:
     - **In-scope detour or fix (`WBS T-0008.1`, `T-0008.2`, `T-0008.1.1`):** When the inserted steps or bug fix are needed to complete `T-0008` itself (or its User Story/Feature), allocate WBS dotted IDs with `python3 scripts/next-id.py --type task --under T-0008` (`parent: T-0008`, optionally setting `external: BUG-NNN`) so it is immediately clear those steps were inserted later inside `T-0008`.
     - **Out-of-scope urgent hotfix (`BUG-NNN` + `T-NNNN`):** Only when an urgent defect belongs to a *different, unrelated* Feature/Wave (where rolling it under `T-0008` would pollute `T-0008`'s Feature traceability), allocate a top-level task `T-NNNN` with `parent` set to the affected Feature/Story (and `external: BUG-NNN`) while still pausing `T-0008` on the Return Stack.
2. **Roadmap Pivot (`Pivot / Re-scope`):**
   - Never delete or renumber existing IDs. Mark obsolete tasks/stories/features as `status: SUPERSEDED` (adding `superseded_by: <ID or ADR-NNN>`) or `status: DEFERRED` (adding `deferred_to: <W-NN>`), log terminal transitions in `state/TASK_LOG.md`, record an `ADR-NNN` if architecture changed (`HAG-02`), and insert the new replacement items.

## Local Git mode

When `AGENTS.md` sets `Git mode` to `local`:

- The prerequisite is `M0-A | PASS` in `PROJECT_STATE.md` (from `/ase-adopt`) instead of `M0 | PASS`.
- Do not create branches, commit or merge. Apply the approved plan in the working tree; the planning task becomes `DONE` after the validation in section 5 passes and the Human Owner confirms the result.
- **Quick task.** For a single bounded change (bug fix, small feature, investigation) the Human Owner may ask for one task instead of a Wave plan. Create one task from `templates/task-template.md` with an empty `parent` (or the related `F-NNN`/`WP-NNN` if one exists), observable criteria and a risk class; show it and assign it in `NEXT_TASK.md` after approval. No MVP specification, Wave or User Story is required. A parentless task is reported as a traceability warning, which is accepted in Lite.
