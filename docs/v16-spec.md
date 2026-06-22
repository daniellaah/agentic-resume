# V16 Specification

## Goal

V16 adds a minimal agent trace viewer.

The goal is to make async agent runs observable through a product UI. Instead of
debugging only through JSON responses, a user can open a web interface, enter a
job id, and inspect the persisted agent plan, steps, orchestrator decisions,
attempts, and final result.

V16 does not add new agent reasoning. It improves agent observability.

## Technology Plan

V16 uses:

- Next.js for the frontend application
- TypeScript for frontend type safety
- React server components for server-side trace loading
- lucide-react for UI icons
- CSS for a lightweight operational interface
- existing FastAPI endpoints for trace data

The frontend reads:

```text
GET /agent-runs/{job_id}/trace
```

It does not call OpenAI and does not require direct database access.

## Frontend Package

V16 adds:

```text
frontend/
```

Important files:

```text
frontend/app/page.tsx
frontend/app/globals.css
frontend/lib/api.ts
frontend/lib/types.ts
frontend/package.json
frontend/Dockerfile
```

## Trace Viewer Experience

The first viewer supports:

- job id lookup
- job status summary
- plan metadata
- specialist and critic step table
- orchestrator decision timeline
- attempt summary
- final rewrite result summary

The UI is intentionally operational rather than marketing-oriented. It is meant
for inspecting agent behavior, debugging retries, and validating critic output.

## Docker Compose

V16 extends Compose with:

```text
frontend
```

The frontend service reads:

```text
AGENTIC_RESUME_API_URL=http://api:8000
```

and exposes:

```text
http://localhost:3000
```

## CI

V16 extends CI with:

```text
npm ci
npm run typecheck
npm run build
```

The Python test pipeline remains unchanged.

## Workflow Version

V16 updates agent metadata:

```json
{
  "workflow_version": "v16"
}
```

The orchestrator plan id becomes:

```text
resume_tailoring_v16
```

## Non-goals

- authentication
- run list page
- creating jobs from the frontend
- streaming updates
- WebSockets
- editing generated resume bullets
- visual eval dashboards

Those are intentionally left for later versions.

## Testing Strategy

V16 should test:

- frontend package scripts exist
- frontend Dockerfile builds a standalone Next.js app
- Compose includes the frontend service
- Python test suite still passes
- frontend typecheck passes
- frontend production build passes

## Definition of Done

- `frontend/` exists
- trace viewer page exists
- frontend can fetch `/agent-runs/{job_id}/trace`
- Compose includes frontend service
- CI includes frontend typecheck and build
- workflow version is `v16`
- Python and frontend checks pass
