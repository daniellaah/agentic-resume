import re
from dataclasses import dataclass

from app.models import EvidenceMatch, JobAnalysis, JobRequirement, Resume, ResumeBullet


TOKEN_PATTERN = re.compile(r"[a-z0-9+#]+(?:/[a-z0-9+#]+)?")

SIGNAL_ALIASES = {
    "api": "api",
    "apis": "api",
    "rest": "rest",
    "backend": "backend",
    "python": "python",
    "fastapi": "fastapi",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "query": "database",
    "queries": "database",
    "table": "database",
    "tables": "database",
    "data": "data",
    "pytest": "testing",
    "test": "testing",
    "tests": "testing",
    "testing": "testing",
    "coverage": "testing",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "container": "container",
    "containers": "container",
    "containerized": "container",
    "deploy": "deployment",
    "deployed": "deployment",
    "deploying": "deployment",
    "deployment": "deployment",
    "ci/cd": "cicd",
    "cicd": "cicd",
    "cloud": "cloud",
    "react": "react",
}

STRONG_SIGNALS = {
    "python",
    "fastapi",
    "postgresql",
    "testing",
    "docker",
    "kubernetes",
    "react",
}

MIN_WEAK_SIGNAL_COUNT = 2


@dataclass(frozen=True)
class BulletMatch:
    bullet_id: str
    status: str
    score: int


def match_evidence(resume: Resume, job_analysis: JobAnalysis) -> list[EvidenceMatch]:
    bullets = _flatten_bullets(resume)

    return [
        _match_requirement(requirement=requirement, bullets=bullets)
        for requirement in job_analysis.requirements
    ]


def _flatten_bullets(resume: Resume) -> list[ResumeBullet]:
    return [
        bullet
        for experience in resume.experience
        for bullet in experience.bullets
    ]


def _match_requirement(
    requirement: JobRequirement,
    bullets: list[ResumeBullet],
) -> EvidenceMatch:
    bullet_matches = [
        match
        for bullet in bullets
        if (match := _score_bullet(requirement=requirement, bullet=bullet)) is not None
    ]

    strong_matches = [match for match in bullet_matches if match.status == "strong"]
    if strong_matches:
        return EvidenceMatch(
            requirement_id=requirement.id,
            bullet_ids=_ordered_bullet_ids(strong_matches),
            status="strong",
        )

    weak_matches = [match for match in bullet_matches if match.status == "weak"]
    if weak_matches:
        return EvidenceMatch(
            requirement_id=requirement.id,
            bullet_ids=_ordered_bullet_ids(weak_matches),
            status="weak",
        )

    return EvidenceMatch(
        requirement_id=requirement.id,
        bullet_ids=[],
        status="missing",
    )


def _score_bullet(
    requirement: JobRequirement,
    bullet: ResumeBullet,
) -> BulletMatch | None:
    requirement_signals = _extract_signals(requirement.text)
    bullet_signals = _extract_signals(bullet.text)
    matching_signals = requirement_signals & bullet_signals

    if not matching_signals:
        return None

    if matching_signals & STRONG_SIGNALS:
        return BulletMatch(
            bullet_id=bullet.id,
            status="strong",
            score=len(matching_signals),
        )

    if len(matching_signals) >= MIN_WEAK_SIGNAL_COUNT:
        return BulletMatch(
            bullet_id=bullet.id,
            status="weak",
            score=len(matching_signals),
        )

    return None


def _extract_signals(text: str) -> set[str]:
    tokens = TOKEN_PATTERN.findall(text.lower())
    return {
        signal
        for token in tokens
        if (signal := SIGNAL_ALIASES.get(token)) is not None
    }


def _ordered_bullet_ids(matches: list[BulletMatch]) -> list[str]:
    return [match.bullet_id for match in matches]
