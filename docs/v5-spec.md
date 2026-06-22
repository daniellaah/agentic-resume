# V5 Specification

## Goal

V5 exposes the resume tailoring pipeline through a minimal HTTP API.

The API should let a client submit resume text and job description text, run the
V4.1 tailoring pipeline, and receive a structured `TailoringResult` response.

V5 is an interface layer. It must not duplicate job analysis, evidence matching,
rewrite generation, or validation logic.

## API

### `GET /health`

Returns a small health payload for local development and deployment probes.

Response:

```json
{
  "status": "ok"
}
```

### `POST /tailor`

Runs the tailoring pipeline.

Request:

```json
{
  "resume_text": "...",
  "job_description_text": "..."
}
```

Response:

```json
{
  "metadata": {
    "pipeline_version": "v4.1",
    "resume_input_format": "structured_sample_resume"
  },
  "resume": {},
  "job_analysis": {},
  "evidence_matches": [],
  "rewrite_suggestions": [],
  "validation_issues": [],
  "status": "success"
}
```

The response shape is the serialized `TailoringResult` model.

## Input Contract

V5 only supports the structured sample resume text format used by this
repository. It does not support arbitrary resume text, PDF files, DOCX files, or
LinkedIn exports.

The API request must include:

- non-empty `resume_text`
- non-empty `job_description_text`

## Error Handling

V5 should map expected application errors into HTTP responses:

- invalid request body: `422`
- invalid resume input for the current parser: `400`
- empty or invalid job description analysis input/output: `400`
- invalid rewrite provider output: `400`
- unsafe generated rewrite converted by the pipeline: `200` with
  `status = "failed_validation"`
- missing OpenAI API key for default provider: `503`

Unexpected errors should not be converted into successful responses.

## Dependency Injection

The API must expose the tailoring pipeline through a dependency function so
tests can override it without calling OpenAI.

Default runtime behavior uses:

```text
tailor_resume_to_job(resume_text, job_description_text)
```

Tests may override the dependency with a fake tailoring service.

## Non-goals

- Frontend UI
- Database persistence
- User accounts
- File upload
- PDF or DOCX parsing
- PDF or DOCX export
- Batch processing
- Authentication
- Rate limiting

## Testing Strategy

Default tests must not call OpenAI.

V5 should include:

- health endpoint test
- successful `POST /tailor` test with dependency override
- request validation test
- application error mapping test
- missing OpenAI API key mapping test

## Definition of Done

- `app/api.py` exists
- FastAPI is installed as a runtime dependency
- Uvicorn is installed for local server execution
- `GET /health` exists
- `POST /tailor` exists
- Endpoint response model is `TailoringResult`
- Tests use dependency override and do not call OpenAI
- Ruff and full test suite pass
