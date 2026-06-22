# V7 Specification

## Goal

V7 improves the local developer workflow for running and inspecting the API.

The project already has an end-to-end pipeline and a FastAPI interface. V7 adds
small, runnable examples so a developer can clone the repository, start the API,
send a known-good request, and inspect the response without reading test code.

## Deliverables

- `examples/tailor_request.json`
- `examples/curl_tailor.sh`
- README local workflow instructions
- tests that validate the example request payload

## Local API Workflow

Install dependencies:

```bash
uv sync
```

Start the API with environment variables from `.env`:

```bash
uv run --env-file .env uvicorn app.api:app --host 127.0.0.1 --port 8000
```

Check health:

```bash
curl http://127.0.0.1:8000/health
```

Run the sample tailoring request:

```bash
bash examples/curl_tailor.sh
```

Open interactive API docs:

```text
http://127.0.0.1:8000/docs
```

## Example Request Contract

`examples/tailor_request.json` must use the same request shape as `POST
/tailor`:

```json
{
  "resume_text": "...",
  "job_description_text": "..."
}
```

The sample resume must use `structured_text_v1`, the only supported resume
input format in V6 and V7.

## Environment

The default API path uses OpenAI-backed providers. Local runs require:

```text
OPENAI_API_KEY
```

The model can be configured with:

```text
OPENAI_MODEL_NAME
```

## Non-goals

- new AI behavior
- frontend UI
- deployment automation
- authentication
- Docker packaging
- API versioning
- request persistence

## Testing Strategy

V7 tests should validate:

- the example JSON payload conforms to `TailorRequest`
- the example resume can be parsed by the V6 input layer
- the example job description is non-empty
- the curl script exists and targets `/tailor`

Default tests must not call OpenAI.

## Definition of Done

- README includes install, test, run, and example request commands
- example request payload is valid JSON
- example payload validates against the API request model
- example resume parses through `parse_resume_text`
- Ruff and full test suite pass
