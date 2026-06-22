# V14 Specification

## Goal

V14 exposes the asynchronous agent job foundation through API endpoints.

The goal is to make agent runs product-addressable:

- clients can create a background agent run
- clients can check job status
- clients can fetch persisted agent traces

V14 keeps the existing synchronous `/tailor/agentic` endpoint. The new endpoints
are additive and prepare the project for a frontend dashboard.

## Technology Plan

V14 uses:

- FastAPI for public HTTP endpoints
- RQ and Redis for job enqueueing
- SQLAlchemy for job and trace reads
- dependency injection for testable queue and database boundaries
- fakeredis and in-memory SQLite in tests

## API Endpoints

V14 adds:

```text
POST /agent-runs
GET /agent-runs/{job_id}
GET /agent-runs/{job_id}/trace
```

### POST /agent-runs

Creates an async agent run job.

Request:

```json
{
  "resume_text": "...",
  "job_description_text": "...",
  "max_attempts": 2
}
```

Response:

```json
{
  "job_id": "...",
  "rq_job_id": "...",
  "status": "queued",
  "run_id": null,
  "error_message": null
}
```

### GET /agent-runs/{job_id}

Returns durable job status.

Possible statuses:

```text
queued
running
succeeded
failed
```

### GET /agent-runs/{job_id}/trace

Returns the persisted trace when a run has completed.

If the job has not completed, the response includes the job object and empty
trace fields.

When completed, the response includes:

- plan
- steps
- decisions
- attempts
- final result

## Dependency Boundaries

V14 adds API dependencies for:

- database sessions
- RQ queues

Tests override both dependencies. This keeps default tests independent from a
real Redis server, real PostgreSQL server, and OpenAI.

## Workflow Version

V14 updates agent metadata:

```json
{
  "workflow_version": "v14"
}
```

The orchestrator plan id becomes:

```text
resume_tailoring_v14
```

## Non-goals

- worker process management
- real Redis integration tests
- streaming job updates
- frontend dashboard
- authentication
- cancellation
- human-in-the-loop resume prompts

Those are intentionally left for later versions.

## Testing Strategy

Default tests must not call OpenAI or require real Redis.

V14 should test:

- creating an agent run enqueues a job
- queued jobs can be fetched by id
- missing jobs return 404
- trace endpoint returns empty trace before completion
- trace endpoint returns persisted plan, steps, decisions, attempts, and final
  result after completion

## Definition of Done

- `/agent-runs` exists
- `/agent-runs/{job_id}` exists
- `/agent-runs/{job_id}/trace` exists
- API tests pass with dependency overrides
- workflow version is `v14`
- Ruff and full test suite pass
