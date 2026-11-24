# Initial Project Context Inbox (`inputs/`)

Drop all your initial project materials here **before** running `/ase-adopt`, `/ase-setup`, or `/ase-plan`:

- Client briefs, RFPs, functional specifications, or architecture documents (`.md`, `.txt`, `.pdf`, `.json`)
- Meeting notes, email threads, or Jira / ticket exports
- Data schemas, SQL dumps, sample payloads, or screenshots
- A quick `notes.md` with any context you already know (*Chi, Cosa, Perché, Dove, Quando, Quanto, Come*)

## How ASE Uses `inputs/` (3-Tier Discovery Order)

1. **Tier 1 (`inputs/` First):** ASE reads every file in `inputs/` **first** to extract project context before scanning the repository.
2. **Tier 2 (Repo Metadata Fallback):** Only for technical details not answered in `inputs/`, ASE inspects `README*`, build manifests, CI workflows, and top-level folders.
3. **Tier 3 (Skippable `6W+1H` Interview):** ASE shows what it extracted and asks **only** the remaining unresolved questions for your context profile (`work` vs. `personal`). You can skip any question or section that is not relevant.

> **Privacy & Cleanliness:** In `local` Git mode, `inputs/` is excluded from Git via `.git/info/exclude`, hidden in the IDE Explorer by `/ase-pack` once the project is packed, and excluded from `/ase-export` stakeholder `.zip` bundles.
