# Correction Prompt

Use this prompt after a verification failure. Replace every placeholder with evidence from the current task; do not invent missing information.

```text
Continue only the assigned task <TASK_ID>.

Goal and acceptance criteria:
<PASTE THE TASK GOAL AND CRITERIA>

Failed verification:
<COMMAND, EXPECTED RESULT, ACTUAL RESULT>

Current correction cycle:
<N OF 3>

Diagnosis:
<ROOT CAUSE OR EXPLICITLY UNCONFIRMED HYPOTHESIS>

Relevant files and constraints:
<AFFECTED ARTIFACTS, DCP/ADR RULES, AND SCOPE LIMITS>

Make the smallest correction that addresses the cause. Preserve all acceptance
criteria, add or update regression checks, and rerun the failed verification
plus relevant regressions. Report changed files and exact results. Do not start
another task or weaken the criteria.

If this is the third failed verification, do not make another correction:
set the task to BLOCKED, record the root cause, impact, evidence, proposed
changes, regression checks, and human decision needed, then stop.
```
