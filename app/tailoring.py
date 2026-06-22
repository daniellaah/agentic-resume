from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel

from app.evidence_matcher import match_evidence
from app.job_analysis import JobAnalysisPayloadProvider, analyze_job_description
from app.models import (
    EvidenceMatch,
    JobAnalysis,
    Resume,
    RewriteSuggestion,
    ValidationIssue,
)
from app.parsers import parse_sample_resume
from app.rewrite_generator import (
    RewritePayloadProvider,
    UnsafeRewriteError,
    generate_rewrite_suggestions,
)
from app.validator import validate_resume_tailoring

TailoringStatus = Literal["success", "completed_with_warnings", "failed_validation"]
ResumeParser = Callable[[str], Resume]


class TailoringResult(BaseModel):
    resume: Resume
    job_analysis: JobAnalysis
    evidence_matches: list[EvidenceMatch]
    rewrite_suggestions: list[RewriteSuggestion]
    validation_issues: list[ValidationIssue]
    status: TailoringStatus


def tailor_resume_to_job(
    resume_text: str,
    jd_text: str,
    *,
    resume_parser: ResumeParser = parse_sample_resume,
    job_analysis_provider: JobAnalysisPayloadProvider | None = None,
    rewrite_provider: RewritePayloadProvider | None = None,
) -> TailoringResult:
    resume = resume_parser(resume_text)
    job_analysis = analyze_job_description(
        jd_text,
        payload_provider=job_analysis_provider,
    )
    evidence_matches = match_evidence(resume, job_analysis)

    try:
        rewrite_suggestions = generate_rewrite_suggestions(
            resume=resume,
            job_analysis=job_analysis,
            evidence_matches=evidence_matches,
            payload_provider=rewrite_provider,
        )
    except UnsafeRewriteError as error:
        return TailoringResult(
            resume=resume,
            job_analysis=job_analysis,
            evidence_matches=evidence_matches,
            rewrite_suggestions=[],
            validation_issues=error.issues,
            status="failed_validation",
        )

    validation_issues = validate_resume_tailoring(
        resume=resume,
        job_analysis=job_analysis,
        evidence_matches=evidence_matches,
        rewrite_suggestions=rewrite_suggestions,
    )

    return TailoringResult(
        resume=resume,
        job_analysis=job_analysis,
        evidence_matches=evidence_matches,
        rewrite_suggestions=rewrite_suggestions,
        validation_issues=validation_issues,
        status=_status_for_validation_issues(validation_issues),
    )


def _status_for_validation_issues(
    validation_issues: list[ValidationIssue],
) -> TailoringStatus:
    if any(issue.severity == "critical" for issue in validation_issues):
        return "failed_validation"
    if validation_issues:
        return "completed_with_warnings"
    return "success"
