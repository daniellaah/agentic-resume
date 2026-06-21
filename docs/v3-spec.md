# V3 Specification

## Goal

Given a parsed `Resume`, structured `JobAnalysis`, and generated
`EvidenceMatch[]`, produce evidence-grounded `RewriteSuggestion[]`.

V3 is the first version that generates resume rewrite suggestions. It does not
produce a final resume document and does not allow rewrites to bypass
validation.

## Inputs

- Parsed `Resume`
- `JobAnalysis`
- `EvidenceMatch[]`

## Outputs

- `RewriteSuggestion[]`
- `ValidationIssue[]` from the existing validator

## Pipeline

```text
sample_resume.txt
-> parse_sample_resume
-> Resume

sample_jd.txt
-> analyze_job_description
-> JobAnalysis

Resume + JobAnalysis
-> match_evidence
-> EvidenceMatch[]

Resume + JobAnalysis + EvidenceMatch[]
-> generate_rewrite_suggestions
-> RewriteSuggestion[]

Resume + JobAnalysis + EvidenceMatch[] + RewriteSuggestion[]
-> validate_resume_tailoring
-> ValidationIssue[]
```

## Rewrite Boundary

The rewrite generator may:

- Rewrite existing resume bullets
- Align language with supported job requirements
- Improve clarity and specificity using existing evidence

The rewrite generator must not:

- Add employers, titles, dates, metrics, team sizes, or business impact
- Add technologies not present in the source bullet
- Target requirements with `missing` evidence
- Generate suggestions without a source bullet ID
- Generate final resume documents

## Candidate Construction

V3 generates rewrite candidates by grouping evidence by source bullet.

For each `EvidenceMatch`:

- `strong` and `weak` matches are eligible
- `missing` matches are ignored
- `uncertain` matches are ignored for V3

Each candidate contains:

- one source bullet ID
- the original bullet text
- one or more supported requirement IDs and requirement texts

The LLM should return exactly one rewrite suggestion per candidate.

## Validation Gate

Generated suggestions must be validated with `validate_resume_tailoring`.

If validation returns any `critical` issue, V3 must reject the generated
suggestions.

V3 validates structural safety:

- source bullet exists
- target requirement exists
- target requirement has evidence
- target requirement is not `missing`

Semantic fact checking is deferred to a later version.

## Non-goals

- Final resume rendering
- PDF or DOCX export
- Human review UI
- Semantic fact checking
- Automatic application submission
- Batch job processing

## Testing Strategy

Default tests must not call OpenAI.

V3 should include:

- Unit tests with fake rewrite providers
- Flow tests with sample resume, fake job analysis, V2 evidence matching, and
  fake rewrite output
- Integration tests for the OpenAI rewrite provider, skipped by default

## Definition of Done

- `app/rewrite_generator.py` exists
- `generate_rewrite_suggestions(...)` exists
- Missing evidence is not sent to the rewrite provider
- Generated suggestions must pass validator safety checks
- Unsafe generated suggestions raise a controlled error
- V3 flow test passes without network access
- OpenAI integration test is available and skipped by default
- Existing V0, V1, and V2 tests continue to pass
