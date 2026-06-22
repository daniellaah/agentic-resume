import pytest
from fakeredis import FakeRedis
from fastapi.testclient import TestClient
from rq import Queue
from sqlalchemy.pool import StaticPool

from app.agent_jobs import (
    AgenticTailoringJobRequest,
    execute_agentic_tailoring_job,
)
from app.api import app, get_agent_job_queue, get_database_session
from app.models import Resume, ResumeBullet, ResumeExperience
from app.persistence import (
    create_agent_run_job_record,
    create_database_engine,
    create_session_factory,
    init_database,
)
from app.tailoring_agent import AGENT_WORKFLOW_VERSION, tailor_resume_to_job_agentic


@pytest.fixture
def agent_run_client():
    app.dependency_overrides.clear()
    engine = create_database_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_database(engine)
    session_factory = create_session_factory(engine)
    queue = Queue(
        "agentic-tailoring-test",
        connection=FakeRedis(),
        is_async=True,
    )

    def override_database_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_database_session] = override_database_session
    app.dependency_overrides[get_agent_job_queue] = lambda: queue

    with TestClient(app) as test_client:
        yield test_client, session_factory, queue

    app.dependency_overrides.clear()


def make_request_json() -> dict:
    return {
        "resume_text": "resume text",
        "job_description_text": "Backend Engineer JD",
        "max_attempts": 2,
    }


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


def test_create_agent_run_enqueues_job(agent_run_client):
    client, _, queue = agent_run_client

    response = client.post("/agent-runs", json=make_request_json())

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["job_id"]
    assert payload["rq_job_id"] == payload["job_id"]
    assert payload["run_id"] is None
    assert queue.fetch_job(payload["rq_job_id"]) is not None


def test_get_agent_run_returns_queued_status(agent_run_client):
    client, _, _ = agent_run_client
    created = client.post("/agent-runs", json=make_request_json()).json()

    response = client.get(f"/agent-runs/{created['job_id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_agent_run_returns_404_for_unknown_job(agent_run_client):
    client, _, _ = agent_run_client

    response = client.get("/agent-runs/missing-job")

    assert response.status_code == 404
    assert response.json() == {"detail": "Agent run job not found."}


def test_get_agent_run_trace_returns_empty_trace_before_completion(agent_run_client):
    client, _, _ = agent_run_client
    created = client.post("/agent-runs", json=make_request_json()).json()

    response = client.get(f"/agent-runs/{created['job_id']}/trace")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job"] == created
    assert payload["plan"] is None
    assert payload["steps"] == []
    assert payload["decisions"] == []
    assert payload["attempts"] == []
    assert payload["final_result"] is None


def test_get_agent_run_trace_returns_persisted_trace_after_completion(
    agent_run_client,
):
    client, session_factory, _ = agent_run_client
    job_id = "55555555-5555-5555-5555-555555555555"
    request = AgenticTailoringJobRequest.model_validate(make_request_json())

    with session_factory() as session:
        create_agent_run_job_record(
            session,
            job_id=job_id,
            request_payload=request,
            rq_job_id=job_id,
        )
        execute_agentic_tailoring_job(
            session,
            job_id=job_id,
            request=request,
            tailoring_service=fake_tailoring_service,
        )
        session.commit()

    response = client.get(f"/agent-runs/{job_id}/trace")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job"]["status"] == "succeeded"
    assert payload["job"]["run_id"] == job_id
    assert payload["plan"]["plan_id"] == "resume_tailoring_v18"
    assert payload["final_result"]["status"] == "success"
    assert [step["agent_name"] for step in payload["steps"]] == [
        "resume_intake_agent",
        "jd_analysis_agent",
        "evidence_mapper_agent",
        "tailoring_strategy_agent",
        "rewrite_agent",
        "fact_critic_agent",
        "domain_validator_agent",
    ]
    assert [decision["decision_type"] for decision in payload["decisions"]] == [
        "plan",
        "accept",
    ]
    assert payload["attempts"][0]["status"] == "accepted"
    assert payload["final_result"]["metadata"]["pipeline_version"] == "v6"
    assert payload["job"]["status"] == "succeeded"
    assert payload["final_result"]["metadata"]
    assert AGENT_WORKFLOW_VERSION == "v18"
