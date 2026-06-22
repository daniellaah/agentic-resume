from collections import Counter
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, Field

from app.agent_runtime import (
    AgentDecision,
    AgentPlan,
    AgentPlanItem,
    AgentStep,
    AgentTrace,
)
from app.claim_checker import check_rewrite_claims
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

AGENT_WORKFLOW_VERSION = "v20"
DEFAULT_MAX_ATTEMPTS = 2
ORCHESTRATOR_AGENT_NAME = "resume_tailoring_orchestrator_agent"

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
    plan: AgentPlan | None = None
    steps: list[AgentStep] = Field(default_factory=list)
    decisions: list[AgentDecision] = Field(default_factory=list)
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

    trace = _build_tailoring_agent_trace(max_attempts)
    trace.record_decision(
        decision_type="plan",
        reason=(
            "Use the evidence-grounded resume tailoring plan with specialist "
            "agents and critic feedback."
        ),
        next_agent="resume_intake_agent",
    )

    resume = resume_parser(resume_text)
    trace.record_step(
        tool_name="resume_input",
        status="success",
        input_summary=_text_input_summary(resume_text),
        output_summary=_resume_output_summary(resume),
    )

    job_analysis = analyze_job_description(
        jd_text,
        payload_provider=job_analysis_provider,
    )
    trace.record_step(
        tool_name="job_analysis",
        status="success",
        input_summary=_text_input_summary(jd_text),
        output_summary=_job_analysis_output_summary(job_analysis),
    )

    evidence_matches = match_evidence(resume, job_analysis)
    trace.record_step(
        tool_name="evidence_matching",
        status="success",
        input_summary=_evidence_matching_input_summary(resume, job_analysis),
        output_summary=_evidence_matching_output_summary(evidence_matches),
    )

    missing_requirement_ids = _missing_requirement_ids(evidence_matches)
    candidates = build_rewrite_candidates(
        resume=resume,
        job_analysis=job_analysis,
        evidence_matches=evidence_matches,
    )
    trace.record_step(
        tool_name="rewrite_candidate_builder",
        status="success",
        input_summary=_rewrite_candidate_input_summary(evidence_matches),
        output_summary=_rewrite_candidate_output_summary(candidates),
    )

    if not candidates:
        trace.record_step(
            tool_name="rewrite_generation",
            status="skipped",
            output_summary="0 rewrite candidates",
            message="No supported evidence was available for rewrite generation.",
        )
        trace.record_step(
            tool_name="claim_checker",
            status="skipped",
            output_summary="0 claim issues",
            message="No rewrite suggestions were generated.",
        )
        trace.record_step(
            tool_name="validation",
            status="skipped",
            output_summary="0 validation issues",
            message="No rewrite suggestions were generated.",
        )
        trace.record_decision(
            decision_type="skip",
            reason="No supported evidence was available for rewrite generation.",
            next_agent=None,
        )
        final_result = _build_tailoring_result(
            resume=resume,
            job_analysis=job_analysis,
            evidence_matches=evidence_matches,
            rewrite_suggestions=[],
            validation_issues=[],
        )
        return _build_agentic_result(
            final_result=final_result,
            trace=trace,
            attempts=[],
            missing_requirement_ids=missing_requirement_ids,
            status="no_rewrite_candidates",
            max_attempts=max_attempts,
        )

    provider = rewrite_provider or _default_agent_rewrite_provider
    attempts: list[TailoringAttempt] = []
    feedback: list[ValidationIssue] = []

    for attempt_number in range(1, max_attempts + 1):
        attempt_feedback = feedback
        try:
            payload = provider(candidates, attempt_feedback)
            rewrite_suggestions = parse_rewrite_payload(payload)
        except RewriteOutputError as error:
            output_issue = _output_error_to_validation_issue(error)
            trace.record_step(
                tool_name="rewrite_generation",
                status="failed",
                input_summary=_rewrite_generation_input_summary(
                    candidates=candidates,
                    feedback=attempt_feedback,
                ),
                output_summary="0 rewrite suggestions",
                message=str(error),
                attempt_number=attempt_number,
            )
            trace.record_step(
                tool_name="claim_checker",
                status="skipped",
                output_summary="0 claim issues",
                message="Rewrite output could not be parsed.",
                attempt_number=attempt_number,
            )
            trace.record_step(
                tool_name="validation",
                status="skipped",
                output_summary="0 validation issues",
                message="Rewrite output could not be parsed.",
                attempt_number=attempt_number,
            )
            feedback = [output_issue]
            attempts.append(
                TailoringAttempt(
                    attempt_number=attempt_number,
                    status="output_error",
                    validation_issues=feedback,
                    message=str(error),
                )
            )
            trace.record_decision(
                decision_type="retry" if attempt_number < max_attempts else "reject",
                reason="Rewrite output could not be parsed.",
                next_agent="rewrite_agent" if attempt_number < max_attempts else None,
                attempt_number=attempt_number,
                feedback_issue_count=len(feedback),
            )
            continue

        trace.record_step(
            tool_name="rewrite_generation",
            status="success",
            input_summary=_rewrite_generation_input_summary(
                candidates=candidates,
                feedback=attempt_feedback,
            ),
            output_summary=_rewrite_generation_output_summary(rewrite_suggestions),
            attempt_number=attempt_number,
        )

        claim_issues = _check_rewrite_claims_for_suggestions(
            resume=resume,
            rewrite_suggestions=rewrite_suggestions,
        )
        claim_critical_issues = [
            issue for issue in claim_issues if issue.severity == "critical"
        ]
        trace.record_step(
            tool_name="claim_checker",
            status="failed" if claim_critical_issues else "success",
            input_summary=_claim_check_input_summary(rewrite_suggestions),
            output_summary=_claim_check_output_summary(claim_issues),
            attempt_number=attempt_number,
        )

        validation_issues = [
            *_validate_agent_rewrite_attempt(
                resume=resume,
                job_analysis=job_analysis,
                evidence_matches=evidence_matches,
                candidates=candidates,
                rewrite_suggestions=rewrite_suggestions,
            ),
            *claim_issues,
        ]
        critical_issues = [
            issue for issue in validation_issues if issue.severity == "critical"
        ]
        trace.record_step(
            tool_name="validation",
            status="failed" if critical_issues else "success",
            input_summary=_validation_input_summary(rewrite_suggestions),
            output_summary=_validation_output_summary(validation_issues),
            attempt_number=attempt_number,
        )
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
            trace.record_decision(
                decision_type="accept",
                reason="The rewrite attempt passed critic and domain validation.",
                next_agent=None,
                attempt_number=attempt_number,
            )
            final_result = _build_tailoring_result(
                resume=resume,
                job_analysis=job_analysis,
                evidence_matches=evidence_matches,
                rewrite_suggestions=rewrite_suggestions,
                validation_issues=validation_issues,
            )
            return _build_agentic_result(
                final_result=final_result,
                trace=trace,
                attempts=attempts,
                missing_requirement_ids=missing_requirement_ids,
                status="success",
                max_attempts=max_attempts,
            )

        feedback = critical_issues
        trace.record_decision(
            decision_type="retry" if attempt_number < max_attempts else "reject",
            reason="Critical validation issues require another rewrite attempt.",
            next_agent="rewrite_agent" if attempt_number < max_attempts else None,
            attempt_number=attempt_number,
            feedback_issue_count=len(feedback),
        )

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
        trace=trace,
        attempts=attempts,
        missing_requirement_ids=missing_requirement_ids,
        status="failed_validation",
        max_attempts=max_attempts,
    )


