from collections import Counter
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, Field

from app.evidence_matcher import match_evidence
from app.job_analysis import JobAnalysisPayloadProvider, analyze_job_description
from app.models import (
    EvidenceMatch,
    JobAnalysis,
    Resume,
    RewriteSuggestion,
    ValidationIssue,
)
from app.resume_input import parse_resume_text
from app.rewrite_generator import (
    RewriteCandidate,
    RewriteOutputError,
    RewritePayload,
    build_rewrite_candidates,
    call_llm_for_rewrite_suggestions,
    parse_rewrite_payload,
)
from app.tailoring import (
    TailoringMetadata,
    TailoringResult,
    TailoringStatus,
    build_tailoring_metadata,
)
from app.validator import validate_resume_tailoring

AGENT_WORKFLOW_VERSION = "v8"
DEFAULT_MAX_ATTEMPTS = 2

AgentAttemptStatus = Literal["accepted", "rejected", "output_error"]
AgenticTailoringStatus = Literal[
    "success",
    "failed_validation",
    "no_rewrite_candidates",
]
ResumeParser = Callable[[str], Resume]
AgentRewritePayloadProvider = Callable[
    [list[RewriteCandidate], list[ValidationIssue]],
    RewritePayload,
]


class AgenticTailoringMetadata(BaseModel):
    workflow_version: str
    pipeline_metadata: TailoringMetadata
    max_attempts: int


class TailoringAttempt(BaseModel):
    attempt_number: int = Field(ge=1)
    status: AgentAttemptStatus
    rewrite_suggestions: list[RewriteSuggestion] = Field(default_factory=list)
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    message: str | None = None


class AgenticTailoringResult(BaseModel):
    metadata: AgenticTailoringMetadata
    final_result: TailoringResult
    attempts: list[TailoringAttempt] = Field(default_factory=list)
    missing_requirement_ids: list[str] = Field(default_factory=list)
    accepted_requirement_ids: list[str] = Field(default_factory=list)
    rejected_requirement_ids: list[str] = Field(default_factory=list)
    status: AgenticTailoringStatus


def tailor_resume_to_job_agentic(
    resume_text: str,
    jd_text: str,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    resume_parser: ResumeParser = parse_resume_text,
    job_analysis_provider: JobAnalysisPayloadProvider | None = None,
    rewrite_provider: AgentRewritePayloadProvider | None = None,
) -> AgenticTailoringResult:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1.")

    resume = resume_parser(resume_text)
    job_analysis = analyze_job_description(
        jd_text,
        payload_provider=job_analysis_provider,
    )
    evidence_matches = match_evidence(resume, job_analysis)
    missing_requirement_ids = _missing_requirement_ids(evidence_matches)
    candidates = build_rewrite_candidates(
        resume=resume,
        job_analysis=job_analysis,
        evidence_matches=evidence_matches,
    )

    if not candidates:
        final_result = _build_tailoring_result(
            resume=resume,
            job_analysis=job_analysis,
            evidence_matches=evidence_matches,
            rewrite_suggestions=[],
            validation_issues=[],
        )
        return _build_agentic_result(
            final_result=final_result,
            attempts=[],
            missing_requirement_ids=missing_requirement_ids,
            status="no_rewrite_candidates",
            max_attempts=max_attempts,
        )

    provider = rewrite_provider or _default_agent_rewrite_provider
    attempts: list[TailoringAttempt] = []
    feedback: list[ValidationIssue] = []

    for attempt_number in range(1, max_attempts + 1):
        try:
            payload = provider(candidates, feedback)
            rewrite_suggestions = parse_rewrite_payload(payload)
        except RewriteOutputError as error:
            output_issue = _output_error_to_validation_issue(error)
            feedback = [output_issue]
            attempts.append(
                TailoringAttempt(
                    attempt_number=attempt_number,
                    status="output_error",
                    validation_issues=feedback,
                    message=str(error),
                )
            )
            continue

        validation_issues = _validate_agent_rewrite_attempt(
            resume=resume,
            job_analysis=job_analysis,
            evidence_matches=evidence_matches,
            candidates=candidates,
            rewrite_suggestions=rewrite_suggestions,
        )
        critical_issues = [
            issue for issue in validation_issues if issue.severity == "critical"
        ]
        attempt_status: AgentAttemptStatus = (
            "rejected" if critical_issues else "accepted"
        )
        attempts.append(
            TailoringAttempt(
                attempt_number=attempt_number,
                status=attempt_status,
                rewrite_suggestions=rewrite_suggestions,
                validation_issues=validation_issues,
            )
        )

        if not critical_issues:
            final_result = _build_tailoring_result(
                resume=resume,
                job_analysis=job_analysis,
                evidence_matches=evidence_matches,
                rewrite_suggestions=rewrite_suggestions,
                validation_issues=validation_issues,
            )
            return _build_agentic_result(
                final_result=final_result,
                attempts=attempts,
                missing_requirement_ids=missing_requirement_ids,
                status="success",
                max_attempts=max_attempts,
            )

        feedback = critical_issues

    last_attempt = attempts[-1]
    final_result = _build_tailoring_result(
        resume=resume,
        job_analysis=job_analysis,
        evidence_matches=evidence_matches,
        rewrite_suggestions=[],
        validation_issues=last_attempt.validation_issues,
    )
    return _build_agentic_result(
        final_result=final_result,
        attempts=attempts,
        missing_requirement_ids=missing_requirement_ids,
        status="failed_validation",
        max_attempts=max_attempts,
    )


