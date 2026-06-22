from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.job_analysis import (
    EmptyJobDescriptionError,
    JobAnalysisOutputError,
)
from app.job_analysis import (
    MissingOpenAIAPIKeyError as MissingJobAnalysisOpenAIAPIKeyError,
)
from app.resume_input import ResumeInputError
from app.rewrite_generator import (
    MissingOpenAIAPIKeyError as MissingRewriteOpenAIAPIKeyError,
)
from app.rewrite_generator import (
    RewriteOutputError,
)
from app.tailoring import TailoringResult, tailor_resume_to_job
from app.tailoring_agent import AgenticTailoringResult, tailor_resume_to_job_agentic

TailoringService = Callable[[str, str], TailoringResult]
AgenticTailoringService = Callable[[str, str, int], AgenticTailoringResult]


class HealthResponse(BaseModel):
    status: str


class TailorRequest(BaseModel):
    resume_text: str = Field(min_length=1)
    job_description_text: str = Field(min_length=1)

    @field_validator("resume_text", "job_description_text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text fields must not be blank.")
        return value


class AgenticTailorRequest(TailorRequest):
    max_attempts: int = Field(default=2, ge=1, le=3)


app = FastAPI(
    title="Agentic Resume API",
    version="0.1.0",
)


def default_tailoring_service(
    resume_text: str,
    job_description_text: str,
) -> TailoringResult:
    return tailor_resume_to_job(
        resume_text=resume_text,
        jd_text=job_description_text,
    )


def get_tailoring_service() -> TailoringService:
    return default_tailoring_service


def default_agentic_tailoring_service(
    resume_text: str,
    job_description_text: str,
    max_attempts: int,
) -> AgenticTailoringResult:
    return tailor_resume_to_job_agentic(
        resume_text=resume_text,
        jd_text=job_description_text,
        max_attempts=max_attempts,
    )


def get_agentic_tailoring_service() -> AgenticTailoringService:
    return default_agentic_tailoring_service


TAILORING_SERVICE_DEPENDENCY = Depends(get_tailoring_service)
AGENTIC_TAILORING_SERVICE_DEPENDENCY = Depends(get_agentic_tailoring_service)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/tailor", response_model=TailoringResult)
def tailor(
    request: TailorRequest,
    tailoring_service: TailoringService = TAILORING_SERVICE_DEPENDENCY,
) -> TailoringResult:
    try:
        return tailoring_service(
            request.resume_text,
            request.job_description_text,
        )
    except (
        MissingJobAnalysisOpenAIAPIKeyError,
        MissingRewriteOpenAIAPIKeyError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except (
        ResumeInputError,
        EmptyJobDescriptionError,
        JobAnalysisOutputError,
        RewriteOutputError,
        ValueError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@app.post("/tailor/agentic", response_model=AgenticTailoringResult)
def tailor_agentic(
    request: AgenticTailorRequest,
    tailoring_service: AgenticTailoringService = AGENTIC_TAILORING_SERVICE_DEPENDENCY,
) -> AgenticTailoringResult:
    try:
        return tailoring_service(
            request.resume_text,
            request.job_description_text,
            request.max_attempts,
        )
    except (
        MissingJobAnalysisOpenAIAPIKeyError,
        MissingRewriteOpenAIAPIKeyError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except (
        ResumeInputError,
        EmptyJobDescriptionError,
        JobAnalysisOutputError,
        RewriteOutputError,
        ValueError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
