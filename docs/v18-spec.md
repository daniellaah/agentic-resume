# V18 Specification

## Goal

V18 adds live agent run monitoring to the frontend.

V17 allowed a user to create an async agentic tailoring run from the web app.
However, after redirecting to the trace page, queued or running jobs still
required manual refresh. V18 makes the trace viewer watch active runs and stop
polling after the run reaches a terminal state.

V18 does not change the specialist or critic agent reasoning. It improves the
runtime feedback loop around async agent execution.

## Technology Plan

V18 uses:

- TanStack Query for client-side server-state management
- React client components for live polling behavior
- Next.js route handlers as a backend-for-frontend proxy
- existing FastAPI trace APIs for persisted agent run data
- TypeScript for frontend request and response safety
- CSS for a compact live monitor status bar

The browser does not call the FastAPI service directly. It calls a relative
Next.js route:

```text
GET /agent-runs/{job_id}/trace
```

That route calls the backend API from the server side, where
`AGENTIC_RESUME_API_URL` can point to either localhost or the Docker Compose API
service.

## User Flow

The user can:

1. create an async run from the frontend
2. land on the run trace page
3. see queued or running status
4. let the page refresh automatically while the run is active
5. see polling stop after success or failure

Active statuses:

```text
queued
running
```

Terminal statuses:

```text
succeeded
failed
```

## Agentic Design Rationale

Agentic workflows are often long-running and iterative. A useful product needs
to expose the runtime state of the orchestrator, specialist agents, critic
agents, retries, and terminal decisions.

V18 supports that by making the UI observe the persisted trace over time. The
agentic logic still lives in the backend. The frontend becomes the monitoring
surface for the agent run lifecycle.

## Frontend Additions

V18 adds:

```text
frontend/app/agent-run-workspace.tsx
frontend/app/query-provider.tsx
frontend/app/agent-runs/[jobId]/trace/route.ts
frontend/lib/client-api.ts
```

V18 keeps:

```text
frontend/app/page.tsx
```

as a server entry point that reads query params and provides initial trace data.

## Polling Policy

The trace query polls every 2.5 seconds while the job status is active.

Polling stops when the trace reports a terminal job status.

The UI also refetches on window focus, so a stale tab can catch up when the
user returns to it.

## Workflow Version

V18 updates agent metadata:

```json
{
  "workflow_version": "v18"
}
```

The orchestrator plan id becomes:

```text
resume_tailoring_v18
```

## Non-goals

- WebSockets
- Server-Sent Events
- run history page
- push notifications
- multi-user collaboration
- live token streaming
- visual graph animation

Those can be evaluated after the polling-based monitor proves the basic runtime
experience.

## Testing Strategy

V18 should test:

- TanStack Query is installed
- the frontend has a query provider
- the trace workspace uses polling
- polling only targets active job statuses
- the browser calls a relative Next.js trace route
- the Next.js trace route calls the server-side backend API client
- workflow metadata is updated to `v18`
- Python tests still pass
- frontend typecheck passes
- frontend production build passes

## Definition of Done

- active agent runs auto-refresh in the trace viewer
- polling stops on terminal job statuses
- frontend does not expose Docker-internal API URLs to the browser
- workflow version is `v18`
- Python and frontend checks pass
