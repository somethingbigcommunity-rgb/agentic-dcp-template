# Lifecycle Artifacts

Structured output directory for generated project and stakeholder deliverables across the lifecycle (P0/P0-A through P8). Every file in this tree must pass `verify-external-clean.py` (zero ASE references), and drafted messages/reviews in `05-release-and-handover/` must use first-person singular (`"I"` / `"Io"`), never `"We"`.

| Folder | Lifecycle Phase | Generated Artifacts |
|--------|-----------------|---------------------|
| `01-discovery/` | P0-A (`/ase-adopt`) | `as-is-report` stakeholder PDFs, discovery summaries, architecture baselines |
| `02-planning/` | P1–P4 (`/ase-plan`) | `project-plan` stakeholder PDFs, WBS & PERT/CPM roadmaps |
| `03-architecture/` | P3 (Solution / Data / Security Design) | `architecture-dossier` stakeholder PDFs, vector architecture & data-flow diagrams |
| `04-verification/` | P6–P7 (`/ase-task`, `/ase-review`) | Data/SQL reconciliation outputs, benchmark results, test & quality gate evidence |
| `05-release-and-handover/` | P7–P8 (`/ase-review`) | `release-report` stakeholder PDFs, ready-to-paste PR descriptions, drafted stakeholder messages (strictly `"I"`, never `"We"`) |
| `specs/` | All phases | Declarative JSON specifications consumed by `build-stakeholder-pdf.py` |
