import pytest

import app.tailoring as tailoring_module
from app.job_analysis import JobAnalysisOutputError
from app.models import (
    EvidenceMatch,
    JobAnalysis,
    JobRequirement,
    Resume,
    ResumeBullet,
    ResumeExperience,
    RewriteSuggestion,
    ValidationIssue,
)
from app.rewrite_generator import UnsafeRewriteError
from app.tailoring import TailoringResult, tailor_resume_to_job


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
                        text="Built internal REST APIs using Python and FastAPI.",
                    )
                ],
            )
        ]
    )


def fake_resume_parser(resume_text: str) -> Resume:
    assert resume_text == "resume text"
    return make_resume()


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


def fake_rewrite_provider(candidates):
    assert [candidate.bullet_id for candidate in candidates] == ["exp_1_bullet_1"]
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


def test_tailor_resume_to_job_returns_success_result():
    result = tailor_resume_to_job(
        resume_text="resume text",
        jd_text="Backend Engineer JD",
        resume_parser=fake_resume_parser,
        job_analysis_provider=fake_job_analysis_provider,
        rewrite_provider=fake_rewrite_provider,
    )

    assert isinstance(result, TailoringResult)
    assert result.status == "success"
    assert result.validation_issues == []
    assert result.job_analysis.job_title == "Backend Engineer"
    assert [match.status for match in result.evidence_matches] == [
        "strong",
        "strong",
    ]
    assert result.rewrite_suggestions == [
        RewriteSuggestion(
            bullet_id="exp_1_bullet_1",
            rewritten_text="Built Python and FastAPI REST APIs for internal workflows.",
            requirement_ids=["req_1", "req_2"],
        )
    ]


def test_tailor_resume_to_job_returns_completed_with_warnings(monkeypatch):
    warning = ValidationIssue(
        issue_type="missing_evidence",
        severity="warning",
        message="Test warning.",
    )

    monkeypatch.setattr(
        tailoring_module,
        "validate_resume_tailoring",
        lambda **kwargs: [warning],
    )

    result = tailor_resume_to_job(
        resume_text="resume text",
        jd_text="Backend Engineer JD",
        resume_parser=fake_resume_parser,
        job_analysis_provider=fake_job_analysis_provider,
        rewrite_provider=fake_rewrite_provider,
    )

    assert result.status == "completed_with_warnings"
    assert result.validation_issues == [warning]


def test_tailor_resume_to_job_returns_failed_validation_for_unsafe_rewrite(
    monkeypatch,
):
    critical_issue = ValidationIssue(
        issue_type="unsupported_claim",
        severity="critical",
        message="Rewrite targets unsupported requirement.",
    )

    def fake_generate_rewrite_suggestions(**kwargs):
        raise UnsafeRewriteError([critical_issue])

    monkeypatch.setattr(
        tailoring_module,
        "generate_rewrite_suggestions",
        fake_generate_rewrite_suggestions,
    )

    result = tailor_resume_to_job(
        resume_text="resume text",
        jd_text="Backend Engineer JD",
        resume_parser=fake_resume_parser,
        job_analysis_provider=fake_job_analysis_provider,
        rewrite_provider=fake_rewrite_provider,
    )

    assert result.status == "failed_validation"
    assert result.rewrite_suggestions == []
    assert result.validation_issues == [critical_issue]


def test_tailor_resume_to_job_propagates_provider_output_errors():
    def invalid_job_analysis_provider(jd_text: str):
        return {
            "job_title": "Backend Engineer",
            "requirements": [],
        }

    with pytest.raises(JobAnalysisOutputError, match="at least one requirement"):
        tailor_resume_to_job(
            resume_text="resume text",
            jd_text="Backend Engineer JD",
            resume_parser=fake_resume_parser,
            job_analysis_provider=invalid_job_analysis_provider,
            rewrite_provider=fake_rewrite_provider,
        )


def test_tailoring_result_accepts_failed_validation_status():
    result = TailoringResult(
        resume=make_resume(),
        job_analysis=JobAnalysis(
            requirements=[
                JobRequirement(
                    id="req_1",
                    text="Build backend APIs using Python.",
                    priority="must_have",
                )
            ]
        ),
        evidence_matches=[
            EvidenceMatch(
                requirement_id="req_1",
                bullet_ids=["exp_1_bullet_1"],
                status="strong",
            )
        ],
        rewrite_suggestions=[],
        validation_issues=[
            ValidationIssue(
                issue_type="unsupported_claim",
                severity="critical",
                message="Critical issue.",
            )
        ],
        status="failed_validation",
    )

    assert result.status == "failed_validation"
