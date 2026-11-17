---
name: ase-roles
description: Load the relevant Lite role cards when a task requires product, architecture, engineering, review, QA, or security expertise.
---

# ASE Lite Role Cards

Load only the role cards relevant to the assigned task. These cards add a perspective; they do not authorize scope changes or override `AGENTS.md`, approved requirements, ADRs, or Human Approval Gates.

Core roles:

- [Product & Project Manager](references/product-project-manager.md): clarify task outcome and scope.
- [Solution Architect](references/solution-architect.md): check design and decision alignment.
- [Frontend Engineer](references/frontend-engineer.md): implement and verify user-interface work.
- [Backend Engineer](references/backend-engineer.md): implement and verify services, data, and integrations.
- [Code Reviewer](references/code-reviewer.md): inspect the diff for correctness and regressions.
- [Context Compiler](references/context-compiler.md): assemble the smallest sufficient context for the task.

Load these roles when the task risk or domain requires them:

- [QA Engineer](references/qa-engineer.md): design or review verification for non-trivial behavior.
- [Security Reviewer](references/security-reviewer.md): assess authentication, authorization, data exposure, dependencies, or other security-sensitive changes.

In Lite, the Implementation Engineer is the executing agent; use the frontend or backend card that matches the change. Do not activate every role for every task.

Load QA Engineer for medium- or high-risk behavior changes. Load Security Reviewer for high-risk work and whenever identity, authorization, sensitive data, dependencies, or trust boundaries are involved, including when a task was misclassified as low risk.

If a required specialist reviewer is unavailable, record the review as `UNAVAILABLE`, not `PASS`. The implementing agent may perform and document the relevant checklist, but must not describe it as an independent review. State the remaining limitations and leave the task awaiting the Human Owner's decision when the required review is an acceptance gate.
