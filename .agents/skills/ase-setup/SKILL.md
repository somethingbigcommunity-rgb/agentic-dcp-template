---
name: ase-setup
description: Set up a new ASE project in Lite mode with the antigravity or vscode engine, approved stack-specific CI, GitHub branches, and an evidence-based M0 checklist. Use when asked to run /ase-setup, bootstrap a new project, or resume its P0 setup.
---

# `/ase-setup`

> If the repository's root `AGENTS.md` belongs to the team and is not the ASE rules file, the installer placed the ASE rules in `.agents/AGENTS.md`; every reference to `AGENTS.md` in this skill means that file.

Prepare one **new** project from this template. This version supports `Lite` mode with `antigravity` or `vscode` as the engine. Existing-project adoption is handled by `/ase-adopt`; Standard, Enterprise, and AI Studio are not implemented. Do not silently substitute a supported choice. Graphify is optional.

Follow `AGENTS.md`. Never merge into, reset, force-push, delete, or overwrite `accepted`. Do not create a remote repository, push, create a remote branch, change GitHub settings, or start a hosted workflow without explicit Human Owner authorization for those actions. Do not ask for or record credentials.

## 1. Check scope and collect the inputs

1. Read `AGENTS.md`, `project-memory/state/PROJECT_STATE.md`, `M0_CHECKLIST.md`, `NEXT_TASK.md`, existing setup tasks, and relevant project files. Use the project root as the only workspace. Do not change files outside it.
2. If M0 is already `PASS` and no change was requested, report the existing result read-only; do not repeat bootstrap. A later configuration change needs a new task and the normal PR to `accepted`.
3. If this is an existing application or a repository whose Git process belongs to a team, stop before changes and use `/ase-adopt` (`local` Git mode). If the requested mode or engine is unsupported, stop and explain that the option is not implemented. Do not treat a repository with an existing application as a new template project.
4. Ask the Human Owner for any missing inputs: confirmation that this is a new project, `Lite` and `antigravity` (or `vscode`), `Project context` (`work` for corporate/Sopra Steria Group deliverables or `personal` for personal/open-source projects), a concise stack description, actual Fast and Gate commands suitable for both the local environment and GitHub's Ubuntu runner, the Graphify choice, and the `Review policy`: `reviewer` if an eligible human other than the PR author can review future PRs, or `solo-owner` (Lite only) if the Human Owner works alone and will merge personally as the HAG-01 approval. Do not invent the stack, commands, reviewer, product scope, or an approval.
5. Show the proposed script contents and any provisioning or dependency changes before executing them. Obtain explicit approval of the commands. Do not install dependencies or modify workflows unless separately approved. Missing tools, unavailable hosted capabilities, and a missing eligible reviewer are blockers, not passing checks.
6. Require a clean worktree before switching branches. Inspect `main`, any local `accepted`, and `origin` if present; for a reachable origin inspect its `main` and `accepted` refs. A failed remote lookup does not prove a branch is absent. If the repository or a branch is unexpectedly dirty, divergent, or ambiguous, stop and ask; never discard work.

## 2. Open or resume one setup task

1. If an ID was supplied, resume only the matching open setup task. Otherwise find the open setup task in `project-memory/dcp/04-implementation/tasks/`. If more than one exists, ask which to resume. Never reuse a `DONE` or `BLOCKED` task or reset its correction count; a restart after `BLOCKED` requires an explicit human decision.
2. If there is no open setup task, require `main`, allocate an ID with `python3 scripts/next-id.py --type task`, and create `task/<ID>` from `main`. Create `<ID>-setup-<slug>.md` from `templates/task-template.md` with an empty parent, `risk: high`, `engine: antigravity` (or `vscode`), `status: IN_PROGRESS`, and `correction_cycles: 0`. Its criteria cover the approved configuration, local and hosted evidence, the protected or explicitly approved procedural `accepted` gate, the M0 checklist, and the task log.
3. Resume the existing task branch without overwriting work. Record the input, proposed file changes, approvals, and outstanding decisions in its execution report. Keep `NEXT_TASK.md` unassigned; this is a bounded setup task, not a planned product task.
4. Load the Product & Project Manager and Solution Architect role cards, plus the Security Reviewer for the GitHub protection and trust-boundary changes. Do not activate every role.

