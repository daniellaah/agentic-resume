# V9 Specification

## Goal

V9 adds explicit agent tool tracing to the existing validation-driven agentic
workflow.

The goal is not to rename every module as an agent. The goal is to make the
actual agent's tool use observable:

```text
agent = workflow controller
tools = resume input, job analysis, evidence matching, rewrite generation,
validation
```

## Agent Step Trace

`AgenticTailoringResult` now includes:

```text
steps: AgentStep[]
```

Each `AgentStep` records:

- `step_number`
- `tool_name`
- `status`
- `input_summary`
- `output_summary`
- optional `message`
- optional `attempt_number`

Supported tool names:

- `resume_input`
- `job_analysis`
- `evidence_matching`
- `rewrite_candidate_builder`
- `rewrite_generation`
- `validation`

Supported step statuses:

- `success`
- `failed`
- `skipped`

## Trace Semantics

For a successful one-attempt run, the trace should look like:

```text
1. resume_input -> success
2. job_analysis -> success
3. evidence_matching -> success
4. rewrite_candidate_builder -> success
5. rewrite_generation attempt 1 -> success
6. validation attempt 1 -> success
```

For a repaired run, later rewrite and validation steps should include
`attempt_number = 2`, `attempt_number = 3`, and so on.

For a failed rewrite provider output, the rewrite step should be marked
`failed`, and the validation step for that attempt should be marked `skipped`.

For no supported rewrite candidates, rewrite generation and validation should be
marked `skipped`.

## Workflow Version

V9 updates agent metadata:

```json
{
  "workflow_version": "v9"
}
```

Pipeline metadata remains unchanged:

```json
{
  "pipeline_version": "v6",
  "resume_input_format": "structured_text_v1"
}
```

## API

`POST /tailor/agentic` returns the same `AgenticTailoringResult`, now including
`steps`.

The API route does not need a new path because V9 is an additive response model
change for the existing agentic endpoint.

## Non-goals

- dynamic tool selection
- external tool registry
- planner LLM
- persistent memory
- database-backed trace storage
- frontend trace visualization

## Testing Strategy

Default tests must not call OpenAI.

V9 should test:

- successful step sequence
- retry step sequence
- no-candidate skipped steps
- API serialization of `steps`
- sample-data flow trace

## Definition of Done

- `AgentStep` model exists
- `AgenticTailoringResult.steps` exists
- agent records major tool calls
- retry attempts are tied to attempt-specific steps
- workflow version is `v9`
- Ruff and full test suite pass
