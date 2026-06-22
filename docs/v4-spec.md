# V4 Specification

## Goal

V4 introduces an end-to-end resume tailoring pipeline.

Given resume text and job description text, the system should produce a single
structured `TailoringResult` containing the parsed resume, job analysis,
evidence matches, rewrite suggestions, validation issues, and final pipeline
status.

V4 does not add a new AI capability. Its purpose is to turn the existing V1,
V2, and V3 modules into a reusable application service that can later be called
by a CLI, API, web UI, notebook, or batch runner.

## Inputs

- Resume text
- Job description text
- Optional resume parser
- Optional job analysis provider
- Optional rewrite provider

Provider injection is required so tests can run without network access while
production usage can still call OpenAI-backed providers.

The default resume parser only supports the structured sample resume text
format used by this repository. V4 does not claim to support arbitrary resume
text, PDF files, DOCX files, or LinkedIn exports. Future API versions must make
this limitation explicit in their request contract until a broader resume
parsing layer exists.

## Outputs

`TailoringResult` contains:

- `metadata`: pipeline metadata
- `resume`: parsed `Resume`
- `job_analysis`: structured `JobAnalysis`
- `evidence_matches`: generated `EvidenceMatch[]`
- `rewrite_suggestions`: generated `RewriteSuggestion[]`
- `validation_issues`: generated `ValidationIssue[]`
- `status`: one of `success`, `completed_with_warnings`, or
  `failed_validation`

## Pipeline

```text
resume_text
-> resume_parser
-> Resume

jd_text
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

All intermediate outputs
-> TailoringResult
```

## Status Rules

`success` means validation returned no issues.

`completed_with_warnings` means validation returned one or more warning issues
and no critical issues.

`failed_validation` means validation returned one or more critical issues, or
the rewrite generator rejected generated suggestions as unsafe.

## Metadata

V4.1 adds response metadata so API consumers can identify the pipeline contract
used to produce a result.

Current metadata fields:

- `pipeline_version`: currently `v4.1`
- `resume_input_format`: currently `structured_sample_resume`

If rewrite generation fails validation, V4 should return a `TailoringResult`
with:

- the metadata
- the parsed resume
- the job analysis
- the evidence matches
- no accepted rewrite suggestions
- the critical validation issues
- `status = "failed_validation"`

## Failure Policy

V4 should not hide upstream operational failures.

The pipeline should allow the following errors to propagate:

- invalid resume text for the selected parser
- empty job description text
- invalid job analysis provider output
- invalid rewrite provider output
- missing OpenAI API key when the default OpenAI provider is used

Only unsafe generated rewrites are converted into a structured
`failed_validation` result, because that is a product-level outcome rather than
an infrastructure or schema failure.

## Non-goals

- Web UI
- CLI
- Database persistence
- User accounts
- Resume version history
- Final resume rendering
- PDF or DOCX export
- Batch application submission

## Testing Strategy

Default tests must not call OpenAI.

V4 should include:

- unit tests for the `TailoringResult` status behavior
- unit tests proving provider injection is used
- tests proving unsafe rewrites become `failed_validation`
- flow tests using sample resume and sample job description

## Definition of Done

- `app/tailoring.py` exists
- `tailor_resume_to_job(...)` exists
- Pipeline returns all intermediate artifacts
- Pipeline supports fake providers for default tests
- Unsafe rewrites return `failed_validation`
- V4 flow test passes without network access
- Existing V0, V1, V2, and V3 tests continue to pass