## 3. Prepare the local project

1. After approval, fill the Project configuration table in `AGENTS.md`: `Lite`, `antigravity` (or `vscode`), `main`, `accepted`, the approved `Review policy`, the approved stack, and the existing `scripts/ci/fast.sh` and `scripts/ci/gate.sh` paths. Use a single Markdown table cell for each value.
2. Preserve the existing Project Memory skeleton and any project data. Do not replace an existing configuration, CI script, or Project Memory file without inspecting it and obtaining explicit approval for the specific change. Create only missing directories and the approved `scripts/ci/fast.sh` and `scripts/ci/gate.sh`; make both executable.
3. Each script must contain real, approved checks, fail when a required tool or check fails, and be usable on the GitHub Actions runner. Use `set -euo pipefail` and have Gate include the relevant Fast checks. Never use an unconditional success, ignore a failure, or pretend that zero tests means tests passed. If an application does not exist yet, record application tests as not applicable, not passed.
4. Record the local choices and their actual results in `M0_CHECKLIST.md`. Keep the `M0` value in `PROJECT_STATE.md` as `PENDING`; local preparation alone is not M0.
5. Run `python3 scripts/verify-m0.py --local` from the project root. It runs both approved scripts; review and report its output. A nonzero result is a failed verification, not a partial pass.
6. For a failed verification, increment `correction_cycles` once for the complete run, record the failure, and make only a bounded correction. At three failed cycles set `BLOCKED`, record the Change Impact Analysis, append exactly one row using `scripts/append-task-log.py`, and stop. A human decision or an unavailable prerequisite is a wait, not permission to bypass checks.

If GitHub is not configured, inaccessible, or not authorized, keep the setup task `IN_REVIEW`, commit the reviewable local work on `task/<ID>`, report exactly what is missing, and stop. Do not append a terminal log row or claim M0 is complete. Resume the same task when the prerequisite is available.

## 4. Integrate and establish the initial baseline

1. After local checks pass, set the setup task `IN_REVIEW`, inspect the complete diff, and commit with `T-NNNN:`. Integrate the task into `main` using the project's authorized merge procedure; never merge into `accepted`.
2. Verify that `origin` identifies the intended GitHub repository, that its default branch is `main`, and that the Human Owner authorizes the required push. Push `main` without force and wait for a successful **Fast** workflow on the exact pushed commit. Save that full SHA as `SETUP_SHA`; local Fast results are not hosted CI.
3. Inspect both local and remote `accepted` again. Only if **both are absent**, and the Human Owner explicitly authorizes creating the initial branch, create the remote ref atomically from `SETUP_SHA`:

   ```sh
   gh api --hostname "$HOST" --method POST "repos/$REPO/git/refs" \
     -f ref=refs/heads/accepted -f sha="$SETUP_SHA"
   ```

   Obtain `HOST` and `REPO` from the GitHub repository resolved from `origin`. A failed lookup or a failed POST is a blocker; never retry with force or update an existing ref. Fetch the new remote ref and create the local `accepted` branch only if it is still absent. This is initial branch creation, not a merge.
