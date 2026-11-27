---
name: ase-memo
description: Continuously update Project Memory from call notes, teammate messages, screenshots, and inputs/ (/ase-memo, /ase-context) with incremental SHA-256 tracking, 2-Bucket autonomous HAG triage, zero-token Graphify blast-radius lookup, and federated HANDOFF.json context sync. Use when asked to run /ase-memo, /ase-context, or update project memory/context mid-project.
---

# `/ase-memo` (and Interchangeable Alias `/ase-context`)

> If the repository's root `AGENTS.md` belongs to the team and is not the ASE rules file, the installer placed the ASE rules in `.agents/AGENTS.md`; every reference to `AGENTS.md` in this skill means that file. When `.ase/` encapsulation is present, `project-memory/`, `specs/`, `scripts/`, and `templates/` resolve under `.ase/`. Always use first-person singular (`"I"`, addressing the Human Owner as `"you"`, never `"we"`), and strictly follow the **Single-Channel Output Rule** (`AGENTS.md` §11.4: write persistent content only to its canonical file and output a 2–4 line pointer in chat, never repeating file contents in chat).

Update Project Memory at any point during an ongoing project (even when not coding) from pasted call summaries, teammate messages, screenshots, or files dropped into `inputs/`.

## 0. Step 0 Prerequisite & Topology Check (`check-prereq.py` + `sync-inputs.py`)

1. Run `python3 scripts/check-prereq.py --command ase-memo` (or `.ase/scripts/check-prereq.py --command ase-memo`).
   - If a prerequisite is missing (`M0`/`M0-A` not `PASS`, or a cloned release folder waiting for `/ase-switch` / `/ase-upgrade`), record the `prerequisite_chain` in `NEXT_TASK.md` (`sync-inputs.py --set-chain`), ask the Human Owner for approval to run the prerequisite first, and automatically continue into `/ase-memo` once approved.
2. Run `python3 scripts/sync-inputs.py --status --ensure-graphifyignore` (or `.ase/scripts/sync-inputs.py`):
   - **Read ONLY `new_files` and `modified_files` in `inputs/`**, never re-reading `unchanged_files` from earlier months (`🔻 Reduce Token Cost`).
   - If `role: member` and `<child>/.ase/project-memory/state/HANDOFF.json` has a pending `CONTEXT_MEMO_SYNC` entry from the Father Orchestrator, ingest its `memo_summary` and acknowledge it via `python3 scripts/ase-topology.py --ack <HO-NNNN>`.

## 1. Autonomous 2-Bucket HAG Triage

Classify every extracted fact from the note, screenshot, or `inputs/` file into two buckets:

1. **Bucket 1 — Non-HAG Descriptive & Informational Updates (Auto-Applied Immediately with Zero Task Ceremony):**
   - Patch non-HAG rows of `dcp/00-project-management/project-charter.md` (*Chi*, *Perché*, *Quando*, *Come* governance) via `python3 scripts/sync-inputs.py --patch-charter "Key=Value"`.
   - Update non-architectural conventions in `dcp/03-design/conventions.md` and environment blockers in `state/KNOWN_ISSUES.md`.
   - If `graphify-out/graph.json` exists, run `python3 scripts/sync-inputs.py --query-graph "<term>"` (or `ase-topology.py --query-graph "<term>"` in `orchestrator` mode) in `0` tokens to identify connected files, Graphify **God-Node** coupling (`HAG-02`), and impacted open tasks (`T-NNNN`).
   - Append the chronological entry to `state/CONTEXT_LOG.md` via `python3 scripts/sync-inputs.py --append-log --source "<source>" --summary "<summary>" --updated "<files>" --hag-status "<NONE | PENDING:HAG-XX>" [--alert-next-task "<warning>"]` and mark ingested files via `--mark-ingested`.
   - **In Father `orchestrator` mode:** If the note impacts specific Child projects, dispatch a `CONTEXT_MEMO_SYNC` handoff to each affected child via `python3 scripts/ase-topology.py --dispatch --child <subfolder> --type CONTEXT_MEMO_SYNC --objective "<memo_summary>"`.
2. **Bucket 2 — HAG-Governed Normative Changes (Gated Before Modifying Normative Files):**
   - If the note/screenshot triggers **`HAG-02`** (architecture, ADR, or backlog scope/task reshape), **`HAG-03`** (auth, GDPR/PII, data model, destructive migration), **`HAG-04`** (FinOps/cloud/query/token cost or SLA ceiling), **`HAG-05`** (new external dependency/license), or **`HAG-06`** (gate waiver):
     - Apply Bucket 1 updates first, log `PENDING:HAG-XX` in `state/CONTEXT_LOG.md`, run `python3 scripts/check-prereq.py --post --command ase-memo`, record `Pending Command Chain: /ase-memo -> /ase-plan`, and ask a single combined **HAG + Reactive Chain Approval** question before running `/ase-plan`.
   - If only Bucket 1 updates exist, output a compact 3-line Memory Update Receipt in chat pointing to `state/CONTEXT_LOG.md` and stop without opening a `T-NNNN` task.
