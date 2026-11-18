---
name: ase-roles
description: Load the relevant Lite role cards when a task requires product, architecture, engineering, review, QA, or security expertise.
---

# ASE Lite Role Cards

> If the repository's root `AGENTS.md` belongs to the team and is not the ASE rules file, the installer placed the ASE rules in `.agents/AGENTS.md`; every reference to `AGENTS.md` in this skill means that file.

Load only the role cards relevant to the assigned task. These cards add a perspective; they do not authorize scope changes or override `AGENTS.md`, approved requirements, ADRs, or Human Approval Gates.

Core roles (role cards and corresponding `.agents/agents/` subagents):

- [Product & Project Manager](references/product-project-manager.md) (`product-project-manager`): clarify task outcome and scope.
- [Solution Architect](references/solution-architect.md) (`solution-architect`): check design and decision alignment.
- [Frontend Engineer](references/frontend-engineer.md) (`frontend-engineer`): implement and verify user-interface work.
- [Backend Engineer](references/backend-engineer.md) (`backend-engineer`): implement and verify services, data, and integrations.
- [Code Reviewer](references/code-reviewer.md) (`code-reviewer`): inspect the diff for correctness and regressions.
- [Context Compiler](references/context-compiler.md) (`context-compiler`): assemble the smallest sufficient context for the task.

Load these roles when the task risk or domain requires them:

- [QA Engineer](references/qa-engineer.md) (`qa-engineer`): design or review verification for non-trivial behavior.
- [Security Reviewer](references/security-reviewer.md) (`security-reviewer`): assess authentication, authorization, data exposure, dependencies, or other security-sensitive changes.

In Antigravity, you can delegate independent reviews or specialist sub-tasks using `invoke_subagent` with the corresponding agent name from `.agents/agents/<role>.md` (or `self` / `research` passing the role card instructions in the subagent prompt). In Lite, the Implementation Engineer is the executing agent; use the frontend, backend, or database card that matches the change. Do not activate every role for every task.

Load QA Engineer for medium- or high-risk behavior changes. Load Security Reviewer for high-risk work and whenever identity, authorization, sensitive data, dependencies, or trust boundaries are involved, including when a task was misclassified as low risk.

If a required specialist reviewer is unavailable, record the review as `UNAVAILABLE`, not `PASS`. The implementing agent may perform and document the relevant checklist, but must not describe it as an independent review. State the remaining limitations and leave the task awaiting the Human Owner's decision when the required review is an acceptance gate.
