import pytest
from fakeredis import FakeRedis
from rq import Queue
from sqlalchemy import select

from app.agent_jobs import (
    AgenticTailoringJobRequest,
    enqueue_agentic_tailoring_job,
    execute_agentic_tailoring_job,
    run_agentic_tailoring_job,
)
from app.models import Resume, ResumeBullet, ResumeExperience
from app.persistence import (
    AgentRunJobRecord,
    AgentRunRecord,
    create_agent_run_job_record,
    create_database_engine,
    create_session_factory,
    init_database,
)
from app.tailoring_agent import AGENT_WORKFLOW_VERSION, tailor_resume_to_job_agentic


def make_request() -> AgenticTailoringJobRequest:
    return AgenticTailoringJobRequest(
        resume_text="resume text",
        job_description_text="Backend Engineer JD",
        max_attempts=2,
    )


def fake_resume_parser(resume_text: str) -> Resume:
    assert resume_text == "resume text"
    return Resume(
        experience=[
            ResumeExperience(
                id="exp_1",
                company="Acme Analytics",
                title="Software Engineer",
                start_date="2024-01",
                bullets=[
                    ResumeBullet(
                        id="exp_1_bullet_1",
                        text="Built internal REST APIs using Python and FastAPI.",
                    )
                ],
            )
        ],
        skills=["Python", "FastAPI"],
    )


def fake_job_analysis_provider(jd_text: str):
    assert jd_text == "Backend Engineer JD"
    return {
        "job_title": "Backend Engineer",
        "requirements": [
            {
                "id": "req_1",
                "text": "Build backend APIs using Python.",
                "priority": "must_have",
            },
            {
                "id": "req_2",
                "text": "Design REST services with FastAPI.",
                "priority": "must_have",
            },
        ],
    }


def fake_rewrite_provider(candidates, feedback):
    assert feedback == []
    assert len(candidates) == 1
    return {
        "suggestions": [
            {
                "bullet_id": "exp_1_bullet_1",
                "rewritten_text": (
                    "Built Python and FastAPI REST APIs for internal workflows."
                ),
                "requirement_ids": ["req_1", "req_2"],
            }
        ]
    }


def fake_tailoring_service(*, resume_text: str, jd_text: str, max_attempts: int):
    return tailor_resume_to_job_agentic(
        resume_text=resume_text,
        jd_text=jd_text,
        max_attempts=max_attempts,
        resume_parser=fake_resume_parser,
        job_analysis_provider=fake_job_analysis_provider,
        rewrite_provider=fake_rewrite_provider,
    )


def make_session_factory(database_url: str = "sqlite:///:memory:"):
    engine = create_database_engine(database_url)
    init_database(engine)
    return create_session_factory(engine)


def test_enqueue_agentic_tailoring_job_persists_queued_job_and_rq_payload():
    session_factory = make_session_factory()
    queue = Queue(
        "agentic-tailoring-test",
        connection=FakeRedis(),
        is_async=True,
    )
    request = make_request()

    with session_factory() as session:
        result = enqueue_agentic_tailoring_job(
            queue,
            session,
            request,
            job_id="11111111-1111-1111-1111-111111111111",
        )
        session.commit()

        saved = session.get(AgentRunJobRecord, result.job_id)

    assert result.status == "queued"
    assert result.rq_job_id == result.job_id
    assert saved is not None
    assert saved.status == "queued"
    assert saved.request_json["job_description_text"] == "Backend Engineer JD"
    assert queue.fetch_job(result.rq_job_id) is not None


def test_execute_agentic_tailoring_job_persists_successful_agent_run():
    session_factory = make_session_factory()
    request = make_request()

    with session_factory() as session:
        create_agent_run_job_record(
            session,
            job_id="22222222-2222-2222-2222-222222222222",
            request_payload=request,
            rq_job_id="22222222-2222-2222-2222-222222222222",
        )
        execution_result = execute_agentic_tailoring_job(
            session,
            job_id="22222222-2222-2222-2222-222222222222",
            request=request,
            tailoring_service=fake_tailoring_service,
        )
        session.commit()

    with session_factory() as session:
        saved_job = session.get(AgentRunJobRecord, execution_result.job_id)
        saved_run = session.scalars(select(AgentRunRecord)).one()

    assert execution_result.status == "succeeded"
    assert execution_result.run_id == "22222222-2222-2222-2222-222222222222"
    assert saved_job is not None
    assert saved_job.status == "succeeded"
    assert saved_job.run_id == saved_run.id
    assert saved_run.workflow_version == AGENT_WORKFLOW_VERSION
    assert saved_run.plan_id == "resume_tailoring_v18"


def test_execute_agentic_tailoring_job_marks_job_failed_on_error():
    session_factory = make_session_factory()
    request = make_request()

    def failing_service(**kwargs):
        raise RuntimeError("LLM provider unavailable")

    with session_factory() as session:
        create_agent_run_job_record(
            session,
            job_id="33333333-3333-3333-3333-333333333333",
            request_payload=request,
            rq_job_id="33333333-3333-3333-3333-333333333333",
        )

        with pytest.raises(RuntimeError, match="LLM provider unavailable"):
            execute_agentic_tailoring_job(
                session,
                job_id="33333333-3333-3333-3333-333333333333",
                request=request,
                tailoring_service=failing_service,
            )
        session.commit()

    with session_factory() as session:
        saved = session.get(
            AgentRunJobRecord,
            "33333333-3333-3333-3333-333333333333",
        )

    assert saved is not None
    assert saved.status == "failed"
    assert saved.error_message == "LLM provider unavailable"


def test_run_agentic_tailoring_job_uses_database_url_and_returns_execution_result(
    tmp_path,
    monkeypatch,
):
    database_url = f"sqlite:///{tmp_path / 'agent_jobs.db'}"
    session_factory = make_session_factory(database_url)
    request = make_request()

    with session_factory() as session:
        create_agent_run_job_record(
            session,
            job_id="44444444-4444-4444-4444-444444444444",
            request_payload=request,
            rq_job_id="44444444-4444-4444-4444-444444444444",
        )
        session.commit()

    monkeypatch.setattr(
        "app.agent_jobs.tailor_resume_to_job_agentic",
        fake_tailoring_service,
    )

    result = run_agentic_tailoring_job(
        "44444444-4444-4444-4444-444444444444",
        request.model_dump(mode="json"),
        database_url,
    )

    assert result == {
        "job_id": "44444444-4444-4444-4444-444444444444",
        "run_id": "44444444-4444-4444-4444-444444444444",
        "status": "succeeded",
    }
