---
context_profile: work # work | personal
status: DRAFT         # DRAFT | APPROVED
date: YYYY-MM-DD
---
# Project Charter & `6W+1H` Context Dossier

> Populated during `/ase-adopt` or `/ase-setup` using the **3-Tier Discovery Order**: (1) `inputs/` directory first, (2) repository metadata fallback, (3) adaptive `work` or `personal` interview. Any field or section evaluated by the Human Owner as not relevant may be marked `SKIPPED (not relevant)`.

## 1. CHI — Stakeholders, Governance & Authorship

- **Project Context Profile:** `work` <!-- work | personal -->
- **Author & Role (for `"I"` deliverables):** <Name / Role, or SKIPPED>
- **Delivery Organization & Practice (`work`):** <e.g. Sopra Steria Group S.p.A. — Practice/BU, or SKIPPED>
- **Client Organization & Industry Domain (`work`):** <Client name, department, industry, or SKIPPED>
- **Stakeholders, RACI & Reviewer / Approver (`work`):** <Business Owner, Tech Referent, Approver, target audience, or SKIPPED>
- **Confidentiality / Classification (`work`):** <e.g. Client Confidential / Internal, or SKIPPED>
- **Target Users & Visual Theme (`personal`):** <Target users and preferred PDF palette preset, or SKIPPED>

## 2. PERCHÉ — Business Context, Objectives & Drivers

- **Problem Statement & As-Is Pain Points:** <Why this work exists, or SKIPPED>
- **Target Business & Technical KPIs (`work`):** <Measurable outcomes / SLAs, or SKIPPED>
- **Ranked Optimization Drivers:** <Priority order among Cost (HAG-04), Time/Latency, Security (HAG-03), Quality (HAG-01), Usability (UX/DX)>

## 3. COSA — Scope, Deliverables & Untouchable Boundaries

- **Engagement / Project Type:** <Greenfield | Evolutionary Maintenance | Migration | Audit & Reconciliation | Bugfix/Hardening | PoC>
- **In-Scope Deliverables:** <Code/SQL/modules + required `deliverables/` reports/PDFs>
- **Strict Out-of-Scope (Untouchable Perimeter):** <Modules, tables, or systems that must NEVER be modified, or SKIPPED>
- **Assumptions & Upstream Dependencies (`work`):** <Required accesses, upstream teams/feeds, or SKIPPED>

## 4. DOVE — System Landscape, Environments & Trackers

- **Runtime & Environment Topology:** <Local / DEV / UAT / PRE-PROD / PROD, cloud provider, project/dataset/DB, or SKIPPED>
- **Upstream & Downstream Integrations (`work`):** <Data sources, BI/API consumers, network/VPN constraints, or SKIPPED>
- **Git Hosting, Branches & Issue Tracker:** <GitHub/GitLab/Azure DevOps, working/target branch, Jira/board key prefix, or SKIPPED>

## 5. QUANDO — Timeline, Milestones & Reporting Cadence

- **Timeline & Key Dates (`work`):** <Start date, UAT date, Go-Live / Delivery deadline, milestones, or SKIPPED>
- **Reporting Cadence:** <Daily `/ase-status`, weekly client SAL, or on-demand, or SKIPPED>

## 6. QUANTO — Volumetry, SLAs & FinOps Guardrails (`HAG-04`)

- **Data Volumetry & Scale (`work`):** <Row counts, data sizes, concurrency, or SKIPPED>
- **Performance & Latency SLAs (`HAG-04`):** <Max response time, batch window, or SKIPPED>
- **Cloud / Query / Token Cost Ceiling (`HAG-04`):** <Max bytes billed per query, API/cloud budget, or SKIPPED>

## 7. COME — Stack, Security/GDPR & Quality Gates (`HAG-03`, `HAG-05`)

- **Tech Stack & Dependency Policy (`HAG-05`):** <Languages, frameworks, allowed/forbidden external libraries>
- **Security, Privacy & GDPR Rules (`HAG-03`, `work`):** <PII masking/anonymization, RBAC/IAM, secrets handling, or SKIPPED>
- **Verification & Acceptance Criteria:** <Fast CI command, Gate CI command, reconciliation/UAT sign-off rules>
