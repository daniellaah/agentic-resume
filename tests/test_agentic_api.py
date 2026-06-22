import pytest
from fastapi.testclient import TestClient

from app.api import app, get_agentic_tailoring_service
from app.models import (
    EvidenceMatch,
    JobAnalysis,
    JobRequirement,
    Resume,
    ResumeBullet,
    ResumeExperience,
    RewriteSuggestion,
)
from app.tailoring import TailoringMetadata, TailoringResult
from app.tailoring_agent import (
    AGENT_WORKFLOW_VERSION,
    AgenticTailoringMetadata,
    AgenticTailoringResult,
    AgentStep,
    TailoringAttempt,
)


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_resume() -> Resume:
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
                        text="Built Python and FastAPI REST APIs.",
                    )
                ],
            )
        ]
    )


def make_agentic_result() -> AgenticTailoringResult:
    rewrite_suggestion = RewriteSuggestion(
        bullet_id="exp_1_bullet_1",
        rewritten_text="Built Python and FastAPI REST APIs.",
        requirement_ids=["req_1"],
    )
    final_result = TailoringResult(
        metadata=TailoringMetadata(
            pipeline_version="v6",
            resume_input_format="structured_text_v1",
        ),
        resume=make_resume(),
        job_analysis=JobAnalysis(
            job_title="Backend Engineer",
            requirements=[
                JobRequirement(
                    id="req_1",
                    text="Build backend APIs using Python.",
                    priority="must_have",
                )
            ],
        ),
        evidence_matches=[
            EvidenceMatch(
                requirement_id="req_1",
                bullet_ids=["exp_1_bullet_1"],
                status="strong",
            )
        ],
        rewrite_suggestions=[rewrite_suggestion],
        validation_issues=[],
        status="success",
    )
    return AgenticTailoringResult(
        metadata=AgenticTailoringMetadata(
            workflow_version=AGENT_WORKFLOW_VERSION,
            pipeline_metadata=final_result.metadata,
            max_attempts=2,
        ),
        final_result=final_result,
        steps=[
            AgentStep(
                step_number=1,
                tool_name="resume_input",
                status="success",
                output_summary="1 experience entries, 1 bullets, 0 skills",
            ),
            AgentStep(
                step_number=2,
                tool_name="validation",
                status="success",
                output_summary="0 validation issues (critical=0, warning=0)",
                attempt_number=1,
            ),
        ],
        attempts=[
            TailoringAttempt(
                attempt_number=1,
                status="accepted",
                rewrite_suggestions=[rewrite_suggestion],
                validation_issues=[],
            )
        ],
        missing_requirement_ids=[],
        accepted_requirement_ids=["req_1"],
        rejected_requirement_ids=[],
        status="success",
    )


def test_tailor_agentic_returns_agentic_result_with_dependency_override(
    client: TestClient,
):
    calls = {}

    def fake_agentic_tailoring_service(
        resume_text: str,
        job_description_text: str,
        max_attempts: int,
    ) -> AgenticTailoringResult:
        calls["resume_text"] = resume_text
        calls["job_description_text"] = job_description_text
        calls["max_attempts"] = max_attempts
        return make_agentic_result()

    app.dependency_overrides[get_agentic_tailoring_service] = lambda: (
        fake_agentic_tailoring_service
    )

    response = client.post(
        "/tailor/agentic",
        json={
            "resume_text": "resume text",
            "job_description_text": "Backend Engineer JD",
            "max_attempts": 2,
        },
    )

    assert response.status_code == 200
    assert calls == {
        "resume_text": "resume text",
        "job_description_text": "Backend Engineer JD",
        "max_attempts": 2,
    }

    payload = response.json()
    assert payload["metadata"]["workflow_version"] == AGENT_WORKFLOW_VERSION
    assert payload["status"] == "success"
    assert [step["tool_name"] for step in payload["steps"]] == [
        "resume_input",
        "validation",
    ]
    assert payload["attempts"][0]["status"] == "accepted"
    assert payload["accepted_requirement_ids"] == ["req_1"]


def test_tailor_agentic_rejects_invalid_max_attempts(client: TestClient):
    response = client.post(
        "/tailor/agentic",
        json={
            "resume_text": "resume text",
            "job_description_text": "Backend Engineer JD",
            "max_attempts": 0,
        },
    )

    assert response.status_code == 422
