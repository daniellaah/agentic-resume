from pathlib import Path

from app.job_analysis import analyze_job_description
from app.models import EvidenceMatch, RewriteSuggestion
from app.parsers import parse_sample_resume
from app.validator import validate_resume_tailoring

ROOT_DIR = Path(__file__).resolve().parents[1]


def fake_job_analysis_provider(jd_text: str):
    assert "Backend Engineer" in jd_text
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
                "text": "Design REST services with FastAPI or similar frameworks.",
                "priority": "must_have",
            },
            {
                "id": "req_3",
                "text": "Work with PostgreSQL-backed application data.",
                "priority": "must_have",
            },
            {
                "id": "req_4",
                "text": "Deploy containerized services to Kubernetes.",
                "priority": "nice_to_have",
            },
        ],
    }


def test_v1_flow_uses_fake_job_analysis_without_network_access():
    resume_text = (ROOT_DIR / "data" / "sample_resume.txt").read_text()
    jd_text = (ROOT_DIR / "data" / "sample_jd.txt").read_text()

    resume = parse_sample_resume(resume_text)
    job_analysis = analyze_job_description(
        jd_text,
        payload_provider=fake_job_analysis_provider,
    )

    issues = validate_resume_tailoring(
        resume=resume,
        job_analysis=job_analysis,
        evidence_matches=[
            EvidenceMatch(
                requirement_id="req_1",
                bullet_ids=["exp_1_bullet_1"],
                status="strong",
            ),
            EvidenceMatch(
                requirement_id="req_2",
                bullet_ids=["exp_1_bullet_1"],
                status="strong",
            ),
            EvidenceMatch(
                requirement_id="req_3",
                bullet_ids=["exp_1_bullet_2"],
                status="strong",
            ),
            EvidenceMatch(
                requirement_id="req_4",
                bullet_ids=[],
                status="missing",
            ),
        ],
        rewrite_suggestions=[
            RewriteSuggestion(
                bullet_id="exp_1_bullet_1",
                rewritten_text=(
                    "Built Python and FastAPI REST APIs for internal analyst workflows."
                ),
                requirement_ids=["req_1", "req_2"],
            ),
            RewriteSuggestion(
                bullet_id="exp_1_bullet_2",
                rewritten_text=(
                    "Designed PostgreSQL-backed reporting data models and "
                    "queries for customer reporting workflows."
                ),
                requirement_ids=["req_3"],
            ),
        ],
    )

    assert issues == []
