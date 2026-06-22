# V10 Specification

## Goal

V10 adds a claim-checking critic tool to the agentic resume tailoring workflow.

The goal is to reduce unsupported rewrite claims before producing accepted
resume suggestions.

V10 does not introduce a second autonomous agent. The module is implemented as a
focused critic tool:

```text
module: app/claim_checker.py
workflow role: critic
```

## Claim Checker

The claim checker compares one source resume bullet with one rewritten bullet:

```text
check_rewrite_claims(source_text, rewritten_text) -> ValidationIssue[]
```

It should return critical `unsupported_claim` issues when a rewrite introduces
claims not supported by the source bullet.

V10 checks:

- new technology claims
- new numeric or metric claims
- new scale or impact claims

Examples of unsupported claims:

- adding `Kubernetes` when the source bullet does not mention Kubernetes
- adding `1m users` when the source bullet does not include that scale
- adding `production`, `enterprise`, or `revenue` claims when not supported

## Agent Integration

V10 adds `claim_checker` as an explicit agent step.

For a successful one-attempt run, the trace should look like:

```text
1. resume_input -> success
2. job_analysis -> success
3. evidence_matching -> success
4. rewrite_candidate_builder -> success
5. rewrite_generation attempt 1 -> success
6. claim_checker attempt 1 -> success
7. validation attempt 1 -> success
```

If the claim checker returns critical issues:

- the `claim_checker` step is marked `failed`
- the attempt is rejected
- the critical issues become feedback for the next rewrite attempt

## Workflow Version

V10 updates agent metadata:

```json
{
  "workflow_version": "v10"
}
```

Pipeline metadata remains:

```json
{
  "pipeline_version": "v6",
  "resume_input_format": "structured_text_v1"
}
```

## Non-goals

- LLM-based semantic fact checking
- full natural-language entailment
- exhaustive claim extraction
- human approval UI
- persistent review history

## Testing Strategy

Default tests must not call OpenAI.

V10 should test:

- supported rewrites pass claim checking
- unsupported technology claims fail
- unsupported numeric claims fail
- unsupported scale or impact claims fail
- claim checker failures trigger agent retry
- agent trace includes `claim_checker`

## Definition of Done

- `app/claim_checker.py` exists
- `check_rewrite_claims(...)` exists
- `claim_checker` appears in agent trace
- unsupported claims are returned as critical validation issues
- failed claim checks can drive retry feedback
- Ruff and full test suite pass
