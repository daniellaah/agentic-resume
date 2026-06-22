import pytest
from fastapi.testclient import TestClient

from app.api import app, get_tailoring_service
from app.job_analysis import (
    JobAnalysisOutputError,
)
from app.job_analysis import (
    MissingOpenAIAPIKeyError as MissingJobAnalysisOpenAIAPIKeyError,
)
from app.llm_backend import LLMProviderRequestError
from app.models import (
    EvidenceMatch,
    JobAnalysis,
    JobRequirement,
    Resume,
    ResumeBullet,
    ResumeExperience,
    RewriteSuggestion,
)
from app.resume_input import ResumeInputError
from app.tailoring import (
    DEFAULT_RESUME_INPUT_FORMAT,
    PIPELINE_VERSION,
    TailoringMetadata,
    TailoringResult,
)


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_tailoring_result() -> TailoringResult:
    return TailoringResult(
        metadata=TailoringMetadata(
            pipeline_version=PIPELINE_VERSION,
            resume_input_format=DEFAULT_RESUME_INPUT_FORMAT,
        ),
        resume=Resume(
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
        ),
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
        rewrite_suggestions=[
            RewriteSuggestion(
                bullet_id="exp_1_bullet_1",
                rewritten_text="Built Python REST APIs for backend workflows.",
                requirement_ids=["req_1"],
            )
        ],
        validation_issues=[],
        status="success",
    )


def test_health_returns_ok(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tailor_returns_pipeline_result_with_dependency_override(client: TestClient):
    calls = {}

    def fake_tailoring_service(
        resume_text: str,
        job_description_text: str,
    ) -> TailoringResult:
        calls["resume_text"] = resume_text
        calls["job_description_text"] = job_description_text
        return make_tailoring_result()

    app.dependency_overrides[get_tailoring_service] = lambda: fake_tailoring_service

    response = client.post(
        "/tailor",
        json={
            "resume_text": "resume text",
            "job_description_text": "Backend Engineer JD",
        },
    )

    assert response.status_code == 200
    assert calls == {
        "resume_text": "resume text",
        "job_description_text": "Backend Engineer JD",
    }

    payload = response.json()
    assert payload["metadata"] == {
        "pipeline_version": PIPELINE_VERSION,
        "resume_input_format": DEFAULT_RESUME_INPUT_FORMAT,
    }
    assert payload["status"] == "success"
    assert payload["job_analysis"]["job_title"] == "Backend Engineer"


def test_tailor_rejects_blank_request_fields(client: TestClient):
    response = client.post(
        "/tailor",
        json={
            "resume_text": " ",
            "job_description_text": "Backend Engineer JD",
        },
    )

    assert response.status_code == 422


def test_tailor_maps_application_input_errors_to_400(client: TestClient):
    def fake_tailoring_service(
        resume_text: str,
        job_description_text: str,
    ) -> TailoringResult:
        raise ResumeInputError("Invalid structured resume text.")

    app.dependency_overrides[get_tailoring_service] = lambda: fake_tailoring_service

    response = client.post(
        "/tailor",
        json={
            "resume_text": "resume text",
            "job_description_text": "Backend Engineer JD",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid structured resume text."}


def test_tailor_maps_provider_output_errors_to_400(client: TestClient):
    def fake_tailoring_service(
        resume_text: str,
        job_description_text: str,
    ) -> TailoringResult:
        raise JobAnalysisOutputError("Invalid job analysis output.")

    app.dependency_overrides[get_tailoring_service] = lambda: fake_tailoring_service

    response = client.post(
        "/tailor",
        json={
            "resume_text": "resume text",
            "job_description_text": "Backend Engineer JD",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid job analysis output."}


def test_tailor_maps_missing_openai_api_key_to_503(client: TestClient):
    def fake_tailoring_service(
        resume_text: str,
        job_description_text: str,
    ) -> TailoringResult:
        raise MissingJobAnalysisOpenAIAPIKeyError("OPENAI_API_KEY must be set.")

    app.dependency_overrides[get_tailoring_service] = lambda: fake_tailoring_service

    response = client.post(
        "/tailor",
        json={
            "resume_text": "resume text",
            "job_description_text": "Backend Engineer JD",
        },
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "OPENAI_API_KEY must be set."}


def test_tailor_maps_llm_provider_request_errors_to_503(client: TestClient):
    def fake_tailoring_service(
        resume_text: str,
        job_description_text: str,
    ) -> TailoringResult:
        raise LLMProviderRequestError("Ollama request failed.")

    app.dependency_overrides[get_tailoring_service] = lambda: fake_tailoring_service

    response = client.post(
        "/tailor",
        json={
            "resume_text": "resume text",
            "job_description_text": "Backend Engineer JD",
        },
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Ollama request failed."}
