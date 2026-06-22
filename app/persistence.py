from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

from app.tailoring_agent import AgenticTailoringResult

DEFAULT_DATABASE_URL = "sqlite:///agentic_resume.db"


class Base(DeclarativeBase):
    pass


class AgentRunRecord(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workflow_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    orchestrator_agent: Mapped[str | None] = mapped_column(String(128))
    plan_id: Mapped[str | None] = mapped_column(String(128))
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    run_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False)
    plan_json: Mapped[dict | None] = mapped_column(JSON)
    final_result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    steps: Mapped[list[AgentStepRecord]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentStepRecord.step_number",
    )
    decisions: Mapped[list[AgentDecisionRecord]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentDecisionRecord.decision_number",
    )
    attempts: Mapped[list[AgentAttemptRecord]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentAttemptRecord.attempt_number",
    )
    jobs: Mapped[list[AgentRunJobRecord]] = relationship(back_populates="run")


class AgentRunJobRecord(Base):
    __tablename__ = "agent_run_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    rq_job_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id"))
    error_message: Mapped[str | None] = mapped_column(Text)
    request_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    run: Mapped[AgentRunRecord | None] = relationship(back_populates="jobs")


class AgentStepRecord(Base):
    __tablename__ = "agent_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    input_summary: Mapped[str | None] = mapped_column(Text)
    output_summary: Mapped[str | None] = mapped_column(Text)
    message: Mapped[str | None] = mapped_column(Text)
    attempt_number: Mapped[int | None] = mapped_column(Integer)
    step_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    run: Mapped[AgentRunRecord] = relationship(back_populates="steps")


class AgentDecisionRecord(Base):
    __tablename__ = "agent_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), nullable=False)
    decision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(128), nullable=False)
    decision_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    next_agent: Mapped[str | None] = mapped_column(String(128))
    attempt_number: Mapped[int | None] = mapped_column(Integer)
    feedback_issue_count: Mapped[int] = mapped_column(Integer, nullable=False)
    decision_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    run: Mapped[AgentRunRecord] = relationship(back_populates="decisions")


class AgentAttemptRecord(Base):
    __tablename__ = "agent_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    rewrite_suggestions_json: Mapped[list] = mapped_column(JSON, nullable=False)
    validation_issues_json: Mapped[list] = mapped_column(JSON, nullable=False)
    attempt_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    run: Mapped[AgentRunRecord] = relationship(back_populates="attempts")


def create_database_engine(
    database_url: str = DEFAULT_DATABASE_URL,
    **kwargs,
) -> Engine:
    return create_engine(database_url, future=True, **kwargs)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_session(engine: Engine) -> Generator[Session]:
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        yield session


def init_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def create_agent_run_job_record(
    session: Session,
    *,
    job_id: str,
    request_payload: BaseModel,
    rq_job_id: str | None = None,
) -> AgentRunJobRecord:
    job = AgentRunJobRecord(
        id=job_id,
        rq_job_id=rq_job_id,
        status="queued",
        request_json=_model_dump_json(request_payload),
    )
    session.add(job)
    session.flush()
    return job


def mark_agent_run_job_running(
    session: Session,
    job_id: str,
) -> AgentRunJobRecord:
    job = session.get(AgentRunJobRecord, job_id)
    if job is None:
        raise ValueError(f"Agent run job not found: {job_id}")

    job.status = "running"
    job.updated_at = datetime.now(UTC)
    session.flush()
    return job


def mark_agent_run_job_succeeded(
    session: Session,
    job_id: str,
    run_id: str,
) -> AgentRunJobRecord:
    job = session.get(AgentRunJobRecord, job_id)
    if job is None:
        raise ValueError(f"Agent run job not found: {job_id}")

    job.status = "succeeded"
    job.run_id = run_id
    job.error_message = None
    job.updated_at = datetime.now(UTC)
    session.flush()
    return job


def mark_agent_run_job_failed(
    session: Session,
    job_id: str,
    error_message: str,
) -> AgentRunJobRecord:
    job = session.get(AgentRunJobRecord, job_id)
    if job is None:
        raise ValueError(f"Agent run job not found: {job_id}")

    job.status = "failed"
    job.error_message = error_message
    job.updated_at = datetime.now(UTC)
    session.flush()
    return job


def save_agentic_tailoring_result(
    session: Session,
    result: AgenticTailoringResult,
    *,
    run_id: str | None = None,
) -> AgentRunRecord:
    run = AgentRunRecord(
        id=run_id or str(uuid4()),
        workflow_version=result.metadata.workflow_version,
        status=result.status,
        orchestrator_agent=(
            result.plan.orchestrator_agent if result.plan is not None else None
        ),
        plan_id=result.plan.plan_id if result.plan is not None else None,
        max_attempts=result.metadata.max_attempts,
        run_metadata=_model_dump_json(result.metadata),
        plan_json=_model_dump_json(result.plan) if result.plan is not None else None,
        final_result_json=_model_dump_json(result.final_result),
    )

    run.steps = [
        AgentStepRecord(
            step_number=step.step_number,
            agent_name=step.agent_name,
            role=step.role,
            tool_name=step.tool_name,
            status=step.status,
            input_summary=step.input_summary,
            output_summary=step.output_summary,
            message=step.message,
            attempt_number=step.attempt_number,
            step_json=_model_dump_json(step),
        )
        for step in result.steps
    ]
    run.decisions = [
        AgentDecisionRecord(
            decision_number=decision.decision_number,
            agent_name=decision.agent_name,
            decision_type=decision.decision_type,
            reason=decision.reason,
            next_agent=decision.next_agent,
            attempt_number=decision.attempt_number,
            feedback_issue_count=decision.feedback_issue_count,
            decision_json=_model_dump_json(decision),
        )
        for decision in result.decisions
    ]
    run.attempts = [
        AgentAttemptRecord(
            attempt_number=attempt.attempt_number,
            status=attempt.status,
            message=attempt.message,
            rewrite_suggestions_json=[
                _model_dump_json(suggestion)
                for suggestion in attempt.rewrite_suggestions
            ],
            validation_issues_json=[
                _model_dump_json(issue) for issue in attempt.validation_issues
            ],
            attempt_json=_model_dump_json(attempt),
        )
        for attempt in result.attempts
    ]

    session.add(run)
    session.flush()
    return run


def _model_dump_json(model: BaseModel) -> dict:
    return model.model_dump(mode="json")
