from collections.abc import Callable, Mapping
from typing import Any

from pydantic import ValidationError

from app.llm_backend import (
    LLMProviderOutputError,
    MissingOpenAIAPIKeyError,
    call_structured_llm,
)
from app.models import JobAnalysis

JOB_ANALYSIS_SYSTEM_PROMPT = """
You analyze software engineering job descriptions.
Extract only concrete job requirements.
Return a JobAnalysis object.
Use deterministic requirement IDs: req_1, req_2, req_3, ...
Set priority to either must_have or nice_to_have.
Do not include resume rewrites, resume evidence, scores, or commentary.
""".strip()

JobAnalysisPayload = Mapping[str, Any]
JobAnalysisPayloadProvider = Callable[[str], JobAnalysisPayload]

__all__ = [
    "EmptyJobDescriptionError",
    "JobAnalysisOutputError",
    "MissingOpenAIAPIKeyError",
    "analyze_job_description",
    "parse_job_analysis_payload",
]


class JobAnalysisError(Exception):
    """Base error for job description analysis failures."""


class EmptyJobDescriptionError(JobAnalysisError, ValueError):
    """Raised when the input job description is empty."""


class JobAnalysisOutputError(JobAnalysisError, ValueError):
    """Raised when provider output cannot be used as JobAnalysis."""


def analyze_job_description(
    jd_text: str,
    payload_provider: JobAnalysisPayloadProvider | None = None,
) -> JobAnalysis:
    cleaned_jd_text = jd_text.strip()
    if not cleaned_jd_text:
        raise EmptyJobDescriptionError("Job description text must not be empty.")

    provider = payload_provider or _call_llm_for_job_analysis
    payload = provider(cleaned_jd_text)
    return parse_job_analysis_payload(payload)


def parse_job_analysis_payload(payload: JobAnalysisPayload) -> JobAnalysis:
    try:
        analysis = JobAnalysis.model_validate(payload)
    except ValidationError as error:
        raise JobAnalysisOutputError(
            "Job analysis output did not match the JobAnalysis schema."
        ) from error

    if not analysis.requirements:
        raise JobAnalysisOutputError(
            "Job analysis output must include at least one requirement."
        )

    _validate_requirement_ids(analysis)
    return analysis


def _validate_requirement_ids(analysis: JobAnalysis) -> None:
    actual_ids = [requirement.id for requirement in analysis.requirements]
    expected_ids = [
        f"req_{index}" for index in range(1, len(analysis.requirements) + 1)
    ]

    if actual_ids != expected_ids:
        raise JobAnalysisOutputError(
            "Job analysis requirement IDs must be deterministic: req_1, req_2, ..."
        )


def _call_llm_for_job_analysis(jd_text: str) -> JobAnalysisPayload:
    try:
        return call_structured_llm(
            system_prompt=JOB_ANALYSIS_SYSTEM_PROMPT,
            user_content=jd_text,
            response_model=JobAnalysis,
        )
    except LLMProviderOutputError as error:
        raise JobAnalysisOutputError(str(error)) from error
