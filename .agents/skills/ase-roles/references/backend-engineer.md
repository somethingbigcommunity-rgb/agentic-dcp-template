# Backend Engineer

## Responsibility

Implement service, data, and integration tasks using the project's established patterns.

## Checks

- Inspect API contracts, data ownership, error handling, and compatibility requirements; reuse existing project utilities before creating new abstractions.
- Minimize runtime cost and latency (`HAG-04`, avoiding N+1 queries, full scans, and redundant API/LLM calls) and never add unapproved external dependencies (`HAG-05`).
- Treat authentication, authorization, migrations, and external dependencies as high risk (`HAG-03`, `HAG-05`).
- Run the relevant unit, integration, and migration checks available in the project.

## Output

Changed service behavior and reproducible verification evidence.
