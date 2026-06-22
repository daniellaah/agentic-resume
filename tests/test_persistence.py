from sqlalchemy import select

from app.models import Resume, ResumeBullet, ResumeExperience
from app.persistence import (
    AgentRunRecord,
    create_database_engine,
    create_session_factory,
    init_database,
    save_agentic_tailoring_result,
)
from app.tailoring_agent import AGENT_WORKFLOW_VERSION, tailor_resume_to_job_agentic


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


def make_agentic_result():
    return tailor_resume_to_job_agentic(
        resume_text="resume text",
        jd_text="Backend Engineer JD",
        resume_parser=fake_resume_parser,
        job_analysis_provider=fake_job_analysis_provider,
        rewrite_provider=fake_rewrite_provider,
    )


def test_save_agentic_tailoring_result_persists_run_trace_and_attempts():
    engine = create_database_engine("sqlite:///:memory:")
    init_database(engine)
    session_factory = create_session_factory(engine)
    result = make_agentic_result()

    with session_factory() as session:
        record = save_agentic_tailoring_result(
            session,
            result,
            run_id="run_1",
        )
        session.commit()

        assert record.id == "run_1"
        assert record.workflow_version == AGENT_WORKFLOW_VERSION
        assert record.status == "success"

    with session_factory() as session:
        saved = session.scalars(
            select(AgentRunRecord).where(AgentRunRecord.id == "run_1")
        ).one()

        assert saved.workflow_version == AGENT_WORKFLOW_VERSION
        assert saved.plan_id == "resume_tailoring_v15"
        assert saved.orchestrator_agent == "resume_tailoring_orchestrator_agent"
        assert saved.run_metadata["workflow_version"] == AGENT_WORKFLOW_VERSION
        assert saved.final_result_json["status"] == "success"
        assert len(saved.steps) == 7
        assert [step.agent_name for step in saved.steps] == [
            "resume_intake_agent",
            "jd_analysis_agent",
            "evidence_mapper_agent",
            "tailoring_strategy_agent",
            "rewrite_agent",
            "fact_critic_agent",
            "domain_validator_agent",
        ]
        assert [decision.decision_type for decision in saved.decisions] == [
            "plan",
            "accept",
        ]
        assert len(saved.attempts) == 1
        assert saved.attempts[0].status == "accepted"
        assert saved.attempts[0].rewrite_suggestions_json[0]["bullet_id"] == (
            "exp_1_bullet_1"
        )


def test_save_agentic_tailoring_result_generates_run_id_when_not_provided():
    engine = create_database_engine("sqlite:///:memory:")
    init_database(engine)
    session_factory = create_session_factory(engine)
    result = make_agentic_result()

    with session_factory() as session:
        record = save_agentic_tailoring_result(session, result)
        session.commit()

        assert record.id
        assert len(record.id) == 36