def _default_agent_rewrite_provider(
    candidates: list[RewriteCandidate],
    feedback: list[ValidationIssue],
) -> RewritePayload:
    return call_llm_for_rewrite_suggestions(
        candidates,
        validation_feedback=feedback,
    )


def _validate_agent_rewrite_attempt(
    resume: Resume,
    job_analysis: JobAnalysis,
    evidence_matches: list[EvidenceMatch],
    candidates: list[RewriteCandidate],
    rewrite_suggestions: list[RewriteSuggestion],
) -> list[ValidationIssue]:
    issues = validate_resume_tailoring(
        resume=resume,
        job_analysis=job_analysis,
        evidence_matches=evidence_matches,
        rewrite_suggestions=rewrite_suggestions,
    )
    issues.extend(
        _validate_rewrite_suggestions_against_candidates(
            suggestions=rewrite_suggestions,
            candidates=candidates,
        )
    )
    return issues


def _validate_rewrite_suggestions_against_candidates(
    suggestions: list[RewriteSuggestion],
    candidates: list[RewriteCandidate],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    allowed_requirement_ids_by_bullet_id = {
        candidate.bullet_id: {requirement.id for requirement in candidate.requirements}
        for candidate in candidates
    }
    expected_bullet_ids = set(allowed_requirement_ids_by_bullet_id)
    actual_bullet_ids = {suggestion.bullet_id for suggestion in suggestions}

    if actual_bullet_ids != expected_bullet_ids:
        issues.append(
            ValidationIssue(
                issue_type="formatting",
                severity="critical",
                message=(
                    "Rewrite output must include exactly one suggestion for each "
                    "candidate."
                ),
            )
        )

    duplicate_bullet_ids = [
        bullet_id
        for bullet_id, count in Counter(
            suggestion.bullet_id for suggestion in suggestions
        ).items()
        if count > 1
    ]
    if duplicate_bullet_ids:
        issues.append(
            ValidationIssue(
                issue_type="formatting",
                severity="critical",
                message=(
                    "Rewrite output must not include duplicate suggestions for a "
                    "bullet."
                ),
            )
        )

    for suggestion in suggestions:
        allowed_requirement_ids = allowed_requirement_ids_by_bullet_id.get(
            suggestion.bullet_id,
            set(),
        )
        unexpected_requirement_ids = [
            requirement_id
            for requirement_id in suggestion.requirement_ids
            if requirement_id not in allowed_requirement_ids
        ]
        if unexpected_requirement_ids:
            issues.append(
                ValidationIssue(
                    issue_type="unsupported_claim",
                    severity="critical",
                    message=(
                        f"Bullet {suggestion.bullet_id} targets requirements "
                        "outside its evidence candidate."
                    ),
                )
            )

    return issues


def _output_error_to_validation_issue(error: RewriteOutputError) -> ValidationIssue:
    return ValidationIssue(
        issue_type="formatting",
        severity="critical",
        message=str(error),
    )


def _build_tailoring_result(
    resume: Resume,
    job_analysis: JobAnalysis,
    evidence_matches: list[EvidenceMatch],
    rewrite_suggestions: list[RewriteSuggestion],
    validation_issues: list[ValidationIssue],
) -> TailoringResult:
    return TailoringResult(
        metadata=build_tailoring_metadata(),
        resume=resume,
        job_analysis=job_analysis,
        evidence_matches=evidence_matches,
        rewrite_suggestions=rewrite_suggestions,
        validation_issues=validation_issues,
        status=_tailoring_status_for_issues(validation_issues),
    )


def _tailoring_status_for_issues(
    validation_issues: list[ValidationIssue],
) -> TailoringStatus:
    if any(issue.severity == "critical" for issue in validation_issues):
        return "failed_validation"
    if validation_issues:
        return "completed_with_warnings"
    return "success"


def _build_agentic_result(
    final_result: TailoringResult,
    attempts: list[TailoringAttempt],
    missing_requirement_ids: list[str],
    status: AgenticTailoringStatus,
    max_attempts: int,
) -> AgenticTailoringResult:
    accepted_requirement_ids = _requirement_ids_from_suggestions(
        final_result.rewrite_suggestions
    )
    rejected_requirement_ids = sorted(
        {
            requirement_id
            for attempt in attempts
            if attempt.status in ("rejected", "output_error")
            for requirement_id in _requirement_ids_from_suggestions(
                attempt.rewrite_suggestions
            )
            if requirement_id not in accepted_requirement_ids
        }
    )

    return AgenticTailoringResult(
        metadata=AgenticTailoringMetadata(
            workflow_version=AGENT_WORKFLOW_VERSION,
            pipeline_metadata=final_result.metadata,
            max_attempts=max_attempts,
        ),
        final_result=final_result,
        attempts=attempts,
        missing_requirement_ids=missing_requirement_ids,
        accepted_requirement_ids=accepted_requirement_ids,
        rejected_requirement_ids=rejected_requirement_ids,
        status=status,
    )


def _missing_requirement_ids(evidence_matches: list[EvidenceMatch]) -> list[str]:
    return [
        evidence_match.requirement_id
        for evidence_match in evidence_matches
        if evidence_match.status == "missing"
    ]


def _requirement_ids_from_suggestions(
    suggestions: list[RewriteSuggestion],
) -> list[str]:
    return sorted(
        {
            requirement_id
            for suggestion in suggestions
            for requirement_id in suggestion.requirement_ids
        }
    )