4. If `accepted` already exists locally or remotely, preserve its exact tip and existing protection. Fetch its remote-tracking ref if needed, and create a local tracking branch only if no local branch exists. If it does not contain the approved setup configuration, the Human Owner must arrange its acceptance through a properly approved `main → accepted` PR and HAG-01; do not invent a WP or merge the PR. Stop and resume only after the human has completed that path and `main` contains the resulting accepted commit. With authorization, publish the synchronized `main`, verify its Fast run, and use that new commit as `SETUP_SHA`. Existing-repository adoption (P0-A) uses `/ase-adopt`.
5. Inspect the remote `accepted` branch and protection. If the branch is unprotected, present the exact settings in `scripts/protect-accepted.sh`, obtain explicit authorization, and run `bash scripts/protect-accepted.sh --apply`. The helper refuses detected existing protection. If protection applies and already satisfies the checklist, retain it without invoking the helper. If GitHub explicitly reports that protection is unavailable because of plan or permissions, explain that the fallback cannot prevent direct pushes or an early merge and ask the Human Owner to approve or reject it under HAG-06. On approval, record `HAG-06 procedural accepted-gate fallback: APPROVED — YYYY-MM-DD` in `M0_CHECKLIST.md` and require the PR/Gate/owner-merge/post-merge-audit procedure in HAG-01. If protection is insufficient or its status cannot be inspected, stop and ask the Human Owner; do not silently select the fallback or replace existing rules.

GitHub required reviews cannot be supplied by the PR author. With `Review policy` `reviewer`, run `--apply`; enforcing the review then requires a distinct eligible reviewer. With `solo-owner`, run `--apply --solo-owner`: the PR and `gate / gate` stay required with no approving review, and the Human Owner's own merge is the HAG-01 approval. The procedural fallback does not waive the configured review requirement or HAG-01. Never enable an administrative bypass, weaken a policy without HAG-06, or waive HAG-01 to make setup pass.

## 5. Verify hosted evidence and finish

1. With explicit authorization, run `gh workflow run m0-smoke.yml --repo "$HOST/$REPO" --ref main`, then wait for its successful `workflow_dispatch` run on `SETUP_SHA`. This workflow executes the Gate command on Actions; it is **not** the binding PR gate. If `main` moved, stop and re-establish the correct setup evidence instead of using a stale run.
2. On clean `main`, run:

   ```sh
   python3 scripts/verify-m0.py --hosted --tested-commit "$SETUP_SHA" --task T-NNNN
   ```

   Replace the task ID with the actual setup task. This reruns both local scripts and verifies matching local/remote refs, `accepted` ancestry and branch protection (or the recorded HAG-06 procedural fallback), a successful hosted Fast run for the current `main`, and a successful hosted Gate smoke for `SETUP_SHA`. It allows only setup-task and descriptive M0-state changes after the tested commit. If any check fails or is unavailable, report it and keep M0 `PENDING`.
3. Verify the remaining checklist items with the Human Owner, especially Copilot availability, the review policy (eligible reviewer or confirmed solo-owner), and the Graphify choice. If Graphify is enabled, verify its actual setup; if disabled, record `NOT APPLICABLE`. Record exact commands, dates, SHA, Fast and smoke run URLs, authorization, and any initial-branch or PR evidence in the checklist. Never claim that a real PR gate or Antigravity was tested by the M0 smoke.
4. Use the same task branch to commit the evidence with the task still `IN_REVIEW` and M0 still `PENDING`; integrate it into `main`, push with authorization, and wait for Fast on that new `main` commit. Rerun the hosted verifier with the original `SETUP_SHA`. Do not proceed if it fails.
5. Only after all required evidence is available, set `M0 | PASS` in `PROJECT_STATE.md`, mark the setup task `DONE`, and append exactly one `DONE` row through `scripts/append-task-log.py`. Commit these descriptive closure updates on the same task branch, integrate them into `main`, push with authorization, and confirm the resulting Fast run. Run the hosted verifier again; it checks the latest Fast run and retains the smoke evidence for `SETUP_SHA`. Report M0 as passed only after these checks succeed.
6. If a hosted check fails after the terminal log entry was committed, report the failed current CI and the inconsistent M0 status immediately. Do not rewrite or duplicate the append-only row or claim success; ask the Human Owner to assign a corrective task to restore accurate state and investigate the regression.
7. Report the task ID, approved configuration, M0 checklist, local results, GitHub run URLs, `accepted` status, optional components, and any remaining real-PR or release validation. If the approved stack has specialized domain conventions or multi-tool guardrails that could be reused across similar projects, proactively offer `/ase-plugin` (`plugins/<slug>/`) as a follow-up option. Stop; do not invoke `/ase-plan` or implement product work.
