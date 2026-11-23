---
name: ase-status
description: Generate a read-only daily project situation report covering roadmap position, WBS inner detour sequences (T-NNNN.1) and Return Stack, daily activity delta, critical insights/risks, a dedicated Next Steps paragraph, and a first-person singular ("I") standup/stakeholder update, then propose (without auto-creating) saving a report or stakeholder PDF. Use when asked to run /ase-status or check daily project status.
---

# `/ase-status`

> If the repository's root `AGENTS.md` belongs to the team and is not the ASE rules file, the installer placed the ASE rules in `.agents/AGENTS.md`; every reference to `AGENTS.md` in this skill means that file. When `.ase/` encapsulation is present, `project-memory/`, `artifacts/`, `scripts/`, and `templates/` resolve under `.ase/`. Always use first-person singular (`"I"`, addressing the Human Owner as `"you"`, never `"we"`).

Produce an on-demand daily operational pulse for multi-week projects. Because `/ase-status` is read-only by default, it requires **no task file** (`AGENTS.md` §5). Never write or generate report files automatically unless the Human Owner explicitly confirms your proposal.

## 1. Run the deterministic status helper

Run from the repository root:

```sh
python3 scripts/project-status.py          # or python3 .ase/scripts/project-status.py
```

Also run `python3 scripts/git-advisor.py --milestone task` (or `.ase/scripts/git-advisor.py`) if you need remote/branch details.

## 2. Present the 6 mandatory sections in chat

Present the report concisely in chat, covering:

1. **Roadmap Position & Progress:**
   - Completion percentage and task counts across all lifecycle states (`DONE`, `IN_PROGRESS`, `IN_REVIEW`, `PAUSED`, `TODO`, `BLOCKED`, `DEFERRED`, `SUPERSEDED`).
   - Explicit list of any WBS-inserted inner sequence tasks (`T-NNNN.1`, `T-NNNN.2`, `T-NNNN.1.1`) so the Human Owner immediately sees which tasks were inserted after the initial roadmap.
   - Wave and Feature / Work Package progress.
2. **Active Task, Inner Sequence Queue & Return Stack:**
   - Current task in `state/NEXT_TASK.md`, any queued steps in an active inner WBS sequence, and any `PAUSED` task on the Return Stack waiting to be resumed.
3. **Daily / Recent Activity Delta:**
   - Tasks completed on the latest active day, verification cycles used, and uncommitted worktree changes.
4. **Critical Insights, Friction & Risks:**
   - Blocked or paused tasks, verification friction hotspots (`correction_cycles > 0`), high-risk upcoming tasks, roadmap drift from detours/pivots, traceability warnings, and `KNOWN_ISSUES.md`.
5. **Next Steps (Dedicated Paragraph):**
   - A clear paragraph explaining the immediate next action (which task or inner WBS sequence step to run next, which `PAUSED` task will resume afterward, any pending `HAG` decision, and the exact `/ase-*` command to invoke next).
6. **Daily Standup / Stakeholder Update (First-Person Singular `"I"`):**
   - A ready-to-copy 3-bullet update written strictly in the Human Owner's first-person singular voice (`"I"`, never `"we"`) and verified free of any ASE framework terms (`ASE`, `DCP`, `HAG-*`, `/ase-*`, `project-memory/`).

## 3. Propose (never auto-create) saving the report or stakeholder PDF

At the end of your response, **propose** (ask the Human Owner) whether to persist the report:

- **Option A — Markdown snapshot:** Save to `.ase/artifacts/04-verification/status-YYYY-MM-DD.md` (or `artifacts/04-verification/status-YYYY-MM-DD.md`) via `python3 scripts/project-status.py --write-report <path>` and verify with `python3 scripts/verify-external-clean.py --check-first-person <path>`.
- **Option B — Executive Stakeholder PDF:** Generate a stakeholder-level status PDF via `python3 scripts/build-stakeholder-pdf.py` (using the repository's configured `work` Sopra Steria Group palette or `personal` palette) and verify with `python3 scripts/verify-external-clean.py`.

Do **not** create either file until the Human Owner says yes.
