from app.agent_runtime import AgentPlan, AgentPlanItem, AgentTrace


def make_plan() -> AgentPlan:
    return AgentPlan(
        plan_id="test_plan",
        orchestrator_agent="test_orchestrator_agent",
        objective="Run a test agent workflow.",
        max_iterations=2,
        items=[
            AgentPlanItem(
                step_id="parse",
                agent_name="parser_agent",
                role="specialist",
                tool_name="parse_tool",
                objective="Parse input.",
            ),
            AgentPlanItem(
                step_id="critique",
                agent_name="critic_agent",
                role="critic",
                tool_name="critic_tool",
                objective="Critique output.",
                depends_on=["parse"],
                repeatable=True,
            ),
        ],
    )


def test_agent_trace_records_steps_with_planned_agent_metadata():
    trace = AgentTrace(plan=make_plan())

    step = trace.record_step(
        tool_name="critic_tool",
        status="success",
        input_summary="1 candidate",
        output_summary="0 issues",
        attempt_number=1,
    )

    assert step.step_number == 1
    assert step.agent_name == "critic_agent"
    assert step.role == "critic"
    assert step.tool_name == "critic_tool"
    assert step.status == "success"
    assert step.attempt_number == 1
    assert trace.steps == [step]


def test_agent_trace_records_orchestrator_decisions_in_order():
    trace = AgentTrace(plan=make_plan())

    first = trace.record_decision(
        decision_type="plan",
        reason="Use the test plan.",
        next_agent="parser_agent",
    )
    second = trace.record_decision(
        decision_type="retry",
        reason="Critic found issues.",
        next_agent="parser_agent",
        attempt_number=1,
        feedback_issue_count=2,
    )

    assert first.decision_number == 1
    assert second.decision_number == 2
    assert [decision.decision_type for decision in trace.decisions] == [
        "plan",
        "retry",
    ]
    assert second.agent_name == "test_orchestrator_agent"
    assert second.feedback_issue_count == 2


def test_agent_trace_allows_unknown_tools_without_losing_trace():
    trace = AgentTrace(plan=make_plan())

    step = trace.record_step(
        tool_name="unexpected_tool",
        status="skipped",
        message="Not part of the current plan.",
    )

    assert step.agent_name == "unknown_agent"
    assert step.role == "tool"
    assert step.step_number == 1
