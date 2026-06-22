# V20 Specification

## Goal

V20 improves evidence mapping for machine learning and recommender-system
resumes.

The previous rule-based matcher was backend-oriented and recognized only a
small set of web/API/database signals. In recommender-system resumes, that
caused strong evidence such as candidate generation, two-tower retrieval, ANN
serving, offline evaluation, Hive, and production ML pipelines to be marked as
missing. V20 expands the matcher while keeping the same `EvidenceMatch`
contract.

## Technology Plan

V20 uses:

- rule-based phrase matching for multi-word ML and recommender concepts
- canonical signal aliases for ML, retrieval, ranking, and data tooling
- profile-level signals from resume summary and skills
- existing Pydantic data contracts
- existing critic and validation stages

No frontend changes are required.

## Evidence Matching Behavior

The matcher now recognizes domain concepts such as:

- candidate generation
- two-tower models
- embedding-based retrieval
- ANN serving
- A/B testing
- offline evaluation
- collaborative filtering
- Recall@K
- Hive, Spark, PyTorch, TensorFlow, Flink, Airflow
- production ML pipelines

Bullet evidence remains the only evidence that can generate rewrite candidates.
Skills and summary signals can mark a requirement as `uncertain` when the
requirement is present in the profile but not supported by a specific bullet.
This prevents unsafe rewrites that inject skills into unrelated bullets.

## Critic Behavior

V20 adds a narrow critic rule for A/B testing ownership claims.

If the source bullet only says something happened before A/B testing, a rewrite
must not claim that the candidate implemented, launched, owned, ran, or
conducted A/B testing.

## Workflow Version

V20 updates agent metadata:

```json
{
  "workflow_version": "v20"
}
```

The orchestrator plan id becomes:

```text
resume_tailoring_v20
```

## Non-goals

- replacing the matcher with an LLM evidence mapper
- changing `EvidenceMatch` schema
- adding skill IDs as first-class evidence
- changing the frontend
- supporting arbitrary resume formats

Those are later milestones.

## Testing Strategy

V20 tests:

- recommender-system requirements map to relevant bullets
- skills-only evidence becomes `uncertain`
- existing backend-oriented matcher behavior still works
- A/B testing ownership expansion is rejected by the critic
- workflow metadata is updated to `v20`
- full Python and frontend checks pass

## Definition of Done

- recommender-system JD requirements are no longer mostly marked missing
- rewrite candidates are still restricted to bullet-supported evidence
- critic catches A/B testing ownership expansion
- workflow version is `v20`