def _build_tailoring_agent_trace(max_attempts: int) -> AgentTrace:
    return AgentTrace(plan=_build_tailoring_agent_plan(max_attempts))


def _build_tailoring_agent_plan(max_attempts: int) -> AgentPlan:
    return AgentPlan(
        plan_id="resume_tailoring_v20",
        orchestrator_agent=ORCHESTRATOR_AGENT_NAME,
        objective=(
            "Generate evidence-grounded resume rewrites for a target job "
            "description without introducing unsupported claims."
        ),
        max_iterations=max_attempts,
        items=[
            AgentPlanItem(
                step_id="resume_input",
                agent_name="resume_intake_agent",
                role="specialist",
                tool_name="resume_input",
                objective="Parse raw resume text into the structured Resume model.",
            ),
            AgentPlanItem(
                step_id="job_analysis",
                agent_name="jd_analysis_agent",
                role="specialist",
                tool_name="job_analysis",
                objective=(
                    "Extract normalized job requirements and role metadata from "
                    "the job description."
                ),
                depends_on=["resume_input"],
            ),
            AgentPlanItem(
                step_id="evidence_matching",
                agent_name="evidence_mapper_agent",
                role="specialist",
                tool_name="evidence_matching",
                objective=(
                    "Map job requirements to resume evidence and identify missing "
                    "or weakly supported requirements."
                ),
                depends_on=["resume_input", "job_analysis"],
            ),
            AgentPlanItem(
                step_id="rewrite_candidate_builder",
                agent_name="tailoring_strategy_agent",
                role="specialist",
                tool_name="rewrite_candidate_builder",
                objective=(
                    "Choose evidence-supported bullets and requirements that are "
                    "safe to send to the rewrite agent."
                ),
                depends_on=["evidence_matching"],
            ),
            AgentPlanItem(
                step_id="rewrite_generation",
                agent_name="rewrite_agent",
                role="specialist",
                tool_name="rewrite_generation",
                objective=(
                    "Generate tailored bullet rewrites using candidate evidence "
                    "and critic feedback."
                ),
                depends_on=["rewrite_candidate_builder"],
                repeatable=True,
            ),
            AgentPlanItem(
                step_id="claim_checker",
                agent_name="fact_critic_agent",
                role="critic",
                tool_name="claim_checker",
                objective=(
                    "Reject rewrites that introduce unsupported technology, "
                    "metric, scale, or impact claims."
                ),
                depends_on=["rewrite_generation"],
                repeatable=True,
            ),
            AgentPlanItem(
                step_id="validation",
                agent_name="domain_validator_agent",
                role="critic",
                tool_name="validation",
                objective=(
                    "Validate rewrite structure, requirement coverage, and "
                    "evidence boundaries before acceptance."
                ),
                depends_on=["claim_checker"],
                repeatable=True,
            ),
        ],
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


def _check_rewrite_claims_for_suggestions(
    resume: Resume,
    rewrite_suggestions: list[RewriteSuggestion],
) -> list[ValidationIssue]:
    bullet_text_by_id = _bullet_text_by_id(resume)
    issues: list[ValidationIssue] = []

    for suggestion in rewrite_suggestions:
        source_text = bullet_text_by_id.get(suggestion.bullet_id)
        if source_text is None:
            continue
        issues.extend(
            check_rewrite_claims(
                source_text=source_text,
                rewritten_text=suggestion.rewritten_text,
            )
        )

    return issues


def _bullet_text_by_id(resume: Resume) -> dict[str, str]:
    return {
        bullet.id: bullet.text
        for experience in resume.experience
        for bullet in experience.bullets
    }


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
    trace: AgentTrace,
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
        plan=trace.plan,
        steps=trace.steps,
        decisions=trace.decisions,
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


def _text_input_summary(text: str) -> str:
    return f"{len(text.strip())} characters"


def _resume_output_summary(resume: Resume) -> str:
    return (
        f"{len(resume.experience)} experience entries, "
        f"{_resume_bullet_count(resume)} bullets, "
        f"{len(resume.skills)} skills"
    )


def _resume_bullet_count(resume: Resume) -> int:
    return sum(len(experience.bullets) for experience in resume.experience)


def _job_analysis_output_summary(job_analysis: JobAnalysis) -> str:
    title = job_analysis.job_title or "untitled role"
    return f"{len(job_analysis.requirements)} requirements for {title}"


def _evidence_matching_input_summary(
    resume: Resume,
    job_analysis: JobAnalysis,
) -> str:
    return (
        f"{_resume_bullet_count(resume)} bullets against "
        f"{len(job_analysis.requirements)} requirements"
    )


def _evidence_matching_output_summary(
    evidence_matches: list[EvidenceMatch],
) -> str:
    status_counts = Counter(match.status for match in evidence_matches)
    return (
        f"{len(evidence_matches)} matches "
        f"(strong={status_counts['strong']}, "
        f"weak={status_counts['weak']}, "
        f"missing={status_counts['missing']}, "
        f"uncertain={status_counts['uncertain']})"
    )


def _rewrite_candidate_input_summary(
    evidence_matches: list[EvidenceMatch],
) -> str:
    eligible_match_count = sum(
        1 for match in evidence_matches if match.status in ("strong", "weak")
    )
    return f"{eligible_match_count} evidence matches eligible for rewrite"


def _rewrite_candidate_output_summary(
    candidates: list[RewriteCandidate],
) -> str:
    requirement_count = sum(len(candidate.requirements) for candidate in candidates)
    return f"{len(candidates)} candidates covering {requirement_count} requirements"


def _rewrite_generation_input_summary(
    candidates: list[RewriteCandidate],
    feedback: list[ValidationIssue],
) -> str:
    return (
        f"{len(candidates)} candidates with {len(feedback)} validation feedback issues"
    )


def _rewrite_generation_output_summary(
    rewrite_suggestions: list[RewriteSuggestion],
) -> str:
    requirement_count = len(_requirement_ids_from_suggestions(rewrite_suggestions))
    return (
        f"{len(rewrite_suggestions)} rewrite suggestions covering "
        f"{requirement_count} requirements"
    )


def _claim_check_input_summary(
    rewrite_suggestions: list[RewriteSuggestion],
) -> str:
    return f"{len(rewrite_suggestions)} rewrite suggestions"


def _claim_check_output_summary(
    claim_issues: list[ValidationIssue],
) -> str:
    return f"{len(claim_issues)} claim issues"


def _validation_input_summary(
    rewrite_suggestions: list[RewriteSuggestion],
) -> str:
    return f"{len(rewrite_suggestions)} rewrite suggestions"


def _validation_output_summary(
    validation_issues: list[ValidationIssue],
) -> str:
    severity_counts = Counter(issue.severity for issue in validation_issues)
    return (
        f"{len(validation_issues)} validation issues "
        f"(critical={severity_counts['critical']}, "
        f"warning={severity_counts['warning']})"
    )
