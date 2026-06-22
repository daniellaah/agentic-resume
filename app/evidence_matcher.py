import re
from dataclasses import dataclass

from app.models import EvidenceMatch, JobAnalysis, JobRequirement, Resume, ResumeBullet

TOKEN_PATTERN = re.compile(r"[a-z0-9+#@]+(?:/[a-z0-9+#@]+)?")
NON_SIGNAL_PATTERN = re.compile(r"[^a-z0-9+#@/]+")

SIGNAL_ALIASES = {
    "ab": "ab_testing",
    "api": "api",
    "apis": "api",
    "airflow": "airflow",
    "ann": "ann",
    "rest": "rest",
    "backend": "backend",
    "candidate": "candidate",
    "candidates": "candidate",
    "collaborative": "collaborative_filtering",
    "contrastive": "contrastive_learning",
    "python": "python",
    "pytorch": "pytorch",
    "fastapi": "fastapi",
    "flink": "flink",
    "hive": "hive",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "query": "database",
    "queries": "database",
    "table": "database",
    "tables": "database",
    "data": "data",
    "evaluation": "evaluation",
    "experiments": "experimentation",
    "experiment": "experimentation",
    "features": "feature",
    "feature": "feature",
    "generation": "generation",
    "index": "index",
    "indexed": "index",
    "item": "item",
    "items": "item",
    "embedding": "embedding",
    "embeddings": "embedding",
    "long-tail": "long_tail",
    "long": "long_tail",
    "tail": "long_tail",
    "ml": "machine_learning",
    "model": "model",
    "models": "model",
    "offline": "offline",
    "pipeline": "pipeline",
    "pipelines": "pipeline",
    "production": "production",
    "recall@k": "recall_at_k",
    "recommendation": "recommendation",
    "recommendations": "recommendation",
    "recommender": "recommendation",
    "retrieval": "retrieval",
    "self-attention": "self_attention",
    "serving": "serving",
    "similarities": "similarity",
    "similarity": "similarity",
    "spark": "spark",
    "streaming": "streaming",
    "swing": "swing",
    "tensorflow": "tensorflow",
    "tower": "tower",
    "towers": "tower",
    "user": "user",
    "users": "user",
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

PHRASE_ALIASES = {
    "a b testing": "ab_testing",
    "ab testing": "ab_testing",
    "ann index": "ann_serving",
    "ann indexed": "ann_serving",
    "ann serving": "ann_serving",
    "average user watch time": "watch_time",
    "candidate generation": "candidate_generation",
    "collaborative filtering": "collaborative_filtering",
    "contrastive auxiliary objective": "contrastive_learning",
    "embedding based retrieval": "embedding_retrieval",
    "embeddings for candidate generation": "candidate_generation",
    "experiment design": "experimentation",
    "factorization machine": "factorization_machine",
    "feature pipelines": "production_ml_pipeline",
    "home feed": "recommendation",
    "in batch sampled softmax": "sampled_softmax",
    "item based collaborative filtering": "collaborative_filtering",
    "item embeddings": "embedding",
    "item to item retrieval": "item_to_item_retrieval",
    "large scale candidate generation": "candidate_generation",
    "logq corrected": "logq",
    "masked user and item feature views": "contrastive_learning",
    "multi interest retrieval": "embedding_retrieval",
    "offline evaluation": "offline_evaluation",
    "online a b testing": "ab_testing",
    "production deployment": "production_ml_pipeline",
    "production ml pipelines": "production_ml_pipeline",
    "real time retrieval": "ann_serving",
    "real time serving": "ann_serving",
    "recall k": "offline_evaluation",
    "self supervised": "self_supervised_learning",
    "streaming item to item retrieval": "item_to_item_retrieval",
    "two tower": "two_tower",
    "user and item embeddings": "embedding",
    "user embeddings": "embedding",
    "user item latent vectors": "embedding",
}

STRONG_SIGNALS = {
    "ab_testing",
    "airflow",
    "ann_serving",
    "candidate_generation",
    "collaborative_filtering",
    "contrastive_learning",
    "embedding_retrieval",
    "factorization_machine",
    "flink",
    "hive",
    "item_to_item_retrieval",
    "logq",
    "offline_evaluation",
    "python",
    "fastapi",
    "postgresql",
    "production_ml_pipeline",
    "pytorch",
    "sampled_softmax",
    "self_supervised_learning",
    "spark",
    "streaming",
    "swing",
    "tensorflow",
    "testing",
    "docker",
    "kubernetes",
    "react",
    "two_tower",
}

MIN_WEAK_SIGNAL_COUNT = 2
MAX_BULLET_IDS_PER_REQUIREMENT = 3


@dataclass(frozen=True)
class BulletMatch:
    bullet_id: str
    status: str
    score: int
    order: int


def match_evidence(resume: Resume, job_analysis: JobAnalysis) -> list[EvidenceMatch]:
    bullets = _flatten_bullets(resume)
    profile_signals = _profile_signals(resume)

    return [
        _match_requirement(
            requirement=requirement,
            bullets=bullets,
            profile_signals=profile_signals,
        )
        for requirement in job_analysis.requirements
    ]


def _flatten_bullets(resume: Resume) -> list[ResumeBullet]:
    return [bullet for experience in resume.experience for bullet in experience.bullets]


def _match_requirement(
    requirement: JobRequirement,
    bullets: list[ResumeBullet],
    profile_signals: set[str],
) -> EvidenceMatch:
    bullet_matches = [
        match
        for order, bullet in enumerate(bullets)
        if (
            match := _score_bullet(
                requirement=requirement,
                bullet=bullet,
                order=order,
            )
        )
        is not None
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

    if _extract_signals(requirement.text) & profile_signals:
        return EvidenceMatch(
            requirement_id=requirement.id,
            bullet_ids=[],
            status="uncertain",
        )

    return EvidenceMatch(
        requirement_id=requirement.id,
        bullet_ids=[],
        status="missing",
    )


def _score_bullet(
    requirement: JobRequirement,
    bullet: ResumeBullet,
    order: int,
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
            score=_match_score(matching_signals),
            order=order,
        )

    if len(matching_signals) >= MIN_WEAK_SIGNAL_COUNT:
        return BulletMatch(
            bullet_id=bullet.id,
            status="weak",
            score=_match_score(matching_signals),
            order=order,
        )

    return None


def _extract_signals(text: str) -> set[str]:
    normalized_text = _normalize_text(text)
    tokens = TOKEN_PATTERN.findall(normalized_text)
    token_signals = {
        signal for token in tokens if (signal := SIGNAL_ALIASES.get(token)) is not None
    }
    phrase_signals = {
        signal for phrase, signal in PHRASE_ALIASES.items() if phrase in normalized_text
    }
    return token_signals | phrase_signals


def _profile_signals(resume: Resume) -> set[str]:
    profile_text = " ".join([resume.summary or "", *resume.skills])
    return _extract_signals(profile_text)


def _normalize_text(text: str) -> str:
    normalized = text.lower().replace("a/b", "a b")
    normalized = normalized.replace("-", " ")
    normalized = NON_SIGNAL_PATTERN.sub(" ", normalized)
    return " ".join(normalized.split())


def _match_score(signals: set[str]) -> int:
    strong_signal_count = len(signals & STRONG_SIGNALS)
    return len(signals) + (strong_signal_count * 2)


def _ordered_bullet_ids(matches: list[BulletMatch]) -> list[str]:
    ordered_matches = sorted(matches, key=lambda match: (-match.score, match.order))
    return [
        match.bullet_id for match in ordered_matches[:MAX_BULLET_IDS_PER_REQUIREMENT]
    ]
