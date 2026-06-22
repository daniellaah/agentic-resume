# V11 Specification

## Goal

V11 introduces the first explicit agent runtime foundation for the resume
tailoring workflow.

The goal is to move the project from a fixed pipeline with agent-like behavior
toward an agentic architecture with:

- an orchestrator agent
- specialist agent roles
- critic agent roles
- an explicit execution plan
- explicit orchestrator decisions
- structured trace metadata for debugging and evaluation

V11 does not replace the existing deterministic tools or LLM calls. It wraps
them in an agent runtime contract so the system can evolve toward planning,
handoffs, reflection, and multi-agent execution without rewriting the business
logic again.

## Runtime Module

V11 adds:

```text
module: app/agent_runtime.py
```

The runtime defines the shared primitives used by agentic workflows:

- `AgentPlan`
- `AgentPlanItem`
- `AgentStep`
- `AgentDecision`
- `AgentTrace`

These models are intentionally framework-neutral. They can later be mapped to
OpenAI Agents SDK, LangGraph, Google ADK, or another orchestration runtime.

## Orchestrator Agent

The top-level orchestrator is:

```text
resume_tailoring_orchestrator_agent
```

It owns the plan, records decisions, and decides whether to accept, retry,
reject, or skip.

V11 records orchestrator decisions such as:

- `plan`
- `retry`
- `accept`
- `reject`
- `skip`

The first V11 implementation still executes a predictable workflow, but the
result now exposes the decisions that make the orchestration explicit.

## Specialist and Critic Agents

V11 maps existing workflow stages to agent roles:

| Tool | Agent | Role |
| --- | --- | --- |
| `resume_input` | `resume_intake_agent` | specialist |
| `job_analysis` | `jd_analysis_agent` | specialist |
| `evidence_matching` | `evidence_mapper_agent` | specialist |
| `rewrite_candidate_builder` | `tailoring_strategy_agent` | specialist |
| `rewrite_generation` | `rewrite_agent` | specialist |
| `claim_checker` | `fact_critic_agent` | critic |
| `validation` | `domain_validator_agent` | critic |

This is not a rename-only change. Each step now carries `agent_name` and `role`
metadata in the trace, and each run carries the plan that explains why those
agents were selected.

## Agent vs Tool Boundary

V11 keeps the boundary clear:

- agents own goals, decisions, retry behavior, and feedback loops
- tools perform concrete operations with structured inputs and outputs

For example:

- `fact_critic_agent` is the critic role
- `app/claim_checker.py` is the deterministic tool used by that critic
- `rewrite_agent` is the specialist role
- `app/rewrite_generator.py` provides rewrite generation tools

This avoids the common anti-pattern of renaming every module to `agent` without
adding agentic behavior.

## API Output

`AgenticTailoringResult` now includes:

```text
plan: AgentPlan
decisions: AgentDecision[]
steps: AgentStep[]
```

The existing `steps` list remains available, but each step now includes:

- `agent_name`
- `role`
- `tool_name`
- `status`
- input and output summaries
- attempt metadata

## Workflow Version

V11 updates agent metadata:

```json
{
  "workflow_version": "v11"
}
```

Pipeline metadata remains:

```json
{
  "pipeline_version": "v6",
  "resume_input_format": "structured_text_v1"
}
```

## Non-goals

- dynamic LLM-generated planning
- autonomous agent routing
- external framework migration
- persistent memory
- human-in-the-loop clarification
- parallel critic execution

Those are intentionally left for later versions.

## Testing Strategy

Default tests must not call OpenAI.

V11 should test:

- `AgentTrace` records planned agent metadata
- `AgentTrace` records orchestrator decisions in order
- agentic tailoring returns a plan
- agentic tailoring steps include specialist and critic roles
- retry and terminal outcomes produce explicit orchestrator decisions
- existing V10 behavior remains compatible

## Definition of Done

- `app/agent_runtime.py` exists
- `AgenticTailoringResult` includes `plan` and `decisions`
- `tailoring_agent` uses `AgentTrace`
- workflow version is `v11`
- specialist and critic roles appear in step traces
- retry, accept, reject, and skip decisions are recorded
- Ruff and full test suite pass
