# V2 Specification

## Goal

Given a parsed `Resume` and structured `JobAnalysis`, produce deterministic
`EvidenceMatch` objects that map each job requirement to supporting resume
bullet IDs.

V2 replaces hand-written evidence mapping with a conservative matcher. It does
not generate resume rewrites.

## Inputs

- Parsed `Resume`
- `JobAnalysis`

## Outputs

- `EvidenceMatch[]`

Each job requirement must receive exactly one `EvidenceMatch`.

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

Resume + JobAnalysis + EvidenceMatch[] + RewriteSuggestion[]
-> validate_resume_tailoring
-> ValidationIssue[]
```

## Matching Boundary

V2 evidence matching is deterministic and local.

The matcher may use:

- Resume bullet text
- Job requirement text
- Normalized lexical tokens
- Curated technical keyword aliases

The matcher must not use:

- LLM calls
- Embeddings
- Resume summary as evidence
- Skills list as evidence
- Inferred facts not present in resume bullets

## Status Rules

The matcher may return these statuses:

- `strong`: a requirement is supported by one or more bullets with matching
  technical evidence.
- `weak`: a requirement has partial evidence but lacks a strong technical
  signal.
- `missing`: no resume bullet supports the requirement.

The `uncertain` status remains available in the schema but is deferred for
future LLM or embedding-based evidence matching.

## Evidence Rules

- Only resume bullet IDs may appear in `EvidenceMatch.bullet_ids`.
- A `missing` match must have an empty `bullet_ids` list.
- A `strong` or `weak` match must have at least one `bullet_id`.
- The matcher should be conservative: generic words such as `work`, `team`,
  `experience`, and `services` should not create evidence by themselves.

## Non-goals

- LLM-generated evidence matching
- LLM-generated resume rewrites
- Semantic fact checking
- Embeddings
- Vector database
- Web interface
- Persistent storage
- Batch processing

## Definition of Done

- `app/evidence_matcher.py` exists
- `match_evidence(resume, job_analysis)` returns one match per requirement
- Python/FastAPI requirements match the API bullet
- PostgreSQL requirements match the database bullet
- automated testing requirements match the pytest bullet
- Kubernetes deployment requirements return `missing`
- V2 flow test passes with the existing validator
- Existing V0 and V1 tests continue to pass
