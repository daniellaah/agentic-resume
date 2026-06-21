from pathlib import Path

from app.models import (
    EvidenceMatch,
    JobAnalysis,
    JobRequirement,
    RewriteSuggestion,
)
from app.parsers import parse_sample_resume
from app.validator import validate_resume_tailoring


ROOT_DIR = Path(__file__).resolve().parents[1]


def make_sample_resume():
    resume_text = (ROOT_DIR / "data" / "sample_resume.txt").read_text()
    return parse_sample_resume(resume_text)



def make_sample_job_analysis() -> JobAnalysis:
    return JobAnalysis(
        job_title="Backend Engineer",
        requirements=[
            JobRequirement(
                id="req_1",
                text="Build backend APIs using Python and FastAPI.",
                priority="must_have",
            ),
            JobRequirement(
                id="req_2",
                text="Work with PostgreSQL-backed application data.",
                priority="must_have",
            ),
            JobRequirement(
                id="req_3",
                text="Write automated tests for backend services.",
                priority="must_have",
            ),
            JobRequirement(
                id="req_4",
                text="Deploy containerized services to Kubernetes.",
                priority="nice_to_have",
            ),
        ],
    )


def make_sample_evidence_matches() -> list[EvidenceMatch]:
    return [
        EvidenceMatch(
            requirement_id="req_1",
            bullet_ids=["exp_1_bullet_1"],
            status="strong",
        ),
        EvidenceMatch(
            requirement_id="req_2",
            bullet_ids=["exp_1_bullet_2"],
            status="strong",
        ),
        EvidenceMatch(
            requirement_id="req_3",
            bullet_ids=["exp_1_bullet_3"],
            status="strong",
        ),
        EvidenceMatch(
            requirement_id="req_4",
            bullet_ids=[],
            status="missing",
        ),
    ]


def make_supported_rewrite_suggestions() -> list[RewriteSuggestion]:
    return [
        RewriteSuggestion(
            bullet_id="exp_1_bullet_1",
            rewritten_text=(
                "Built Python and FastAPI REST APIs for internal analyst "
                "workflows."
            ),
            requirement_ids=["req_1"],
        ),
        RewriteSuggestion(
            bullet_id="exp_1_bullet_2",
            rewritten_text=(
                "Designed PostgreSQL-backed reporting data models and queries "
                "for customer-facing analytics workflows."
            ),
            requirement_ids=["req_2"],
        ),
    ]


def test_sample_files_contain_stable_resume_ids_and_jd_requirements():
    resume_text = (ROOT_DIR / "data" / "sample_resume.txt").read_text()
    jd_text = (ROOT_DIR / "data" / "sample_jd.txt").read_text()

    assert "[exp_1_bullet_1]" in resume_text
    assert "[exp_1_bullet_2]" in resume_text
    assert "[exp_1_bullet_3]" in resume_text
    assert "Deploy containerized services to Kubernetes" in jd_text


def test_v0_flow_accepts_supported_rewrite_suggestions():
    issues = validate_resume_tailoring(
        resume=make_sample_resume(),
        job_analysis=make_sample_job_analysis(),
        evidence_matches=make_sample_evidence_matches(),
        rewrite_suggestions=make_supported_rewrite_suggestions(),
    )

    assert issues == []


def test_v0_flow_rejects_rewrite_targeting_missing_evidence():
    unsupported_rewrite = RewriteSuggestion(
        bullet_id="exp_1_bullet_1",
        rewritten_text="Deployed Python services to Kubernetes for internal teams.",
        requirement_ids=["req_4"],
    )

    issues = validate_resume_tailoring(
        resume=make_sample_resume(),
        job_analysis=make_sample_job_analysis(),
        evidence_matches=make_sample_evidence_matches(),
        rewrite_suggestions=[unsupported_rewrite],
    )

    assert len(issues) == 1
    assert issues[0].issue_type == "unsupported_claim"
    assert issues[0].severity == "critical"
    assert "req_4" in issues[0].message
