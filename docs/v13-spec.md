# V13 Specification

## Goal

V13 adds an asynchronous agent job foundation.

The goal is to prepare the system for long-running agent workflows that should
not block an HTTP request. A resume tailoring run can now be represented as a
background job, executed by a worker, persisted to the database, and inspected
later.

V13 does not replace the current synchronous `/tailor/agentic` endpoint. It
adds the queue and worker primitives needed before introducing job APIs.

## Technology Plan

V13 uses:

- Redis as the queue backend
- RQ as the Python job queue
- SQLAlchemy for job lifecycle persistence
- Alembic for the job table migration
- fakeredis for tests that should not require a real Redis server

RQ was chosen before Celery or Temporal because it is small, explicit, and easy
to learn. It is enough for the first background-agent execution layer. Celery or
Temporal may be considered later if the workflow needs advanced scheduling,
durable execution, cancellation, or complex distributed orchestration.

## Runtime Module

V13 adds:

```text
module: app/agent_jobs.py
```

The module defines:

- `AgenticTailoringJobRequest`
- `AgenticTailoringJobEnqueueResult`
- `AgenticTailoringJobExecutionResult`
- `enqueue_agentic_tailoring_job(...)`
- `run_agentic_tailoring_job(...)`
- `execute_agentic_tailoring_job(...)`

## Job Lifecycle

V13 introduces a job lifecycle:

```text
queued -> running -> succeeded
queued -> running -> failed
```

The queue stores work for background workers. The database stores durable job
state and connects the job to the persisted agent run.

## Database Changes

V13 adds:

```text
agent_run_jobs
```

The table stores:

- job id
- RQ job id
- job status
- linked agent run id
- error message
- serialized request payload
- creation timestamp
- update timestamp

Migration:

```text
alembic/versions/0002_create_agent_run_jobs.py
```

## Execution Flow

The V13 background flow is:

```text
1. Create AgenticTailoringJobRequest
2. Save agent_run_jobs row with status=queued
3. Enqueue run_agentic_tailoring_job in RQ
4. Worker marks job as running
5. Worker calls tailor_resume_to_job_agentic
6. Worker persists AgenticTailoringResult
7. Worker marks job as succeeded with run_id
8. If execution fails, worker marks job as failed with error_message
```

## Workflow Version

V13 updates agent metadata:

```json
{
  "workflow_version": "v13"
}
```

The orchestrator plan id becomes:

```text
resume_tailoring_v13
```

## Non-goals

- new public job API endpoints
- frontend job status UI
- worker deployment scripts
- real Redis integration tests
- job cancellation
- human-in-the-loop pause/resume
- Temporal-style durable execution

Those are intentionally left for later versions.

## Testing Strategy

Default tests must not call OpenAI or require a real Redis server.

V13 should test:

- enqueue creates a queued database job record
- enqueue stores an RQ job payload
- execution marks a job running then succeeded
- execution persists the agent run
- execution links job to run
- execution marks failed jobs with error messages
- worker wrapper uses a database URL and returns execution status

## Definition of Done

- `RQ` and `Redis` are runtime dependencies
- `fakeredis` is a dev/test dependency
- `app/agent_jobs.py` exists
- `agent_run_jobs` migration exists
- workflow version is `v13`
- job tests pass without real Redis or OpenAI
- Ruff and full test suite pass
