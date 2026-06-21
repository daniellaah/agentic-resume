from pathlib import Path

from app.evidence_matcher import match_evidence
from app.job_analysis import analyze_job_description
from app.models import RewriteSuggestion
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
                "text": "Write automated tests for backend services.",
                "priority": "must_have",
            },
            {
                "id": "req_5",
                "text": "Deploy containerized services to Kubernetes.",
                "priority": "nice_to_have",
            },
        ],
    }


def make_v2_inputs():
    resume_text = (ROOT_DIR / "data" / "sample_resume.txt").read_text()
    jd_text = (ROOT_DIR / "data" / "sample_jd.txt").read_text()

    resume = parse_sample_resume(resume_text)
    job_analysis = analyze_job_description(
        jd_text,
        payload_provider=fake_job_analysis_provider,
    )
    evidence_matches = match_evidence(resume, job_analysis)

    return resume, job_analysis, evidence_matches


def test_v2_flow_accepts_supported_rewrite_suggestions_with_matched_evidence():
    resume, job_analysis, evidence_matches = make_v2_inputs()

    issues = validate_resume_tailoring(
        resume=resume,
        job_analysis=job_analysis,
        evidence_matches=evidence_matches,
        rewrite_suggestions=[
            RewriteSuggestion(
                bullet_id="exp_1_bullet_1",
                rewritten_text=(
                    "Built Python and FastAPI REST APIs for internal analyst "
                    "workflows."
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
            RewriteSuggestion(
                bullet_id="exp_1_bullet_3",
                rewritten_text=(
                    "Added pytest coverage for backend service validation and "
                    "API error handling."
                ),
                requirement_ids=["req_4"],
            ),
        ],
    )

    assert issues == []


def test_v2_flow_rejects_rewrite_targeting_missing_evidence():
    resume, job_analysis, evidence_matches = make_v2_inputs()

    issues = validate_resume_tailoring(
        resume=resume,
        job_analysis=job_analysis,
        evidence_matches=evidence_matches,
        rewrite_suggestions=[
            RewriteSuggestion(
                bullet_id="exp_1_bullet_1",
                rewritten_text="Deployed Python services to Kubernetes.",
                requirement_ids=["req_5"],
            )
        ],
    )

    assert len(issues) == 1
    assert issues[0].issue_type == "unsupported_claim"
    assert issues[0].severity == "critical"
    assert "req_5" in issues[0].message
