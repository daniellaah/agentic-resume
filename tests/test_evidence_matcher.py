from app.evidence_matcher import match_evidence
from app.models import (
    JobAnalysis,
    JobRequirement,
    Resume,
    ResumeBullet,
    ResumeExperience,
)


def make_resume() -> Resume:
    return Resume(
        experience=[
            ResumeExperience(
                id="exp_1",
                company="Acme Analytics",
                title="Software Engineer",
                start_date="2024-01",
                bullets=[
                    ResumeBullet(
                        id="exp_1_bullet_1",
                        text=(
                            "Built internal REST APIs using Python and FastAPI "
                            "to support analyst workflows."
                        ),
                    ),
                    ResumeBullet(
                        id="exp_1_bullet_2",
                        text=(
                            "Designed PostgreSQL tables and queries for customer "
                            "reporting data."
                        ),
                    ),
                    ResumeBullet(
                        id="exp_1_bullet_3",
                        text=(
                            "Added pytest coverage for service-layer validation "
                            "and API error handling."
                        ),
                    ),
                ],
            )
        ]
    )


def make_job_analysis() -> JobAnalysis:
    return JobAnalysis(
        job_title="Backend Engineer",
        requirements=[
            JobRequirement(
                id="req_1",
                text="Build backend APIs using Python.",
                priority="must_have",
            ),
            JobRequirement(
                id="req_2",
                text="Design REST services with FastAPI or similar frameworks.",
                priority="must_have",
            ),
            JobRequirement(
                id="req_3",
                text="Work with PostgreSQL-backed application data.",
                priority="must_have",
            ),
            JobRequirement(
                id="req_4",
                text="Write automated tests for backend services.",
                priority="must_have",
            ),
            JobRequirement(
                id="req_5",
                text="Deploy containerized services to Kubernetes.",
                priority="nice_to_have",
            ),
        ],
    )


def test_match_evidence_returns_one_match_per_requirement():
    matches = match_evidence(make_resume(), make_job_analysis())

    assert [match.requirement_id for match in matches] == [
        "req_1",
        "req_2",
        "req_3",
        "req_4",
        "req_5",
    ]


def test_match_evidence_matches_python_api_requirement_strongly():
    matches = match_evidence(make_resume(), make_job_analysis())
    match_by_requirement = {match.requirement_id: match for match in matches}

    assert match_by_requirement["req_1"].status == "strong"
    assert match_by_requirement["req_1"].bullet_ids == ["exp_1_bullet_1"]


def test_match_evidence_matches_fastapi_rest_requirement_strongly():
    matches = match_evidence(make_resume(), make_job_analysis())
    match_by_requirement = {match.requirement_id: match for match in matches}

    assert match_by_requirement["req_2"].status == "strong"
    assert match_by_requirement["req_2"].bullet_ids == ["exp_1_bullet_1"]


def test_match_evidence_matches_postgresql_requirement_strongly():
    matches = match_evidence(make_resume(), make_job_analysis())
    match_by_requirement = {match.requirement_id: match for match in matches}

    assert match_by_requirement["req_3"].status == "strong"
    assert match_by_requirement["req_3"].bullet_ids == ["exp_1_bullet_2"]


def test_match_evidence_matches_automated_testing_requirement_strongly():
    matches = match_evidence(make_resume(), make_job_analysis())
    match_by_requirement = {match.requirement_id: match for match in matches}

    assert match_by_requirement["req_4"].status == "strong"
    assert match_by_requirement["req_4"].bullet_ids == ["exp_1_bullet_3"]


def test_match_evidence_marks_kubernetes_requirement_missing():
    matches = match_evidence(make_resume(), make_job_analysis())
    match_by_requirement = {match.requirement_id: match for match in matches}

    assert match_by_requirement["req_5"].status == "missing"
    assert match_by_requirement["req_5"].bullet_ids == []


def test_match_evidence_can_return_weak_match_for_partial_non_technical_overlap():
    resume = Resume(
        experience=[
            ResumeExperience(
                id="exp_1",
                company="Acme",
                title="Engineer",
                start_date="2024-01",
                bullets=[
                    ResumeBullet(
                        id="exp_1_bullet_1",
                        text="Built REST API service endpoints for internal users.",
                    )
                ],
            )
        ]
    )
    job_analysis = JobAnalysis(
        requirements=[
            JobRequirement(
                id="req_1",
                text="Design REST API services.",
                priority="must_have",
            )
        ]
    )

    matches = match_evidence(resume, job_analysis)

    assert matches[0].status == "weak"
    assert matches[0].bullet_ids == ["exp_1_bullet_1"]


