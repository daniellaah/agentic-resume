# V17 Specification

## Goal

V17 adds a minimal agent run intake experience to the frontend.

V16 made completed or pending agent runs observable through a trace viewer.
V17 closes the loop by letting a user create an async agentic tailoring run from
the same web app, then redirecting directly to the new run's trace page.

V17 does not change the specialist agent reasoning steps. It improves the
product workflow around the orchestrator by connecting user input, async job
creation, and trace inspection.

## Technology Plan

V17 uses:

- Next.js route handlers for server-side form submission
- TypeScript for request and response type safety
- existing FastAPI async run creation through `POST /agent-runs`
- existing trace loading through `GET /agent-runs/{job_id}/trace`
- HTML forms for a no-client-state first implementation
- CSS for the expanded operational UI

The frontend still does not call OpenAI directly. The backend owns the agentic
workflow, queueing, persistence, and LLM calls.

## User Flow

The user can:

1. open the frontend
2. paste resume text
3. paste a job description
4. choose the maximum number of rewrite attempts
5. create an agent run
6. land on the trace page for the queued run

The frontend submits:

```text
POST /agent-runs
```

with:

```json
{
  "resume_text": "...",
  "job_description_text": "...",
  "max_attempts": 2
}
```

On success, the frontend redirects to:

```text
/?jobId={job_id}
```

## Agentic Design Rationale

The new UI is not itself an agent. It is the product entry point into the
agentic workflow.

The actual agentic behavior remains in the backend:

- the orchestrator defines the plan
- specialist agents perform resume intake, JD analysis, evidence mapping, and
  rewrite generation
- critic agents check claims and domain constraints
- orchestrator decisions accept, retry, skip, or reject attempts
- the persisted trace records how the workflow executed

V17 makes this workflow usable as an application instead of only as an API.

## Frontend Additions

V17 adds:

```text
frontend/app/agent-runs/route.ts
```

and extends:

```text
frontend/app/page.tsx
frontend/app/globals.css
frontend/lib/api.ts
frontend/lib/types.ts
```

## Workflow Version

V17 updates agent metadata:

```json
{
  "workflow_version": "v17"
}
```

The orchestrator plan id becomes:

```text
resume_tailoring_v17
```

## Non-goals

- file uploads
- PDF or DOCX parsing
- authentication
- run list page
- polling or streaming run updates
- WebSockets
- editing generated resume bullets in the UI
- live multi-agent visualization

Those remain later product and agent observability milestones.

## Testing Strategy

V17 should test:

- the frontend includes an agent run creation form
- the Next.js route handler calls the frontend API client
- the frontend API client posts to `/agent-runs`
- workflow metadata is updated to `v17`
- Python tests still pass
- frontend typecheck passes
- frontend production build passes

## Definition of Done

- user can create an async agent run from the frontend
- successful creation redirects to the trace viewer for the new job id
- trace lookup from V16 still works
- workflow version is `v17`
- Python and frontend checks pass
