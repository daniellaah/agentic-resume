# V8 Specification

## Goal

V8 introduces a validation-driven agentic workflow for resume tailoring.

The workflow turns the existing one-pass pipeline into a bounded loop:

```text
plan -> generate rewrite attempt -> validate -> repair or stop
```

The purpose is to improve reliability while preserving evidence-grounded resume
rewrites.

## Workflow

V8 performs:

1. parse resume input
2. analyze the job description
3. match resume evidence to job requirements
4. build rewrite candidates from supported evidence
5. generate rewrite suggestions
6. validate generated suggestions
7. if validation has critical issues, feed those issues into the next rewrite
   attempt
8. stop when an attempt is accepted or `max_attempts` is reached

The workflow is bounded. It must not retry indefinitely.

## Outputs

`AgenticTailoringResult` contains:

- `metadata`: workflow version, pipeline metadata, and max attempts
- `final_result`: accepted or failed `TailoringResult`
- `attempts`: all rewrite attempts
- `missing_requirement_ids`: requirements with missing evidence
- `accepted_requirement_ids`: requirements covered by accepted suggestions
- `rejected_requirement_ids`: requirements seen only in rejected suggestions
- `status`: `success`, `failed_validation`, or `no_rewrite_candidates`

Each `TailoringAttempt` contains:

- `attempt_number`
- `status`: `accepted`, `rejected`, or `output_error`
- `rewrite_suggestions`
- `validation_issues`
- optional `message`

## Validation Feedback

Validation feedback may include:

- validator issues from `validate_resume_tailoring`
- candidate-boundary issues, such as a suggestion targeting requirements outside
  the evidence candidate
- output formatting issues, such as invalid rewrite provider output

Only attempts without critical validation issues can be accepted.

## API

V8 adds:

```text
POST /tailor/agentic
```

Request:

```json
{
  "resume_text": "...",
  "job_description_text": "...",
  "max_attempts": 2
}
```

`max_attempts` defaults to `2` and is limited to `1..3`.

Response:

```text
AgenticTailoringResult
```

## Non-goals

- unbounded autonomous loops
- tool use outside the current pipeline
- frontend UI
- database persistence
- final resume document rendering
- PDF or DOCX export
- automatic job application submission

## Testing Strategy

Default tests must not call OpenAI.

V8 should include:

- first-attempt success
- retry after a validation failure
- failed validation after max attempts
- no-candidate path
- API dependency override for `/tailor/agentic`
- sample-data flow test with fake providers

## Definition of Done

- `app/tailoring_agent.py` exists
- `tailor_resume_to_job_agentic(...)` exists
- retry loop is bounded by `max_attempts`
- attempts are recorded
- validation feedback is passed to later rewrite attempts
- `/tailor/agentic` exists
- Ruff and full test suite pass
