# Iteration Protocol

Use this protocol for exactly one assigned task. `AGENTS.md` and the task file remain authoritative for project-specific constraints and acceptance criteria.

## 1. Input

Read `AGENTS.md`, `project-memory/state/NEXT_TASK.md`, the assigned task file, relevant approved DCP sections and ADRs, and the current project state. An explicit task ID from the human takes precedence over `NEXT_TASK.md`. Do not start a task that is not assigned or whose required metadata and verifiable criteria are missing.

## 2. Pre-implementation

Inspect the relevant code, tests, and conventions. Identify affected components, dependencies, and architecture conflicts. Stop for a required Human Approval Gate or a conflict with an approved ADR; report the decision needed instead of proceeding.

## 3. Planning

Record a concise implementation plan in the task execution report:

- affected files or components;
- implementation steps;
- dependencies and risks;
- checks that will demonstrate each acceptance criterion.

Keep the plan within the task's goal and constraints.

## 4. Implementation

Implement only the assigned task. Reuse project patterns, preserve compatibility, and do not weaken acceptance criteria or make unrelated changes.

## 5. Verification

Run the focused checks for the task and the project's declared fast check when applicable. Map every acceptance criterion to a command, observation, or other reproducible evidence. Report unavailable commands explicitly; they are not passing checks.

Treat one complete verification run as one failure, even if several commands in it fail. Increment `correction_cycles` once for that failure. For cycles 1 and 2, diagnose the cause, make a bounded correction, and rerun the failed check plus relevant regressions. Use `templates/correction-prompt.md` when another correction prompt is needed. After the third failed verification, set the task to `BLOCKED`, record the impact analysis, append the terminal log entry, and stop without a fourth correction.

## 6. Reporting

Record in the task's execution report:

- files and behavior changed;
- checks run, results, and evidence for each criterion;
- known issues;
- architecture deviations, or `None`;
- completion status (`DONE`, `BLOCKED`, or `IN_REVIEW`) and any outstanding decision.

For `BLOCKED`, also record the root cause or that it is unconfirmed, affected artifacts, proposed changes, regression checks, and the human decision required.

## 7. State update

Set descriptive task status and counter in the task file. After reviewable implementation and passing focused checks, use `IN_REVIEW`. If review or CI identifies a failure, return to `IN_PROGRESS` and count the failed verification as a correction cycle. A task is `DONE` only after the preliminary check, integration into `main`, and green CI on `main`. For a local-only project without CI automation, run the declared Fast CI command on `main` and record it explicitly as local gate evidence, not hosted CI. If the applicable gate is unavailable or fails, leave the task `IN_REVIEW`; never merge into `accepted`.

For terminal status `DONE` or `BLOCKED`, append exactly one row to `project-memory/state/TASK_LOG.md` using `scripts/append-task-log.py`. Do not rewrite the log or edit generated `TRACEABILITY.md`. Update other descriptive state only when the task provides sufficient evidence.

## 8. Stop

Stop after one task reaches `DONE`, `BLOCKED`, or an explicitly reported `IN_REVIEW` wait. Do not select or implement a future task in the same invocation.
