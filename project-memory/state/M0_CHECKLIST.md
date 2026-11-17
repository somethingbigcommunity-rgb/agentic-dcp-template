# M0 Checklist — Lite

This is descriptive project state. Leave every item pending until its evidence is available. `/ase-setup` records the setup task ID, the verified commit, dates, commands, results, and GitHub run URLs below; never record credentials.

| Check | Status | Evidence |
|-------|--------|----------|
| New project, Lite mode, `vscode` engine, and approved stack | PENDING | Not verified |
| Copilot is usable in the project workspace | PENDING | Not verified |
| Project Memory and task are present; Fast and Gate scripts are approved and pass locally | PENDING | Not verified |
| GitHub `origin` and `main` are synchronized | PENDING | Not verified |
| `accepted` exists and is protected, or the procedural HAG-01 fallback is explicitly approved (HAG-06) | PENDING | Not verified |
| Hosted Fast workflow passes on the verified setup commit | PENDING | Not verified |
| Hosted M0 smoke workflow runs the Gate script successfully on that commit | PENDING | Not verified |
| Review policy confirmed: an eligible reviewer other than the PR author (`reviewer`), or the Human Owner merges personally as the HAG-01 approval (`solo-owner`, Lite only) | PENDING | Not verified |
| Optional Graphify choice and any enabled checks | PENDING | Not chosen |

The M0 smoke workflow tests the Gate command on GitHub Actions. It is not a `main → accepted` PR and does not prove that the real PR gate or branch protection rejects an invalid merge. Those checks must be verified separately; HAG-01 remains in force.

HAG-06 procedural accepted-gate fallback: PENDING
Reason and accepted residual risk: PENDING

Use this record only if GitHub cannot enforce branch protection. After the Human Owner explicitly accepts the residual risk, replace `PENDING` with `APPROVED — YYYY-MM-DD`, state why protection is unavailable and that direct pushes/early merges cannot be technically blocked, and record that `gate / gate` must pass before the Human Owner merges each PR. This does not waive any separate reviewer requirement.
