# V1 Specification

## Goal

Given a plain-text English software engineering job description, produce a
structured `JobAnalysis` using an LLM while preserving the V0 data contract and
validation flow.

V1 introduces the first AI-powered step in the system: job description analysis.
The LLM may extract job title and requirements, but it must not generate final
resume content or bypass deterministic validation.

## Inputs

- Plain-text English resume in the controlled sample format
- Plain-text English job description

## Outputs

- Parsed `Resume`
- LLM-generated `JobAnalysis`
- Hand-written or deterministic `EvidenceMatch` data for V1 testing
- Hand-written or deterministic `RewriteSuggestion` data for V1 testing
- `ValidationIssue` results from the existing validator

## Pipeline

```text
sample_resume.txt
-> parse_sample_resume
-> Resume

sample_jd.txt
-> analyze_job_description
-> JobAnalysis

Resume + JobAnalysis + EvidenceMatch[] + RewriteSuggestion[]
-> validate_resume_tailoring
-> ValidationIssue[]
```

## LLM Boundary

The LLM is only responsible for converting job description text into
`JobAnalysis`.

The LLM must not:

- Generate final resume bullets
- Invent resume evidence
- Decide whether a rewrite suggestion is safe
- Override validator results
- Return free-form data that cannot be parsed into the Pydantic models

All LLM output must be parsed into existing Pydantic models before the data is
used by the rest of the system.

## Job Analysis Requirements

The generated `JobAnalysis` must include:

- `job_title`, if it can be clearly inferred from the job description
- `requirements`, each with:
  - stable requirement ID
  - requirement text
  - priority of `must_have` or `nice_to_have`

Requirement IDs should be deterministic within a single analysis result:

```text
req_1
req_2
req_3
...
```

The model should prefer concrete requirements over vague statements. For
example:

- Good: `Build backend APIs using Python.`
- Good: `Work with PostgreSQL-backed application data.`
- Too vague: `Be a great team player.`

## Core Rules

- The system must keep the V0 rule that resume rewrites must be evidence
  grounded.
- V1 does not allow the LLM to generate or approve rewrite suggestions.
- A `JobAnalysis` with malformed requirements must fail Pydantic validation.
- A `JobAnalysis` with empty or vague requirements may be accepted by schema
  validation but should be caught by future quality checks.
- Unit tests must not depend on live LLM calls.

## Non-goals

- Web interface
- User authentication
- PDF or DOCX parsing
- Database storage
- Cloud deployment
- LangGraph orchestration
- Automatic job application
- ATS score prediction
- LLM-generated resume rewrites
- LLM-generated evidence matching
- LLM-based fact checking
- Batch processing multiple jobs

## Implementation Plan

### 1. Configuration

Add environment-based configuration for the LLM provider.

Expected local environment variable:

```text
OPENAI_API_KEY
```

The project should include `.env.example`, but real `.env` files must remain
ignored by Git.

### 2. Dependencies

Add the official OpenAI Python SDK as a runtime dependency.

The implementation should keep Pydantic as the source of truth for structured
data. The LLM client should return data that can be validated as `JobAnalysis`.

### 3. Job Analysis Module

Create a dedicated module for job description analysis.

Proposed module:

```text
app/job_analysis.py
```

Proposed public function:

```text
analyze_job_description(jd_text: str) -> JobAnalysis
```

This function should:

- Accept raw job description text
- Call the LLM with a structured-output prompt
- Parse the model result into `JobAnalysis`
- Raise or return a controlled error if the model output cannot be validated

### 4. Tests

Unit tests should not call the real OpenAI API.

V1 should include tests for:

- Parsing a mocked valid LLM response into `JobAnalysis`
- Rejecting malformed LLM output
- Preserving deterministic requirement IDs
- Running the V1 flow using a fixture or fake LLM response

Live API tests, if added, must be separated from unit tests and skipped by
default.

### 5. V1 Flow Test

Add a flow test that uses:

- `data/sample_resume.txt`
- `data/sample_jd.txt`
- `parse_sample_resume`
- a fake or fixture-backed `JobAnalysis`
- existing validator behavior

The test should prove that replacing the hand-written V0 job analysis with the
V1 job analysis interface does not break the validation flow.

## Error Handling

The system should treat these as controlled errors:

- Empty job description input
- LLM response cannot be parsed as JSON or structured output
- LLM response fails `JobAnalysis` validation
- LLM returns no requirements for a non-empty job description

These errors should not produce partial resume rewrites.

## Testing Strategy

V1 should keep three layers of tests:

- Model tests for Pydantic schema behavior
- Parser and validator tests for deterministic behavior
- Job analysis tests using fake LLM responses

The default test command must remain:

```text
uv run pytest
```

This command must not require network access or real API credentials.

## Definition of Done

- `docs/v1-spec.md` exists and defines the V1 scope
- OpenAI SDK is added through `uv`
- `.env.example` documents required environment variables
- `analyze_job_description(jd_text: str) -> JobAnalysis` exists
- Valid mocked LLM output can be parsed into `JobAnalysis`
- Invalid mocked LLM output fails predictably
- V1 flow test passes without live network access
- Existing V0 tests continue to pass

## Deferred to V2

- LLM-generated evidence matching
- LLM-generated rewrite suggestions
- Semantic fact checking of rewritten bullets
- Human review UI
- Exporting tailored resumes
- Persistent storage
- Multi-job batch tailoring
