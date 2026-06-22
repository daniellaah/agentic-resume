# V15 Specification

## Goal

V15 adds a local production runtime foundation.

The goal is to make the API, async worker, Redis queue, PostgreSQL database, and
database migrations runnable as one local system. This turns the V13/V14 async
agent job architecture into something that can be exercised outside isolated
unit tests.

V15 does not add new agent intelligence. It makes the agentic system easier to
run, debug, and eventually deploy.

## Technology Plan

V15 uses:

- Docker for a reproducible application image
- Docker Compose for local multi-service orchestration
- PostgreSQL for production-like persistence
- Redis for the RQ queue backend
- RQ worker process for async agent execution
- Alembic migration service for database schema setup
- psycopg as the PostgreSQL SQLAlchemy driver

## Runtime Services

V15 defines five Compose services:

```text
api
worker
migrate
redis
postgres
```

### api

Runs:

```text
uvicorn app.api:app --host 0.0.0.0 --port 8000
```

The API exposes synchronous tailoring endpoints and async agent-run endpoints.

### worker

Runs:

```text
python -m app.worker
```

The worker consumes the `agentic-tailoring` queue and executes background agent
jobs created by `POST /agent-runs`.

### migrate

Runs:

```text
alembic upgrade head
```

The migration service applies schema changes before the API and worker start.

### redis

Provides the RQ queue backend.

### postgres

Provides durable persistence for agent jobs, runs, traces, decisions, and
attempts.

## Worker Module

V15 adds:

```text
module: app/worker.py
```

It reads:

```text
AGENT_JOB_QUEUE_NAME
REDIS_URL
```

and starts an RQ worker for that queue.

## Environment

V15 extends `.env.example` with:

```text
DATABASE_URL=sqlite:///agentic_resume.db
REDIS_URL=redis://localhost:6379/0
AGENT_JOB_QUEUE_NAME=agentic-tailoring
```

Docker Compose overrides these with service-to-service URLs.

## Workflow Version

V15 updates agent metadata:

```json
{
  "workflow_version": "v15"
}
```

The orchestrator plan id becomes:

```text
resume_tailoring_v15
```

## Non-goals

- frontend trace viewer
- production cloud deployment
- Kubernetes
- Terraform
- authentication
- real Redis integration tests in CI
- Docker image publishing

Those are intentionally left for later versions.

## Testing Strategy

Default tests do not build Docker images or start Compose services.

V15 should test:

- worker settings read defaults and environment overrides
- Dockerfile starts the API process
- Compose defines API, worker, migration, Redis, and Postgres services
- environment example includes runtime settings
- `.dockerignore` excludes local state and secrets
- existing agentic workflow tests still pass

## Definition of Done

- `Dockerfile` exists
- `docker-compose.yml` exists
- `.dockerignore` exists
- `app/worker.py` exists
- `psycopg` is a runtime dependency
- workflow version is `v15`
- Ruff and full test suite pass
