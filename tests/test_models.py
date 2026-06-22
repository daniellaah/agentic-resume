import pytest
from pydantic import ValidationError

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


def make_resume_bullet() -> ResumeBullet:
    return ResumeBullet(
        id="exp_1_bullet_1",
        text="Built an internal API using Python and FastAPI.",
    )


def make_job_requirement() -> JobRequirement:
    return JobRequirement(
        id="req_1",
        text="Experience building backend APIs with Python.",
        priority="must_have",
    )


def test_resume_bullet_accepts_valid_data():
    bullet = make_resume_bullet()

    assert bullet.id == "exp_1_bullet_1"
    assert bullet.text == "Built an internal API using Python and FastAPI."


def test_resume_bullet_rejects_empty_id():
    with pytest.raises(ValidationError):
        ResumeBullet(id="", text="Built an internal API using Python and FastAPI.")


def test_resume_bullet_rejects_empty_text():
    with pytest.raises(ValidationError):
        ResumeBullet(id="exp_1_bullet_1", text="")


def test_resume_experience_accepts_valid_data():
    experience = ResumeExperience(
        id="exp_1",
        company="Acme",
        title="Software Engineer",
        start_date="2024-01",
        end_date=None,
        bullets=[make_resume_bullet()],
    )

    assert experience.id == "exp_1"
    assert len(experience.bullets) == 1


def test_resume_experience_rejects_empty_bullets():
    with pytest.raises(ValidationError):
        ResumeExperience(
            id="exp_1",
            company="Acme",
            title="Software Engineer",
            start_date="2024-01",
            bullets=[],
        )


def test_resume_accepts_valid_data():
    resume = Resume(
        summary="Backend engineer focused on Python services.",
        skills=["Python", "FastAPI"],
        experience=[
            ResumeExperience(
                id="exp_1",
                company="Acme",
                title="Software Engineer",
                start_date="2024-01",
                bullets=[make_resume_bullet()],
            )
        ],
    )

    assert resume.skills == ["Python", "FastAPI"]
    assert len(resume.experience) == 1


def test_resume_rejects_empty_experience():
    with pytest.raises(ValidationError):
        Resume(experience=[])


def test_resume_rejects_empty_skill():
    with pytest.raises(ValidationError):
        Resume(
            skills=[""],
            experience=[
                ResumeExperience(
                    id="exp_1",
                    company="Acme",
                    title="Software Engineer",
                    start_date="2024-01",
                    bullets=[make_resume_bullet()],
                )
            ],
        )


def test_job_requirement_accepts_valid_priority():
    requirement = make_job_requirement()

    assert requirement.priority == "must_have"


def test_job_requirement_rejects_invalid_priority():
    with pytest.raises(ValidationError):
        JobRequirement(
            id="req_1",
            text="Experience building backend APIs with Python.",
            priority="required",
        )


def test_job_analysis_accepts_valid_data():
    analysis = JobAnalysis(
        job_title="Backend Engineer",
        requirements=[make_job_requirement()],
    )

    assert analysis.job_title == "Backend Engineer"
    assert len(analysis.requirements) == 1


def test_evidence_match_accepts_missing_without_bullets():
    match = EvidenceMatch(
        requirement_id="req_1",
        status="missing",
    )

    assert match.bullet_ids == []
    assert match.status == "missing"


def test_evidence_match_accepts_valid_bullet_ids():
    match = EvidenceMatch(
        requirement_id="req_1",
        bullet_ids=["exp_1_bullet_1"],
        status="strong",
    )

    assert match.bullet_ids == ["exp_1_bullet_1"]


def test_evidence_match_rejects_empty_requirement_id():
    with pytest.raises(ValidationError):
        EvidenceMatch(
            requirement_id="",
            bullet_ids=["exp_1_bullet_1"],
            status="strong",
        )


def test_evidence_match_rejects_empty_bullet_id():
    with pytest.raises(ValidationError):
        EvidenceMatch(
            requirement_id="req_1",
            bullet_ids=[""],
            status="strong",
        )


def test_evidence_match_rejects_invalid_status():
    with pytest.raises(ValidationError):
        EvidenceMatch(
            requirement_id="req_1",
            bullet_ids=["exp_1_bullet_1"],
            status="matched",
        )


def test_rewrite_suggestion_accepts_valid_data():
    rewritten_text = "Built Python and FastAPI APIs aligned with backend product needs."

    suggestion = RewriteSuggestion(
        bullet_id="exp_1_bullet_1",
        rewritten_text=rewritten_text,
        requirement_ids=["req_1"],
    )

    assert suggestion.bullet_id == "exp_1_bullet_1"
    assert suggestion.requirement_ids == ["req_1"]


def test_rewrite_suggestion_rejects_empty_bullet_id():
    rewritten_text = "Built Python and FastAPI APIs aligned with backend product needs."

    with pytest.raises(ValidationError):
        RewriteSuggestion(
            bullet_id="",
            rewritten_text=rewritten_text,
            requirement_ids=["req_1"],
        )


def test_rewrite_suggestion_rejects_empty_rewritten_text():
    with pytest.raises(ValidationError):
        RewriteSuggestion(
            bullet_id="exp_1_bullet_1",
            rewritten_text="",
            requirement_ids=["req_1"],
        )


def test_rewrite_suggestion_rejects_empty_requirement_ids():
    rewritten_text = "Built Python and FastAPI APIs aligned with backend product needs."

    with pytest.raises(ValidationError):
        RewriteSuggestion(
            bullet_id="exp_1_bullet_1",
            rewritten_text=rewritten_text,
            requirement_ids=[],
        )


def test_rewrite_suggestion_rejects_empty_requirement_id_item():
    rewritten_text = "Built Python and FastAPI APIs aligned with backend product needs."

    with pytest.raises(ValidationError):
        RewriteSuggestion(
            bullet_id="exp_1_bullet_1",
            rewritten_text=rewritten_text,
            requirement_ids=[""],
        )


@pytest.mark.parametrize(
    "issue_type",
    ["unsupported_claim", "changed_fact", "missing_evidence", "formatting"],
)
def test_validation_issue_accepts_valid_issue_types(issue_type: str):
    issue = ValidationIssue(
        issue_type=issue_type,
        severity="critical",
        message="Rewrite suggestion adds unsupported technology.",
    )

    assert issue.issue_type == issue_type


def test_validation_issue_rejects_invalid_issue_type():
    with pytest.raises(ValidationError):
        ValidationIssue(
            issue_type="style",
            severity="warning",
            message="Bullet is too long.",
        )


def test_validation_issue_rejects_invalid_severity():
    with pytest.raises(ValidationError):
        ValidationIssue(
            issue_type="formatting",
            severity="error",
            message="Bullet is too long.",
        )


def test_validation_issue_rejects_empty_message():
    with pytest.raises(ValidationError):
        ValidationIssue(
            issue_type="formatting",
            severity="warning",
            message="",
        )
