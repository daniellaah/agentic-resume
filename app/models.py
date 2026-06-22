from typing import Annotated, Literal

from pydantic import BaseModel, Field

NonEmptyStr = Annotated[str, Field(min_length=1)]


class ResumeBullet(BaseModel):
    id: NonEmptyStr
    text: NonEmptyStr


class ResumeExperience(BaseModel):
    id: NonEmptyStr
    company: NonEmptyStr
    title: NonEmptyStr
    start_date: str
    end_date: str | None = None
    bullets: list[ResumeBullet] = Field(min_length=1)


class Resume(BaseModel):
    summary: str | None = None
    skills: list[NonEmptyStr] = Field(default_factory=list)
    experience: list[ResumeExperience] = Field(min_length=1)


class JobRequirement(BaseModel):
    id: NonEmptyStr
    text: NonEmptyStr
    priority: Literal["must_have", "nice_to_have"]


class JobAnalysis(BaseModel):
    job_title: str | None = None
    requirements: list[JobRequirement]


class EvidenceMatch(BaseModel):
    requirement_id: NonEmptyStr
    bullet_ids: list[NonEmptyStr] = Field(default_factory=list)
    status: Literal["strong", "weak", "missing", "uncertain"]


class RewriteSuggestion(BaseModel):
    bullet_id: NonEmptyStr
    rewritten_text: NonEmptyStr
    requirement_ids: list[NonEmptyStr] = Field(min_length=1)


class ValidationIssue(BaseModel):
    issue_type: Literal[
        "unsupported_claim", "changed_fact", "missing_evidence", "formatting"
    ]
    severity: Literal["critical", "warning"]
    message: NonEmptyStr
