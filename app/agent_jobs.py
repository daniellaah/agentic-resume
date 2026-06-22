from collections.abc import Callable
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator
from rq import Queue
from sqlalchemy.orm import Session

from app.persistence import (
    DEFAULT_DATABASE_URL,
    AgentRunJobRecord,
    create_agent_run_job_record,
    create_database_engine,
    create_session_factory,
    init_database,
    mark_agent_run_job_failed,
    mark_agent_run_job_running,
    mark_agent_run_job_succeeded,
    save_agentic_tailoring_result,
)
from app.tailoring_agent import AgenticTailoringResult, tailor_resume_to_job_agentic

AgentRunJobStatus = Literal["queued", "running", "succeeded", "failed"]
TailoringAgentJobService = Callable[..., AgenticTailoringResult]


class AgenticTailoringJobRequest(BaseModel):
    resume_text: str = Field(min_length=1)
    job_description_text: str = Field(min_length=1)
    max_attempts: int = Field(default=2, ge=1, le=3)

    @field_validator("resume_text", "job_description_text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text fields must not be blank.")
        return value


class AgenticTailoringJobEnqueueResult(BaseModel):
    job_id: str
    rq_job_id: str
    status: AgentRunJobStatus


class AgenticTailoringJobExecutionResult(BaseModel):
    job_id: str
    run_id: str | None = None
    status: AgentRunJobStatus


def enqueue_agentic_tailoring_job(
    queue: Queue,
    session: Session,
    request: AgenticTailoringJobRequest,
    *,
    database_url: str = DEFAULT_DATABASE_URL,
    job_id: str | None = None,
) -> AgenticTailoringJobEnqueueResult:
    agent_job_id = job_id or str(uuid4())
    create_agent_run_job_record(
        session,
        job_id=agent_job_id,
        request_payload=request,
        rq_job_id=agent_job_id,
    )
    queue.enqueue(
        run_agentic_tailoring_job,
        agent_job_id,
        request.model_dump(mode="json"),
        database_url,
        job_id=agent_job_id,
    )
    session.flush()
    return AgenticTailoringJobEnqueueResult(
        job_id=agent_job_id,
        rq_job_id=agent_job_id,
        status="queued",
    )


def run_agentic_tailoring_job(
    job_id: str,
    request_payload: dict,
    database_url: str = DEFAULT_DATABASE_URL,
) -> dict:
    request = AgenticTailoringJobRequest.model_validate(request_payload)
    engine = create_database_engine(database_url)
    init_database(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        result = execute_agentic_tailoring_job(
            session,
            job_id=job_id,
            request=request,
        )
        session.commit()
        return result.model_dump(mode="json")


def execute_agentic_tailoring_job(
    session: Session,
    *,
    job_id: str,
    request: AgenticTailoringJobRequest,
    tailoring_service: TailoringAgentJobService | None = None,
) -> AgenticTailoringJobExecutionResult:
    mark_agent_run_job_running(session, job_id)
    service = tailoring_service or tailor_resume_to_job_agentic

    try:
        result = service(
            resume_text=request.resume_text,
            jd_text=request.job_description_text,
            max_attempts=request.max_attempts,
        )
        run = save_agentic_tailoring_result(session, result, run_id=job_id)
        job_record = mark_agent_run_job_succeeded(session, job_id, run.id)
        return _execution_result_from_record(job_record)
    except Exception as error:
        mark_agent_run_job_failed(session, job_id, str(error))
        raise


def _execution_result_from_record(
    job_record: AgentRunJobRecord,
) -> AgenticTailoringJobExecutionResult:
    return AgenticTailoringJobExecutionResult(
        job_id=job_record.id,
        run_id=job_record.run_id,
        status=job_record.status,
    )
