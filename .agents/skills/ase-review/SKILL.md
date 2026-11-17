---
name: ase-review
description: Review a completed ASE Work Package, verify local evidence and traceability, then open its main-to-accepted pull request. Use when asked to run /ase-review or prepare a Work Package for acceptance.
---

# `/ase-review`

> If the repository's root `AGENTS.md` belongs to the team and is not the ASE rules file, the installer placed the ASE rules in `.agents/AGENTS.md`; every reference to `AGENTS.md` in this skill means that file.

Review one completed Work Package and open a Pull Request from `main` to `accepted`. Follow `AGENTS.md`, DEC-10, DEC-11, and the project's configured CI commands. This skill never merges into `accepted`.

## 1. Validate the review target

1. Read `AGENTS.md`, `project-memory/state/PROJECT_STATE.md`, `IMPLEMENTATION_STATUS.md`, `NEXT_TASK.md`, the target Feature or Work Package, its linked User Stories, requirements, tasks, relevant ADRs, and the Code Reviewer role card. Load QA Engineer or Security Reviewer only when risk or impact requires them.
2. Require exactly one explicit target ID (`F-NNN` or `WP-NNN`) that exists in the canonical Feature directory. Stop if its scope cannot be tied to a single Work Package.
3. Require the current branch to be `main`, a clean worktree, and both `main` and `accepted` to exist locally and on `origin`. Confirm local and remote branch tips match; stop if synchronization is needed. Do not fetch, push, switch branches, or discard work.
4. Require the target's implementation tasks to be `DONE`; stop if a linked task is `TODO`, `IN_PROGRESS`, `IN_REVIEW`, or `BLOCKED`.
5. Run `git merge-base --is-ancestor accepted main`; stop if the branches diverged. Confirm `git rev-list --count accepted..main` is greater than zero.
6. Confirm that no open PR from `main` to `accepted` already exists with `gh pr list --base accepted --head main --state open --json url`. Never create a duplicate PR.

## 2. Run the preliminary review

1. Require `scripts/ci/fast.sh` and `scripts/ci/gate.sh`; run the declared fast check on `main`. A missing command or failed check is a blocker, not a pass.
2. Run `python3 scripts/build-traceability.py --mode <lite|standard|enterprise>` using the mode in `AGENTS.md`. Review every warning and error. Lite gaps are visible warnings; unresolved IDs always fail, and Standard/Enterprise requirements without named tests fail.
3. If regenerating `TRACEABILITY.md` changed the worktree, stop. Do not silently include or commit generated state outside a task; report the change and require it to be committed as part of the relevant task before retrying.
4. Inspect the complete `accepted...main` diff. Verify scope against the approved Feature/WP, task commit prefixes, criteria, tests, configured risk controls, and the applicable Definition of Done. Do not invent missing evidence.
5. If any evidence or check is missing, report the exact blocker and stop without creating a PR.

## 3. Open the PR

1. Run `gh auth status`. Set `REPO` from `gh repo view --json nameWithOwner --jq .nameWithOwner`. If `accepted` is protected, verify via its protection endpoint that it requires a PR, strict `gate / gate`, and the configured review policy (at least one eligible approval for `reviewer`, zero for `solo-owner`); if it is unprotected, require the exact HAG-06 approval marker and risk record in `project-memory/state/M0_CHECKLIST.md` and follow the procedural fallback in `AGENTS.md`. Never treat an API inspection failure as proof that protection is unavailable. Under the fallback, the Human Owner must wait for `gate / gate` to pass before merging; then run `bash scripts/verify-accepted.sh <PR-number>` to verify the current `accepted` tip is that PR's merge commit. If protection is insufficient or the fallback was not approved, stop. Do not change remote settings yourself.
2. Build the PR title as `<WP-ID>: <Feature title>`. The body includes the scope, changed files, task IDs and commit evidence, test/check results, traceability warnings, and the human approval requirement. Keep any body file under `.git/` and remove it after the command.
3. Run `gh pr create --base accepted --head main --title "<WP-ID>: <Feature title>" --body-file <review-body>`. If `gh` fails, surface its output and do not claim a PR exists.
4. For an unprotected branch under the approved procedural fallback, wait for the PR checks and verify `gate / gate` is successful before handing off for merge. If the Gate fails or is absent, do not recommend merging.
5. Report the PR URL and state clearly that the merge remains reserved to the Human Owner under HAG-01. Under `Review policy` `reviewer`, an eligible human other than the author must approve first; under `solo-owner`, the Human Owner reads the PR and merges it personally, and that merge is the approval. Do not enable auto-merge or merge the PR.

## Local Git mode

When `AGENTS.md` sets `Git mode` to `local`, there is no `accepted` branch and agents never open PRs. Instead:

1. Require exactly one target (`F-NNN`, `WP-NNN`, or a set of `DONE` quick tasks named by the Human Owner) and require its tasks to be `DONE`.
2. Run the declared `Fast CI command` and, if declared, the `Gate CI command`; run `python3 scripts/build-traceability.py --mode lite` and review its warnings.
3. Review the relevant diff against the team's base branch named by the Human Owner (`git diff <base>...HEAD` plus uncommitted changes) with the Code Reviewer perspective, and QA/Security when risk requires it.
4. Write `project-memory/state/reviews/<target>-review.md` with scope, findings, check results, residual risks, and a ready-to-paste PR title and description that follow the team's conventions and contain no ASE IDs unless asked.
5. Report the findings. Opening the PR, requesting reviewers and merging remain human actions under the team's process.
