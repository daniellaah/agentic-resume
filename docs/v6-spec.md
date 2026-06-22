# V6 Specification

## Goal

V6 introduces a dedicated resume input layer.

The goal is to make resume parsing a stable application boundary before adding
broader file parsing, frontend upload flows, or user-facing API clients.

V6 does not attempt to parse arbitrary resumes. It wraps the existing structured
resume parser with explicit input-format metadata and controlled errors.

## Supported Input Format

V6 supports one resume input format:

```text
structured_text_v1
```

The format must include:

- `Summary` heading
- `Skills` heading
- `Experience` heading
- experience headers using `Company - Title`
- date ranges using `start - end`
- bullet lines using stable IDs: `- [bullet_id] Bullet text`

Example bullet:

```text
- [exp_1_bullet_1] Built internal REST APIs using Python and FastAPI.
```

## Application Boundary

The public parser entrypoint is:

```text
parse_resume_text(text) -> Resume
```

It should:

- reject empty input
- parse supported structured text into `Resume`
- wrap parser and schema errors as `ResumeInputError`
- keep internal parser details out of API error handling

The lower-level sample parser may continue to exist, but application code should
use the V6 input layer by default.

## Pipeline Metadata

V6 updates tailoring metadata:

```json
{
  "pipeline_version": "v6",
  "resume_input_format": "structured_text_v1"
}
```

This metadata lets API clients understand what resume format was accepted when a
result was generated.

## API Behavior

The V5 API should map `ResumeInputError` to HTTP `400`.

Request body validation errors, such as missing or blank fields, still return
HTTP `422`.

## Non-goals

- PDF parsing
- DOCX parsing
- LinkedIn export parsing
- arbitrary plain-text resume parsing
- LLM-based resume extraction
- file upload
- resume repair or auto-formatting

## Testing Strategy

Default tests should cover:

- valid `structured_text_v1` input
- empty resume text
- unsupported or malformed resume text
- API mapping from `ResumeInputError` to HTTP `400`
- updated pipeline metadata

## Definition of Done

- `app/resume_input.py` exists
- `parse_resume_text(...)` exists
- `ResumeInputError` exists
- tailoring pipeline uses `parse_resume_text` by default
- metadata reports `pipeline_version = "v6"`
- metadata reports `resume_input_format = "structured_text_v1"`
- API maps resume input errors to HTTP `400`
- Ruff and full test suite pass
