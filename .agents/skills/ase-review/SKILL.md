---
name: ase-review
description: Review a completed ASE Work Package, verify local evidence and traceability, then open its main-to-accepted pull request. Use when asked to run /ase-review or prepare a Work Package for acceptance.
---

# `/ase-review`

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

1. Run `gh auth status`. Set `REPO` from `gh repo view --json nameWithOwner --jq .nameWithOwner`. Use `gh api repos/$REPO/branches/accepted/protection --jq '.required_status_checks.contexts | index("gate / gate") != null'` and `gh api repos/$REPO/branches/accepted/protection --jq '.required_pull_request_reviews.required_approving_review_count >= 1'`; both must return `true`. If protection is missing or insufficient, stop and ask the Human Owner to inspect it. `bash scripts/protect-accepted.sh --apply` can initialize an unprotected branch only after explicit authorization; it refuses to replace detected protection. Do not change remote settings yourself.
2. Build the PR title as `<WP-ID>: <Feature title>`. The body includes the scope, changed files, task IDs and commit evidence, test/check results, traceability warnings, and the human approval requirement. Keep any body file under `.git/` and remove it after the command.
3. Run `gh pr create --base accepted --head main --title "<WP-ID>: <Feature title>" --body-file <review-body>`. If `gh` fails, surface its output and do not claim a PR exists.
4. Report the PR URL and state clearly that the merge remains reserved to the Human Owner under HAG-01. Under `Review policy` `reviewer`, an eligible human other than the author must approve first; under `solo-owner`, the Human Owner reads the PR and merges it personally, and that merge is the approval. Do not enable auto-merge or merge the PR.
