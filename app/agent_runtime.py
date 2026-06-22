from typing import Literal

from pydantic import BaseModel, Field

AgentRole = Literal["orchestrator", "specialist", "critic", "tool"]
AgentStepStatus = Literal["success", "failed", "skipped"]
AgentDecisionType = Literal["plan", "continue", "retry", "accept", "reject", "skip"]


class AgentPlanItem(BaseModel):
    step_id: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    role: AgentRole
    tool_name: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    optional: bool = False
    repeatable: bool = False


class AgentPlan(BaseModel):
    plan_id: str = Field(min_length=1)
    orchestrator_agent: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    max_iterations: int | None = Field(default=None, ge=1)
    items: list[AgentPlanItem] = Field(min_length=1)

    def item_for_tool(self, tool_name: str) -> AgentPlanItem | None:
        for item in self.items:
            if item.tool_name == tool_name:
                return item
        return None


class AgentStep(BaseModel):
    step_number: int = Field(ge=1)
    agent_name: str = Field(default="unknown_agent", min_length=1)
    role: AgentRole = "tool"
    tool_name: str = Field(min_length=1)
    status: AgentStepStatus
    input_summary: str | None = None
    output_summary: str | None = None
    message: str | None = None
    attempt_number: int | None = Field(default=None, ge=1)


class AgentDecision(BaseModel):
    decision_number: int = Field(ge=1)
    agent_name: str = Field(min_length=1)
    decision_type: AgentDecisionType
    reason: str = Field(min_length=1)
    next_agent: str | None = None
    attempt_number: int | None = Field(default=None, ge=1)
    feedback_issue_count: int = Field(default=0, ge=0)


class AgentTrace(BaseModel):
    plan: AgentPlan
    steps: list[AgentStep] = Field(default_factory=list)
    decisions: list[AgentDecision] = Field(default_factory=list)

    def record_step(
        self,
        tool_name: str,
        status: AgentStepStatus,
        input_summary: str | None = None,
        output_summary: str | None = None,
        message: str | None = None,
        attempt_number: int | None = None,
    ) -> AgentStep:
        plan_item = self.plan.item_for_tool(tool_name)
        step = AgentStep(
            step_number=len(self.steps) + 1,
            agent_name=plan_item.agent_name if plan_item else "unknown_agent",
            role=plan_item.role if plan_item else "tool",
            tool_name=tool_name,
            status=status,
            input_summary=input_summary,
            output_summary=output_summary,
            message=message,
            attempt_number=attempt_number,
        )
        self.steps.append(step)
        return step

    def record_decision(
        self,
        decision_type: AgentDecisionType,
        reason: str,
        next_agent: str | None = None,
        attempt_number: int | None = None,
        feedback_issue_count: int = 0,
    ) -> AgentDecision:
        decision = AgentDecision(
            decision_number=len(self.decisions) + 1,
            agent_name=self.plan.orchestrator_agent,
            decision_type=decision_type,
            reason=reason,
            next_agent=next_agent,
            attempt_number=attempt_number,
            feedback_issue_count=feedback_issue_count,
        )
        self.decisions.append(decision)
        return decision
