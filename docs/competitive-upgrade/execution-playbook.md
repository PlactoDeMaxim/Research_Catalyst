# Execution Playbook

## Rollout Gates

### Gate 1 - Foundation Ready

- Planner/citation/editor/plagiarism state persisted via Prisma-backed services.
- Shared job APIs report consistent lifecycle and retry metadata.
- Retrieval service available for at least one source type end-to-end.
- Observability baseline in place (request traces, task traces, model traces).

### Gate 2 - Tier 1 Beta Ready

- PDF chat, cross-paper chat, and extraction tables pass quality thresholds.
- Editor grounding and citation insertion work on beta projects.
- Golden eval suite in CI for retrieval, grounding, and citation validity.
- Feature flags and rollback controls validated in staging.

### Gate 3 - Tier 2 Partner Ready

- Verification queue precision/recall meets predefined thresholds.
- Collaboration conflict handling and version restore tested.
- Security and abuse safeguards validated for uploads/sharing.
- Human review queue enabled for low-confidence outputs.

### Gate 4 - GA Ready

- SLA dashboard stable for 2 consecutive release cycles.
- Canary metrics (error rate, latency, completion, user satisfaction) within thresholds.
- Incident response and on-call runbooks operational.

## Evaluation Datasets

1. **Retrieval set**: 500 queries with expected paper/chunk relevance labels.
2. **Grounding set**: 300 writing prompts with mandatory citation-backed evidence.
3. **Citation correctness set**: 1,000 citation records with verified metadata truth.
4. **Verification set**: 400 claims with known true/false/insufficient-evidence labels.
5. **Plagiarism remediation set**: 200 passages labeled across plagiarism/paraphrase/cited overlap.

## Team Staffing Assignments

### Platform Squad

- Owns persistence migration, model gateway, task orchestration, observability.
- Inputs: backend modules and infrastructure services.
- Outputs: reusable contracts consumed by product squads.

### Research Intelligence Squad

- Owns discovery, summarization, extraction, and synthesis workflows.
- Inputs: paper sources, ingestion pipeline, retrieval services.
- Outputs: chat/synthesis/extraction user experiences.

### Writing and Trust Squad

- Owns editor copilot, citation intelligence, verification, plagiarism remediation, collaboration.
- Inputs: evidence graph + model gateway + persistence.
- Outputs: publication-quality writing and trust workflows.

## Beta Customer Validation Milestones

1. **Milestone A** (end of Wave 1): 5 internal power users validate cross-device persistence and continuity.
2. **Milestone B** (mid Wave 2): 10 design partners validate literature review and chat utility.
3. **Milestone C** (end Wave 2): 15 design partners validate writing + citation workflow.
4. **Milestone D** (Wave 3): 20 partners validate verification + collaboration impact.

## Release Cadence

- Weekly integration builds.
- Bi-weekly feature-flagged beta drops.
- Monthly stability and debt burn-down sprint.
