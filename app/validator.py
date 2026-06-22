from app.models import (
    EvidenceMatch,
    JobAnalysis,
    Resume,
    RewriteSuggestion,
    ValidationIssue,
)


def validate_resume_tailoring(
    resume: Resume,
    job_analysis: JobAnalysis,
    evidence_matches: list[EvidenceMatch],
    rewrite_suggestions: list[RewriteSuggestion],
) -> list[ValidationIssue]:
    issues = []

    valid_bullets = set()
    for experience in resume.experience:
        valid_bullets.update(bullet.id for bullet in experience.bullets)

    valid_requirements = set()
    for requirement in job_analysis.requirements:
        valid_requirements.add(requirement.id)

    evidence_status_map = {}
    for evidence_match in evidence_matches:
        if evidence_match.requirement_id not in valid_requirements:
            issues.append(
                ValidationIssue(
                    issue_type="missing_evidence",
                    severity="warning",
                    message=(
                        f"Requirement {evidence_match.requirement_id} is "
                        "referenced in an evidence match but not found in the "
                        "job analysis."
                    ),
                )
            )
        else:
            if evidence_match.requirement_id in evidence_status_map:
                issues.append(
                    ValidationIssue(
                        issue_type="missing_evidence",
                        severity="critical",
                        message=(
                            f"Requirement {evidence_match.requirement_id} has "
                            "multiple evidence matches."
                        ),
                    )
                )
            else:
                evidence_status_map[evidence_match.requirement_id] = (
                    evidence_match.status
                )

        if evidence_match.status == "missing" and evidence_match.bullet_ids:
            issues.append(
                ValidationIssue(
                    issue_type="missing_evidence",
                    severity="warning",
                    message="Missing evidence match should not contain bullet IDs.",
                )
            )

        if (
            evidence_match.status in ("strong", "weak")
            and not evidence_match.bullet_ids
        ):
            issues.append(
                ValidationIssue(
                    issue_type="missing_evidence",
                    severity="warning",
                    message=(
                        f"Bullet IDs are required for {evidence_match.status} "
                        "evidence matches."
                    ),
                )
            )

        if evidence_match.bullet_ids:
            for bullet_id in evidence_match.bullet_ids:
                if bullet_id not in valid_bullets:
                    issues.append(
                        ValidationIssue(
                            issue_type="missing_evidence",
                            severity="warning",
                            message=(
                                f"Bullet {bullet_id} is referenced in an evidence "
                                "match but not found in the resume."
                            ),
                        )
                    )

    for rewrite_suggestion in rewrite_suggestions:
        if rewrite_suggestion.bullet_id not in valid_bullets:
            issues.append(
                ValidationIssue(
                    issue_type="missing_evidence",
                    severity="critical",
                    message=(
                        f"Bullet {rewrite_suggestion.bullet_id} is referenced "
                        "in a rewrite suggestion but not found in the resume."
                    ),
                )
            )

        for requirement_id in rewrite_suggestion.requirement_ids:
            if requirement_id not in valid_requirements:
                issues.append(
                    ValidationIssue(
                        issue_type="missing_evidence",
                        severity="critical",
                        message=(
                            f"Requirement {requirement_id} is referenced in a "
                            "rewrite suggestion but not found in the job analysis."
                        ),
                    )
                )
            elif evidence_status_map.get(requirement_id) == "missing":
                issues.append(
                    ValidationIssue(
                        issue_type="unsupported_claim",
                        severity="critical",
                        message=(
                            f"Requirement {requirement_id} is referenced in a "
                            "rewrite suggestion but has missing evidence."
                        ),
                    )
                )
            elif evidence_status_map.get(requirement_id) is None:
                issues.append(
                    ValidationIssue(
                        issue_type="missing_evidence",
                        severity="critical",
                        message=(
                            f"Requirement {requirement_id} is referenced in a "
                            "rewrite suggestion but has no evidence match."
                        ),
                    )
                )

    return issues
