---
name: ase-task
description: Execute exactly one assigned ASE task with the Iteration Protocol, verification, correction-cycle limit, state updates, and task log entry. Use when asked to run /ase-task or execute the next assigned task.
---

# `/ase-task`

> If the repository's root `AGENTS.md` belongs to the team and is not the ASE rules file, the installer placed the ASE rules in `.agents/AGENTS.md`; every reference to `AGENTS.md` in this skill means that file. When `.ase/` encapsulation is present, `project-memory/`, `artifacts/`, `scripts/`, and `templates/` resolve under `.ase/`. Always speak and draft commit/PR/handover messages in first-person singular (`"I"` / `"Io"`, never `"we"` / `"noi"`).

Execute one assigned task and stop. Follow `AGENTS.md` and the Iteration Protocol in `project-memory/dcp/04-implementation/iteration-protocol.md`. Do not improvise if a required project command, script, or skill is missing.

## 1. Select and validate the task

1. Read `AGENTS.md`, `project-memory/state/NEXT_TASK.md`, and the referenced task file. An explicit task ID supplied by the human takes precedence over `NEXT_TASK.md`.
2. Execute no more than one task per invocation. If no task is assigned, the task file is missing, required fields or verifiable criteria are absent, or its status is `DONE` or `BLOCKED`, make no implementation changes; explain the blocker. An `IN_REVIEW` task may be resumed only to address identified review or CI findings; if none are pending, report that it is awaiting the gate and stop.
3. Check applicable HAGs, dependencies, DCP sections, and ADRs before proceeding. Stop for human approval where required.
4. If the task is already on `task/<ID>`, continue there. Otherwise create or switch to `task/<ID>` from the current `main`. Do not overwrite or discard existing work.
5. Set the task status to `IN_PROGRESS`. Load only relevant cards from `.agents/skills/ase-roles/SKILL.md`; do not activate every role.

## 2. Inspect and plan

Follow Iteration Protocol steps 1–3: inspect relevant project context and code, identify affected files and architecture conflicts, then record a concise implementation and verification plan in the task's execution report. If the task conflicts with approved architecture, stop and report it.

## 3. Implement and verify

Implement only the assigned task. Map every acceptance criterion to evidence. Run the project's declared focused checks and `scripts/ci/fast.sh` when available and applicable. Report missing commands explicitly; never treat a skipped or unavailable check as passing.

When verification fails:

1. Treat the complete verification run as one failed cycle, even if several commands in that run fail.
2. Increment `correction_cycles` once and record the command, expected and actual results in the task report.
3. If the count is 1 or 2, diagnose the cause and use `templates/correction-prompt.md` to make a bounded correction, then rerun the failed check and relevant regressions.
4. At count 3, do not attempt another correction. Set `BLOCKED`, record the Change Impact Analysis (root cause, affected artifacts, proposed changes, regression checks, and human decision needed), append one log entry using the script below, and stop.

Do not reset the cycle count during a task run. A later human-authorized restart must be explicit in the task history.

If a required specialist review cannot be obtained, record it as `UNAVAILABLE`, not as a successful review. A documented checklist by the implementing agent is useful evidence but is not independent review; record the remaining limitations and keep the task `IN_REVIEW` until the Human Owner decides whether the project's acceptance criteria allow closure. Do not waive an active gate without its required approval.

## 4. Review and close

After all criteria pass:

