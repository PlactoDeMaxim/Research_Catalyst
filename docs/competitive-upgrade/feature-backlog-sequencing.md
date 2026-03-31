# Tier 1 and Tier 2 Feature Backlog Sequencing

## Dependency-Aware Sequence

## Wave 1 - Foundation Prerequisites

1. Persistent project backbone (Prisma cutover for planner/citations/editor/plagiarism jobs)
2. Unified job orchestration and status APIs
3. Evidence ingestion + chunking + retrieval service
4. Model gateway with provider abstraction + prompt registry

## Wave 2 - Tier 1 Parity Features

1. Chat with PDF (single document)
2. Cross-paper chat workspace
3. Literature review synthesis workspace
4. Multi-paper extraction tables
5. Source-grounded section drafting in editor
6. Academic writing autocomplete
7. Citation autocomplete + inline insert
8. Citation metadata validation
9. Claim-to-source traceability
10. Manuscript review assistant

## Wave 3 - Tier 2 Differentiators

1. Research gap + contradiction detector
2. Systematic review screening workflow
3. Source credibility scoring
4. Fact-check and claim verification queue
5. Plagiarism remediation assistant
6. Venue compliance checker
7. Reviewer response assistant
8. Team library, tags, and collections
9. Version history with compare/restore
10. Realtime collaboration + comments + mentions

## Feature Success Metrics

| Feature Area | KPI | Target |
|---|---|---|
| PDF/Cross-paper chat | Grounded answer rate | >= 90% |
| Literature review synthesis | Time-to-first-draft review | <= 30 min for 25 papers |
| Extraction tables | Structured field accuracy | >= 85% |
| Writing autocomplete | Suggestion acceptance rate | >= 25% |
| Citation intelligence | Citation correction rate | >= 95% metadata validity |
| Claim traceability | Claims with linked evidence | >= 90% |
| Manuscript review | Revision cycle reduction | >= 20% |
| Verification queue | Precision / recall | >= 0.85 / >= 0.75 |
| Plagiarism remediation | Accepted remediation suggestions | >= 50% |
| Collaboration | Multi-user project activity | >= 40% of active projects |

## Guardrails

- No Tier 2 feature starts before Wave 1 foundation metrics are green.
- Every AI generation feature requires grounded evidence or confidence labeling.
- All high-risk features launch behind feature flags and staged cohorts.
