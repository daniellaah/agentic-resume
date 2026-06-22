import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

from app.job_analysis import DEFAULT_OPENAI_MODEL, OPENAI_API_KEY_ENV, OPENAI_MODEL_ENV
from app.models import (
    EvidenceMatch,
    JobAnalysis,
    JobRequirement,
    Resume,
    ResumeBullet,
    RewriteSuggestion,
    ValidationIssue,
)
from app.validator import validate_resume_tailoring

REWRITE_SYSTEM_PROMPT = """
You generate evidence-grounded resume rewrite suggestions.
Rewrite each provided source bullet to better align with the provided job
requirements.
Use only facts present in the source bullet.
Do not add employers, titles, dates, metrics, team sizes, business impact, or
technologies not present in the source bullet.
Return exactly one RewriteSuggestion for each candidate.
Each suggestion must use the candidate bullet_id and only that candidate's
requirement_ids.
Do not include commentary, scores, or final resume sections.
""".strip()

ELIGIBLE_EVIDENCE_STATUSES = {"strong", "weak"}

RewritePayload = Mapping[str, Any]


@dataclass(frozen=True)
class RewriteTargetRequirement:
    id: str
    text: str


@dataclass(frozen=True)
class RewriteCandidate:
    bullet_id: str
    bullet_text: str
    requirements: tuple[RewriteTargetRequirement, ...]


RewritePayloadProvider = Callable[[list[RewriteCandidate]], RewritePayload]


class RewriteSuggestionBatch(BaseModel):
    suggestions: list[RewriteSuggestion] = Field(default_factory=list)


class RewriteGenerationError(Exception):
    """Base error for rewrite generation failures."""


class RewriteOutputError(RewriteGenerationError, ValueError):
    """Raised when provider output cannot be used as rewrite suggestions."""


class UnsafeRewriteError(RewriteGenerationError, ValueError):
    """Raised when generated rewrite suggestions fail validation."""

    def __init__(self, issues: list[ValidationIssue]):
        self.issues = issues
        super().__init__(_format_critical_issues(issues))


class MissingOpenAIAPIKeyError(RewriteGenerationError, RuntimeError):
    """Raised when the OpenAI provider is used without an API key."""


def generate_rewrite_suggestions(
    resume: Resume,
    job_analysis: JobAnalysis,
    evidence_matches: list[EvidenceMatch],
    payload_provider: RewritePayloadProvider | None = None,
) -> list[RewriteSuggestion]:
    candidates = build_rewrite_candidates(
        resume=resume,
        job_analysis=job_analysis,
        evidence_matches=evidence_matches,
    )
    if not candidates:
        return []

    provider = payload_provider or _call_llm_for_rewrite_suggestions
    payload = provider(candidates)
    suggestions = parse_rewrite_payload(payload)
    _validate_suggestions_against_candidates(
        suggestions=suggestions,
        candidates=candidates,
    )
    _validate_suggestions_with_tailoring_validator(
        resume=resume,
        job_analysis=job_analysis,
        evidence_matches=evidence_matches,
        suggestions=suggestions,
    )

    return suggestions


def build_rewrite_candidates(
    resume: Resume,
    job_analysis: JobAnalysis,
    evidence_matches: list[EvidenceMatch],
) -> list[RewriteCandidate]:
    bullets = _bullet_by_id(resume)
    requirements = _requirement_by_id(job_analysis)
    requirement_ids_by_bullet_id: dict[str, list[str]] = {}

    for evidence_match in evidence_matches:
        if evidence_match.status not in ELIGIBLE_EVIDENCE_STATUSES:
            continue
        if evidence_match.requirement_id not in requirements:
            continue

        for bullet_id in evidence_match.bullet_ids:
            if bullet_id not in bullets:
                continue
            requirement_ids_by_bullet_id.setdefault(bullet_id, [])
            if (
                evidence_match.requirement_id
                not in requirement_ids_by_bullet_id[bullet_id]
            ):
                requirement_ids_by_bullet_id[bullet_id].append(
                    evidence_match.requirement_id
                )

    candidates: list[RewriteCandidate] = []
    for bullet_id, bullet in bullets.items():
        requirement_ids = requirement_ids_by_bullet_id.get(bullet_id, [])
        if not requirement_ids:
            continue

        candidates.append(
            RewriteCandidate(
                bullet_id=bullet_id,
                bullet_text=bullet.text,
                requirements=tuple(
                    RewriteTargetRequirement(
                        id=requirement_id,
                        text=requirements[requirement_id].text,
                    )
                    for requirement_id in requirement_ids
                ),
            )
        )

    return candidates


