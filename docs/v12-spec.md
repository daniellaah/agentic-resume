# V12 Specification

## Goal

V12 adds a persistence foundation for agentic workflow runs.

The goal is to make agent runs durable so future versions can support:

- asynchronous agent execution
- run history
- agent trace dashboards
- evaluation datasets
- retry analysis
- user-facing review workflows

V12 keeps the existing agent execution path unchanged. Persistence is an
optional boundary that can save an `AgenticTailoringResult` after a run
completes.

## Technology Plan

V12 uses:

- SQLAlchemy 2.x for ORM models and database sessions
- Alembic for schema migrations
- PostgreSQL-compatible table design
- SQLite for local tests and lightweight development

The production target is PostgreSQL, but the first implementation avoids
requiring every local test run to start a database server.

## Runtime Module

V12 adds:

```text
module: app/persistence.py
```

The module defines:

- `AgentRunRecord`
- `AgentStepRecord`
- `AgentDecisionRecord`
- `AgentAttemptRecord`
- `create_database_engine(...)`
- `create_session_factory(...)`
- `init_database(...)`
- `save_agentic_tailoring_result(...)`

## Database Tables

V12 persists four main tables:

```text
agent_runs
agent_steps
agent_decisions
agent_attempts
```

`agent_runs` stores run-level metadata:

- run id
- workflow version
- run status
- orchestrator agent
- plan id
- max attempts
- serialized metadata
- serialized plan
- serialized final result
- creation timestamp

`agent_steps` stores the agent trace:

- step number
- agent name
- role
- tool name
- status
- input and output summaries
- attempt number
- serialized step payload

`agent_decisions` stores orchestrator decisions:

- decision number
- decision type
- reason
- next agent
- attempt number
- feedback issue count
- serialized decision payload

`agent_attempts` stores rewrite attempt history:

- attempt number
- attempt status
- message
- rewrite suggestions
- validation issues
- serialized attempt payload

## Migration

V12 adds Alembic configuration:

```text
alembic.ini
alembic/env.py
alembic/versions/0001_create_agent_run_tables.py
```

The default local database URL is:

```text
sqlite:///agentic_resume.db
```

Production deployments should set:

```text
DATABASE_URL
```

## Workflow Version

V12 updates agent metadata:

```json
{
  "workflow_version": "v12"
}
```

The orchestrator plan id becomes:

```text
resume_tailoring_v12
```

## Non-goals

- automatic persistence inside `/tailor/agentic`
- async job execution
- user accounts
- dashboard UI
- PostgreSQL-only local development
- pgvector evidence search

Those are intentionally left for later versions.

## Testing Strategy

Default tests must not call OpenAI.

V12 should test:

- database tables can be initialized in SQLite
- an agentic tailoring result can be persisted
- run metadata is saved
- plan and final result JSON are saved
- steps keep agent names and roles
- decisions keep orchestrator decision types
- attempts keep rewrite suggestions and validation issues

## Definition of Done

- `SQLAlchemy` is a runtime dependency
- `Alembic` is available for migrations
- `app/persistence.py` exists
- initial migration exists
- agent run persistence tests pass
- existing agentic workflow tests still pass
- Ruff and full test suite pass