def make_recommender_resume() -> Resume:
    return Resume(
        summary=(
            "Machine learning engineer with experience building large-scale "
            "recommendation, retrieval, candidate generation, offline evaluation, "
            "A/B testing, and production ML pipelines."
        ),
        skills=["Python", "PyTorch", "Spark", "Hive"],
        experience=[
            ResumeExperience(
                id="exp_1",
                company="RedNote",
                title="Machine Learning Engineer",
                start_date="2021-01",
                bullets=[
                    ResumeBullet(
                        id="exp_1_bullet_1",
                        text=(
                            "Designed and shipped production recommendation models "
                            "for large-scale candidate generation and retrieval."
                        ),
                    ),
                    ResumeBullet(
                        id="exp_1_bullet_2",
                        text=(
                            "Launched a multi-interest retrieval model with "
                            "self-attention over behavior sequences to learn diverse "
                            "user interest embeddings."
                        ),
                    ),
                    ResumeBullet(
                        id="exp_1_bullet_3",
                        text=(
                            "Improved a two-tower retrieval model by applying "
                            "LogQ-corrected in-batch sampled softmax and a "
                            "self-supervised contrastive auxiliary objective."
                        ),
                    ),
                ],
            ),
            ResumeExperience(
                id="exp_2",
                company="Joyy",
                title="Machine Learning Engineer",
                start_date="2019-01",
                bullets=[
                    ResumeBullet(
                        id="exp_2_bullet_1",
                        text=(
                            "Owned candidate generation for personalized video "
                            "recommendations, building production retrieval models, "
                            "offline evaluation workflows, and feature pipelines "
                            "through ANN-indexed real-time serving."
                        ),
                    ),
                    ResumeBullet(
                        id="exp_2_bullet_2",
                        text=(
                            "Built and deployed a two-tower model to learn user and "
                            "item embeddings for candidate generation, serving via "
                            "an ANN index for real-time retrieval."
                        ),
                    ),
                    ResumeBullet(
                        id="exp_2_bullet_3",
                        text=(
                            "Built user- and item-based collaborative filtering "
                            "pipelines using Hive and developed offline evaluation "
                            "with Recall@K before online A/B testing."
                        ),
                    ),
                ],
            ),
        ],
    )


def make_recommender_job_analysis() -> JobAnalysis:
    return JobAnalysis(
        job_title="Machine Learning Engineer",
        requirements=[
            JobRequirement(
                id="req_1",
                text="Experience with candidate generation.",
                priority="must_have",
            ),
            JobRequirement(
                id="req_2",
                text="Two-tower models.",
                priority="must_have",
            ),
            JobRequirement(
                id="req_3",
                text="Embedding-based retrieval.",
                priority="must_have",
            ),
            JobRequirement(
                id="req_4",
                text="ANN serving.",
                priority="nice_to_have",
            ),
            JobRequirement(
                id="req_5",
                text="A/B testing.",
                priority="nice_to_have",
            ),
            JobRequirement(
                id="req_6",
                text="Offline evaluation.",
                priority="must_have",
            ),
            JobRequirement(
                id="req_7",
                text="Python.",
                priority="must_have",
            ),
            JobRequirement(
                id="req_8",
                text="PyTorch.",
                priority="nice_to_have",
            ),
            JobRequirement(
                id="req_9",
                text="Spark.",
                priority="nice_to_have",
            ),
            JobRequirement(
                id="req_10",
                text="Hive.",
                priority="nice_to_have",
            ),
            JobRequirement(
                id="req_11",
                text="Production ML pipelines.",
                priority="must_have",
            ),
        ],
    )


def test_match_evidence_matches_recommender_system_requirements():
    matches = match_evidence(make_recommender_resume(), make_recommender_job_analysis())
    match_by_requirement = {match.requirement_id: match for match in matches}

    assert match_by_requirement["req_1"].status == "strong"
    assert "exp_1_bullet_1" in match_by_requirement["req_1"].bullet_ids
    assert "exp_2_bullet_1" in match_by_requirement["req_1"].bullet_ids
    assert match_by_requirement["req_2"].status == "strong"
    assert "exp_1_bullet_3" in match_by_requirement["req_2"].bullet_ids
    assert "exp_2_bullet_2" in match_by_requirement["req_2"].bullet_ids
    assert match_by_requirement["req_3"].status == "strong"
    assert "exp_1_bullet_2" in match_by_requirement["req_3"].bullet_ids
    assert match_by_requirement["req_4"].status == "strong"
    assert "exp_2_bullet_1" in match_by_requirement["req_4"].bullet_ids
    assert match_by_requirement["req_5"].status == "strong"
    assert match_by_requirement["req_5"].bullet_ids == ["exp_2_bullet_3"]
    assert match_by_requirement["req_6"].status == "strong"
    assert "exp_2_bullet_3" in match_by_requirement["req_6"].bullet_ids
    assert match_by_requirement["req_10"].status == "strong"
    assert match_by_requirement["req_10"].bullet_ids == ["exp_2_bullet_3"]
    assert match_by_requirement["req_11"].status in {"strong", "weak"}
    assert match_by_requirement["req_11"].bullet_ids


def test_match_evidence_uses_profile_skills_as_uncertain_non_rewritable_evidence():
    matches = match_evidence(make_recommender_resume(), make_recommender_job_analysis())
    match_by_requirement = {match.requirement_id: match for match in matches}

    assert match_by_requirement["req_7"].status == "uncertain"
    assert match_by_requirement["req_7"].bullet_ids == []
    assert match_by_requirement["req_8"].status == "uncertain"
    assert match_by_requirement["req_8"].bullet_ids == []
    assert match_by_requirement["req_9"].status == "uncertain"
    assert match_by_requirement["req_9"].bullet_ids == []