def parse_rewrite_payload(payload: RewritePayload) -> list[RewriteSuggestion]:
    try:
        batch = RewriteSuggestionBatch.model_validate(payload)
    except ValidationError as error:
        raise RewriteOutputError(
            "Rewrite output did not match the RewriteSuggestionBatch schema."
        ) from error

    if not batch.suggestions:
        raise RewriteOutputError("Rewrite output must include at least one suggestion.")

    return batch.suggestions


def _bullet_by_id(resume: Resume) -> dict[str, ResumeBullet]:
    return {
        bullet.id: bullet
        for experience in resume.experience
        for bullet in experience.bullets
    }


def _requirement_by_id(job_analysis: JobAnalysis) -> dict[str, JobRequirement]:
    return {requirement.id: requirement for requirement in job_analysis.requirements}


def _validate_suggestions_against_candidates(
    suggestions: list[RewriteSuggestion],
    candidates: list[RewriteCandidate],
) -> None:
    allowed_requirement_ids_by_bullet_id = {
        candidate.bullet_id: {requirement.id for requirement in candidate.requirements}
        for candidate in candidates
    }
    expected_bullet_ids = set(allowed_requirement_ids_by_bullet_id)
    actual_bullet_ids = {suggestion.bullet_id for suggestion in suggestions}

    if actual_bullet_ids != expected_bullet_ids:
        raise RewriteOutputError(
            "Rewrite output must include exactly one suggestion for each candidate."
        )

    if len(actual_bullet_ids) != len(suggestions):
        raise RewriteOutputError(
            "Rewrite output must not include duplicate suggestions for a bullet."
        )

    for suggestion in suggestions:
        allowed_requirement_ids = allowed_requirement_ids_by_bullet_id[
            suggestion.bullet_id
        ]
        unexpected_requirement_ids = [
            requirement_id
            for requirement_id in suggestion.requirement_ids
            if requirement_id not in allowed_requirement_ids
        ]

        if unexpected_requirement_ids:
            raise RewriteOutputError(
                "Rewrite suggestion targets requirements outside its evidence "
                "candidate."
            )


def _validate_suggestions_with_tailoring_validator(
    resume: Resume,
    job_analysis: JobAnalysis,
    evidence_matches: list[EvidenceMatch],
    suggestions: list[RewriteSuggestion],
) -> None:
    issues = validate_resume_tailoring(
        resume=resume,
        job_analysis=job_analysis,
        evidence_matches=evidence_matches,
        rewrite_suggestions=suggestions,
    )
    critical_issues = [issue for issue in issues if issue.severity == "critical"]

    if critical_issues:
        raise UnsafeRewriteError(critical_issues)


def _format_critical_issues(issues: list[ValidationIssue]) -> str:
    return "; ".join(issue.message for issue in issues)


def _call_llm_for_rewrite_suggestions(
    candidates: list[RewriteCandidate],
) -> RewritePayload:
    api_key = _get_openai_api_key()
    client = OpenAI(api_key=api_key)

    response = client.responses.parse(
        model=_get_openai_model(),
        input=[
            {
                "role": "system",
                "content": REWRITE_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "candidates": [
                            _candidate_to_payload(candidate) for candidate in candidates
                        ]
                    },
                    indent=2,
                ),
            },
        ],
        text_format=RewriteSuggestionBatch,
    )

    batch = response.output_parsed
    if batch is None:
        raise RewriteOutputError(
            "OpenAI response did not include parsed rewrite suggestions."
        )

    return batch.model_dump()


def _candidate_to_payload(candidate: RewriteCandidate) -> dict[str, Any]:
    return {
        "bullet_id": candidate.bullet_id,
        "source_bullet": candidate.bullet_text,
        "requirements": [
            {
                "id": requirement.id,
                "text": requirement.text,
            }
            for requirement in candidate.requirements
        ],
    }


def _get_openai_api_key() -> str:
    import os

    api_key = os.environ.get(OPENAI_API_KEY_ENV)
    if not api_key:
        raise MissingOpenAIAPIKeyError(
            f"{OPENAI_API_KEY_ENV} must be set to generate rewrite suggestions."
        )

    return api_key


def _get_openai_model() -> str:
    import os

    return os.environ.get(OPENAI_MODEL_ENV, DEFAULT_OPENAI_MODEL)
