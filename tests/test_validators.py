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
from app.validator import validate_resume_tailoring


def make_resume() -> Resume:
    return Resume(
        experience=[
            ResumeExperience(
                id="exp_1",
                company="Acme",
                title="Software Engineer",
                start_date="2024-01",
                bullets=[
                    ResumeBullet(
                        id="exp_1_bullet_1",
                        text="Built backend APIs using Python and FastAPI.",
                    )
                ],
            )
        ]
    )


def make_job_analysis() -> JobAnalysis:
    return JobAnalysis(
        job_title="Backend Engineer",
        requirements=[
            JobRequirement(
                id="req_1",
                text="Experience building backend APIs with Python.",
                priority="must_have",
            ),
            JobRequirement(
                id="req_2",
                text="Experience deploying services on Kubernetes.",
                priority="nice_to_have",
            ),
        ],
    )


def has_issue(
    issues: list[ValidationIssue],
    issue_type: str,
    severity: str,
    message_fragment: str,
) -> bool:
    return any(
        issue.issue_type == issue_type
        and issue.severity == severity
        and message_fragment in issue.message
        for issue in issues
    )


def test_validator_returns_no_issues_for_valid_tailoring():
    issues = validate_resume_tailoring(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
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
                rewritten_text=(
                    "Built Python and FastAPI backend APIs for internal users."
                ),
                requirement_ids=["req_1"],
            )
        ],
    )

    assert issues == []


def test_validator_detects_evidence_match_with_unknown_requirement():
    issues = validate_resume_tailoring(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
        evidence_matches=[
            EvidenceMatch(
                requirement_id="unknown_req",
                bullet_ids=["exp_1_bullet_1"],
                status="strong",
            )
        ],
        rewrite_suggestions=[],
    )

    assert has_issue(
        issues,
        issue_type="missing_evidence",
        severity="warning",
        message_fragment="unknown_req",
    )


def test_validator_detects_duplicate_evidence_matches():
    issues = validate_resume_tailoring(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
        evidence_matches=[
            EvidenceMatch(
                requirement_id="req_1",
                bullet_ids=["exp_1_bullet_1"],
                status="strong",
            ),
            EvidenceMatch(
                requirement_id="req_1",
                bullet_ids=["exp_1_bullet_1"],
                status="weak",
            ),
        ],
        rewrite_suggestions=[],
    )

    assert has_issue(
        issues,
        issue_type="missing_evidence",
        severity="critical",
        message_fragment="multiple evidence matches",
    )


def test_validator_detects_missing_evidence_with_bullet_ids():
    issues = validate_resume_tailoring(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
        evidence_matches=[
            EvidenceMatch(
                requirement_id="req_2",
                bullet_ids=["exp_1_bullet_1"],
                status="missing",
            )
        ],
        rewrite_suggestions=[],
    )

    assert has_issue(
        issues,
        issue_type="missing_evidence",
        severity="warning",
        message_fragment="should not contain bullet IDs",
    )


def test_validator_detects_strong_evidence_without_bullet_ids():
    issues = validate_resume_tailoring(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
        evidence_matches=[
            EvidenceMatch(
                requirement_id="req_1",
                bullet_ids=[],
                status="strong",
            )
        ],
        rewrite_suggestions=[],
    )

    assert has_issue(
        issues,
        issue_type="missing_evidence",
        severity="warning",
        message_fragment="required for strong",
    )


def test_validator_detects_weak_evidence_without_bullet_ids():
    issues = validate_resume_tailoring(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
        evidence_matches=[
            EvidenceMatch(
                requirement_id="req_1",
                bullet_ids=[],
                status="weak",
            )
        ],
        rewrite_suggestions=[],
    )

    assert has_issue(
        issues,
        issue_type="missing_evidence",
        severity="warning",
        message_fragment="required for weak",
    )


def test_validator_detects_evidence_match_with_unknown_bullet():
    issues = validate_resume_tailoring(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
        evidence_matches=[
            EvidenceMatch(
                requirement_id="req_1",
                bullet_ids=["unknown_bullet"],
                status="strong",
            )
        ],
        rewrite_suggestions=[],
    )

    assert has_issue(
        issues,
        issue_type="missing_evidence",
        severity="warning",
        message_fragment="unknown_bullet",
    )


def test_validator_allows_uncertain_evidence_without_bullet_ids():
    issues = validate_resume_tailoring(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
        evidence_matches=[
            EvidenceMatch(
                requirement_id="req_1",
                bullet_ids=[],
                status="uncertain",
            )
        ],
        rewrite_suggestions=[],
    )

    assert issues == []


def test_validator_detects_rewrite_with_unknown_bullet():
    issues = validate_resume_tailoring(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
        evidence_matches=[
            EvidenceMatch(
                requirement_id="req_1",
                bullet_ids=["exp_1_bullet_1"],
                status="strong",
            )
        ],
        rewrite_suggestions=[
            RewriteSuggestion(
                bullet_id="unknown_bullet",
                rewritten_text="Built Python and FastAPI backend APIs.",
                requirement_ids=["req_1"],
            )
        ],
    )

    assert has_issue(
        issues,
        issue_type="missing_evidence",
        severity="critical",
        message_fragment="unknown_bullet",
    )


def test_validator_detects_rewrite_with_unknown_requirement():
    issues = validate_resume_tailoring(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
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
                rewritten_text="Built Python and FastAPI backend APIs.",
                requirement_ids=["unknown_req"],
            )
        ],
    )

    assert has_issue(
        issues,
        issue_type="missing_evidence",
        severity="critical",
        message_fragment="unknown_req",
    )


def test_validator_detects_rewrite_targeting_missing_requirement():
    issues = validate_resume_tailoring(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
        evidence_matches=[
            EvidenceMatch(
                requirement_id="req_2",
                bullet_ids=[],
                status="missing",
            )
        ],
        rewrite_suggestions=[
            RewriteSuggestion(
                bullet_id="exp_1_bullet_1",
                rewritten_text="Deployed services on Kubernetes.",
                requirement_ids=["req_2"],
            )
        ],
    )

    assert has_issue(
        issues,
        issue_type="unsupported_claim",
        severity="critical",
        message_fragment="req_2",
    )


def test_validator_detects_rewrite_targeting_requirement_without_evidence_match():
    issues = validate_resume_tailoring(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
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
                rewritten_text="Deployed services on Kubernetes.",
                requirement_ids=["req_2"],
            )
        ],
    )

    assert has_issue(
        issues,
        issue_type="missing_evidence",
        severity="critical",
        message_fragment="no evidence match",
    )


def test_validator_allows_rewrite_targeting_uncertain_requirement():
    issues = validate_resume_tailoring(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
        evidence_matches=[
            EvidenceMatch(
                requirement_id="req_1",
                bullet_ids=["exp_1_bullet_1"],
                status="uncertain",
            )
        ],
        rewrite_suggestions=[
            RewriteSuggestion(
                bullet_id="exp_1_bullet_1",
                rewritten_text="Built backend APIs using Python and FastAPI.",
                requirement_ids=["req_1"],
            )
        ],
    )

    assert issues == []