1. Record changed files, verification commands/results, evidence, known issues, and architecture deviations in the task report.
2. Set status to `IN_REVIEW` and inspect the complete diff. For any modified or created external-facing files (application code, `plugins/**`, external `docs/**`, or `*.pdf` files — everything outside `project-memory/`, `.agents/`, `.github/`, `templates/`, `scripts/`), run `python3 scripts/verify-external-clean.py <external-paths>` and record its `PASS` output in the task report. If review, `verify-external-clean.py`, or CI finds a problem, return it to `IN_PROGRESS`, count one failed verification cycle, and resolve findings within the remaining correction-cycle budget.
3. Commit task changes with a message starting `T-NNNN:`. Then run `python3 scripts/build-traceability.py --mode <project-mode>` and review its warnings/errors. If it updates `TRACEABILITY.md`, commit that generated file with the same task ID. This is a generated state artifact; never edit it by hand.
4. Follow the repository's preliminary check and merge procedure for `task/<ID>` into `main`; never merge into `accepted`.
5. Confirm the configured CI on `main` is green. If the project is local-only and has no CI automation, run its declared Fast CI command on `main` and record the result explicitly as local gate evidence, not hosted CI. Only after the applicable gate passes set status to `DONE`. If review, merge, or the applicable gate is pending, unavailable, or failing, leave the task `IN_REVIEW` or return it to `IN_PROGRESS` for a failed check; do not log it as closed.
6. For a terminal `DONE` or `BLOCKED` task, append exactly one row to `project-memory/state/TASK_LOG.md` with the helper script. Do not hand-edit or rewrite the log:

   ```sh
   python3 scripts/append-task-log.py \
     --log project-memory/state/TASK_LOG.md \
     --date YYYY-MM-DD \
     --task T-NNNN \
     --parent US-NNN \
     --engine antigravity \
     --outcome DONE \
     --cycles 0 \
     --note "Short outcome"
   ```

   Use an empty `--parent` if the task has no parent. Use the actual project engine (`antigravity` or `vscode`), date, final cycle count, and a concise note. If the helper fails, surface the error and do not claim the log was updated.

7. Update `NEXT_TASK.md` and other descriptive state only when the task provides enough evidence to do so. When completing an inner WBS sequence task (`T-NNNN.1`, `T-NNNN.2`, `T-NNNN.1.1`), advance `NEXT_TASK.md` to the next task in `Queued next in inner sequence`; when the inner sequence is empty, pop the `Return Stack (PAUSED tasks to resume)` in `NEXT_TASK.md` and restore the paused parent task (`T-NNNN`) back to `IN_PROGRESS` (or `TODO`). Do not hand-edit `TRACEABILITY.md`; rebuild it with `scripts/build-traceability.py`.
8. Report status, files, checks and results, log entry, commit, and any blocker. Stop; do not begin another task.

## Local Git mode

When `AGENTS.md` sets `Git mode` to `local`, these rules replace the branch, commit, merge and CI steps above:

- Work in the current working tree and branch. Do not create or switch branches, commit, push, or open PRs. Require the Human Owner to confirm before starting if the worktree already has unrelated changes, and never discard them.
- Run the declared `Fast CI command` (not `scripts/ci/fast.sh`) and the focused checks for the change. If it is `none`, record that no automated check exists; do not claim one passed.
- After the criteria pass, run `build-traceability.py --mode lite`, set the task `IN_REVIEW`, and show the Human Owner `git status --short`, a summary of `git diff`, a suggested commit message written in first-person singular (`"I"`, never `"we"`) without ASE IDs in `work`/unversioned mode, and the output of `python3 scripts/git-advisor.py --milestone task --task-id <ID>` (or `.ase/scripts/git-advisor.py`). Place any reconciliation or verification outputs in `artifacts/04-verification/` and verify them with `verify-external-clean.py`.
- Enforce the `Project context` execution policy from `git-advisor.py`:
  - **`Project context: personal`**: Offer to execute the proposed `git commit` (and `git push` if a remote is connected) directly for the Human Owner once the diff is accepted (`HAG-01`).
  - **`Project context: work`**: Present the proposed `git commit` / `git push` commands for the Human Owner to run manually, and **never** execute `git commit`, `git push`, branch, or remote commands yourself.
- Set the task `DONE` and append the task-log row only after the Human Owner states that the diff is accepted (HAG-01 in local mode). If the human rejects it, count one failed cycle and correct within the budget.
