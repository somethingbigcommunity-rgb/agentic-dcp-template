# M0 Checklist — Lite

This is descriptive project state. Leave every item pending until its evidence is available. `/ase-setup` records the setup task ID, the verified commit, dates, commands, results, and GitHub run URLs below; never record credentials.

| Check | Status | Evidence |
|-------|--------|----------|
| New project, Lite mode, `vscode` engine, and approved stack | PENDING | Not verified |
| Copilot is usable in the project workspace | PENDING | Not verified |
| Project Memory and task are present; Fast and Gate scripts are approved and pass locally | PENDING | Not verified |
| GitHub `origin` and `main` are synchronized | PENDING | Not verified |
| `accepted` exists and is protected without overwriting existing rules | PENDING | Not verified |
| Hosted Fast workflow passes on the verified setup commit | PENDING | Not verified |
| Hosted M0 smoke workflow runs the Gate script successfully on that commit | PENDING | Not verified |
| An eligible human reviewer other than the PR author can approve future PRs | PENDING | Not verified |
| Optional Graphify choice and any enabled checks | PENDING | Not chosen |

The M0 smoke workflow tests the Gate command on GitHub Actions. It is not a `main → accepted` PR and does not prove that the real PR gate or branch protection rejects an invalid merge. Those checks must be verified separately; HAG-01 remains in force.
