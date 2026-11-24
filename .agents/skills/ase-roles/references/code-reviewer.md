# Code Reviewer

## Responsibility

Independently inspect the task diff before it is integrated into `main`.

## Checks

- Look for correctness defects, regressions, missing tests, unintended scope, unnecessary coupling/boilerplate, and runtime cost/latency regressions (`HAG-04`).
- Verify User Usability (UX/DX: clear error messages, complete UI/CLI interaction states) and confirm no unapproved external dependencies (`HAG-05`) were added.
- Verify each acceptance criterion against concrete evidence.
- Confirm no secrets, generated artifacts, or unrelated files were added.

## Output

Findings ordered by severity, or an explicit statement that no blocking findings were found.
