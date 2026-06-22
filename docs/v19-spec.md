# V19 Specification

## Goal

V19 adds an LLM provider abstraction and a local Ollama backend.

The backend can now run the same agentic resume workflow with either a local
Ollama model or OpenAI. Ollama is the default backend for local-first
development, cost control, and experimentation with weaker model outputs that
exercise the validator and critic loop.

## Technology Plan

V19 uses:

- a shared Python provider module for structured LLM calls
- OpenAI Responses API for the OpenAI backend
- Ollama's native `/api/chat` endpoint for the local backend
- Pydantic models as the structured output contract
- existing downstream validators for schema and domain safety
- Docker Compose environment variables for API and worker configuration

The frontend does not change in V19.

## Public Configuration

Default local configuration:

```text
LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:latest
OLLAMA_TIMEOUT_SECONDS=120
```

OpenAI configuration:

```text
LLM_BACKEND=openai
OPENAI_API_KEY=
OPENAI_MODEL_NAME=gpt-5.5
```

When running without Docker, `OLLAMA_BASE_URL` can be:

```text
http://localhost:11434
```

When running inside Docker Compose, it should be:

```text
http://host.docker.internal:11434
```

## Provider Behavior

The shared provider accepts:

- system prompt
- user content
- Pydantic response model

and returns a JSON-compatible dictionary.

OpenAI path:

- uses `responses.parse`
- relies on the OpenAI SDK to parse into the response model
- requires `OPENAI_API_KEY`

Ollama path:

- posts to `/api/chat`
- sets `stream` to `false`
- sets `format` to `json`
- sets temperature to `0`
- includes the Pydantic JSON schema in the system prompt
- parses the returned message content as JSON

Both paths still flow through existing business parsing:

- job analysis validates `JobAnalysis`
- rewrite generation validates `RewriteSuggestionBatch`
- rewrite safety checks and critic checks remain unchanged

## Error Handling

Provider configuration errors return service-unavailable responses through the
API layer.

Provider request errors, such as Ollama being unreachable, also return
service-unavailable responses.

Provider output errors are treated as invalid provider output and mapped through
the existing job analysis or rewrite output errors.

## Workflow Version

V19 updates agent metadata:

```json
{
  "workflow_version": "v19"
}
```

The orchestrator plan id becomes:

```text
resume_tailoring_v19
```

## Non-goals

- auto-pulling Ollama models
- model selection in the UI
- provider-specific prompt tuning beyond JSON schema guidance
- streaming tokens from Ollama
- replacing Ollama as the default local backend
- changing agent orchestration behavior

## Testing Strategy

V19 tests:

- default backend selection
- OpenAI structured output request wiring
- missing OpenAI key behavior
- unsupported backend behavior
- Ollama request payload shape
- Ollama JSON parsing
- Ollama invalid JSON handling
- Ollama request error handling
- API mapping for provider request failures
- Docker Compose provider environment
- workflow version metadata

V19 also adds an optional integration test:

```text
RUN_OLLAMA_INTEGRATION=1
```

It calls a local Ollama model and verifies that job analysis returns at least
one deterministic requirement.

## Definition of Done

- Ollama is the default backend
- OpenAI can be selected with `LLM_BACKEND=openai`
- API and worker receive provider configuration
- local Docker Compose can reach host Ollama through `host.docker.internal`
- existing agentic workflow tests pass
- Python lint, format check, and tests pass
