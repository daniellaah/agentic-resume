# V21 Specification

## Goal

V21 strengthens the critic layer by validating that each rewrite actually
covers the requirements it claims to cover.

Before V21, a rewrite suggestion could pass structural validation when its
`requirement_ids` referenced supported evidence, even if the rewritten sentence
did not mention the relevant requirement signal. For example, a rewrite could
claim to cover A/B testing and offline evaluation while the text only mentioned
Hive collaborative filtering. V21 closes that gap.

## Technology Plan

V21 uses:

- deterministic signal extraction from the existing evidence matcher
- strong domain signals for key concepts such as A/B testing, offline
  evaluation, Hive, FastAPI, Kubernetes, and recommender-system concepts
- the existing `ValidationIssue` contract
- the existing agent retry loop and validation feedback mechanism

No frontend changes are required.

## Validator Behavior

For each `RewriteSuggestion.requirement_ids` entry, the validator now checks:

1. the requirement exists in `JobAnalysis`
2. the requirement has an evidence match
3. the evidence match is not `missing`
4. the `rewritten_text` contains at least one relevant signal from the claimed
   requirement

When the requirement has strong domain signals, those signals are preferred for
coverage checking. If no strong signals are present, the validator falls back to
all extracted signals.

If the rewritten text does not cover the claimed requirement, the validator
returns a critical `unsupported_claim` issue.

## Agentic Workflow Impact

The `domain_validator_agent` now acts as a stronger critic gate. Failed coverage
checks are passed back to the `rewrite_agent` as validation feedback, allowing
the orchestrator to retry the rewrite with a more specific correction request.

The workflow version is updated to:

```json
{
  "workflow_version": "v21"
}
```

The orchestrator plan id becomes:

```text
resume_tailoring_v21
```

## Non-goals

- replacing deterministic validation with an LLM judge
- changing the `RewriteSuggestion` schema
- changing candidate generation
- changing the frontend
- supporting new input formats

## Testing Strategy

V21 tests:

- validator rejects a rewrite that claims an A/B testing requirement without
  covering A/B testing in the rewritten text
- validator accepts a rewrite that explicitly covers all claimed requirement
  signals
- rewrite generation raises `UnsafeRewriteError` when provider output claims a
  requirement that the rewritten text does not cover
- workflow metadata is updated to `v21`

## Definition of Done

- claimed requirement coverage is checked after rewrite generation
- unsupported claimed requirement coverage becomes retry feedback in the agentic
  workflow
- existing downstream validation contracts remain unchanged
- all Python and frontend checks pass
