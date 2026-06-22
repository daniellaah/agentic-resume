import pytest

from app.models import (
    JobAnalysis,
    JobRequirement,
    Resume,
    ResumeBullet,
    ResumeExperience,
)
from app.tailoring_agent import (
    AGENT_WORKFLOW_VERSION,
    DEFAULT_MAX_ATTEMPTS,
    tailor_resume_to_job_agentic,
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
                        text="Built internal REST APIs using Python and FastAPI.",
                    )
                ],
            )
        ]
    )


def fake_resume_parser(resume_text: str) -> Resume:
    assert resume_text == "resume text"
    return make_resume()


def fake_job_analysis_provider(jd_text: str):
    assert jd_text == "Backend Engineer JD"
    return {
        "job_title": "Backend Engineer",
        "requirements": [
            {
                "id": "req_1",
                "text": "Build backend APIs using Python.",
                "priority": "must_have",
            },
            {
                "id": "req_2",
                "text": "Design REST services with FastAPI.",
                "priority": "must_have",
            },
            {
                "id": "req_3",
                "text": "Deploy services to Kubernetes.",
                "priority": "nice_to_have",
            },
        ],
    }


def valid_rewrite_payload():
    return {
        "suggestions": [
            {
                "bullet_id": "exp_1_bullet_1",
                "rewritten_text": (
                    "Built Python and FastAPI REST APIs for internal workflows."
                ),
                "requirement_ids": ["req_1", "req_2"],
            }
        ]
    }


def test_agentic_tailoring_accepts_first_safe_attempt():
    calls = []

    def fake_rewrite_provider(candidates, feedback):
        calls.append(
            {
                "candidate_count": len(candidates),
                "feedback": feedback,
            }
        )
        return valid_rewrite_payload()

    result = tailor_resume_to_job_agentic(
        resume_text="resume text",
        jd_text="Backend Engineer JD",
        resume_parser=fake_resume_parser,
        job_analysis_provider=fake_job_analysis_provider,
        rewrite_provider=fake_rewrite_provider,
    )

    assert result.status == "success"
    assert result.metadata.workflow_version == AGENT_WORKFLOW_VERSION
    assert result.metadata.max_attempts == DEFAULT_MAX_ATTEMPTS
    assert result.final_result.status == "success"
    assert [attempt.status for attempt in result.attempts] == ["accepted"]
    assert [step.tool_name for step in result.steps] == [
        "resume_input",
        "job_analysis",
        "evidence_matching",
        "rewrite_candidate_builder",
        "rewrite_generation",
        "claim_checker",
        "validation",
    ]
    assert result.steps[-1].status == "success"
    assert result.steps[-1].attempt_number == 1
    assert calls[0]["feedback"] == []
    assert result.accepted_requirement_ids == ["req_1", "req_2"]
    assert result.missing_requirement_ids == ["req_3"]


def test_agentic_tailoring_retries_after_validation_failure():
    feedback_seen = []

    def fake_rewrite_provider(candidates, feedback):
        feedback_seen.append(feedback)
        if len(feedback_seen) == 1:
            return {
                "suggestions": [
                    {
                        "bullet_id": "exp_1_bullet_1",
                        "rewritten_text": (
                            "Built Python APIs and deployed services to Kubernetes."
                        ),
                        "requirement_ids": ["req_1", "req_3"],
                    }
                ]
            }

        assert feedback
        assert any(issue.severity == "critical" for issue in feedback)
        return valid_rewrite_payload()

    result = tailor_resume_to_job_agentic(
        resume_text="resume text",
        jd_text="Backend Engineer JD",
        resume_parser=fake_resume_parser,
        job_analysis_provider=fake_job_analysis_provider,
        rewrite_provider=fake_rewrite_provider,
        max_attempts=2,
    )

    assert result.status == "success"
    assert [attempt.status for attempt in result.attempts] == [
        "rejected",
        "accepted",
    ]
    assert [step.status for step in result.steps if step.tool_name == "validation"] == [
        "failed",
        "success",
    ]
    assert [
        step.attempt_number
        for step in result.steps
        if step.tool_name == "rewrite_generation"
    ] == [1, 2]
    assert [
        step.status for step in result.steps if step.tool_name == "claim_checker"
    ] == [
        "failed",
        "success",
    ]
    assert result.final_result.status == "success"
    assert result.accepted_requirement_ids == ["req_1", "req_2"]
    assert result.rejected_requirement_ids == ["req_3"]
    assert feedback_seen[0] == []
    assert feedback_seen[1]


def test_agentic_tailoring_retries_after_unsupported_claim():
    feedback_seen = []

    def fake_rewrite_provider(candidates, feedback):
        feedback_seen.append(feedback)
        if len(feedback_seen) == 1:
            return {
                "suggestions": [
                    {
                        "bullet_id": "exp_1_bullet_1",
                        "rewritten_text": (
                            "Built Python and FastAPI APIs deployed to Kubernetes."
                        ),
                        "requirement_ids": ["req_1", "req_2"],
                    }
                ]
            }

        assert feedback
        assert any("Kubernetes" in issue.message for issue in feedback)
        return valid_rewrite_payload()

    result = tailor_resume_to_job_agentic(
        resume_text="resume text",
        jd_text="Backend Engineer JD",
        resume_parser=fake_resume_parser,
        job_analysis_provider=fake_job_analysis_provider,
        rewrite_provider=fake_rewrite_provider,
        max_attempts=2,
    )

    assert result.status == "success"
    assert [attempt.status for attempt in result.attempts] == [
        "rejected",
        "accepted",
    ]
    assert [
        step.status for step in result.steps if step.tool_name == "claim_checker"
    ] == [
        "failed",
        "success",
    ]
    assert result.accepted_requirement_ids == ["req_1", "req_2"]
    assert result.rejected_requirement_ids == []


def test_agentic_tailoring_fails_after_max_attempts():
    def fake_rewrite_provider(candidates, feedback):
        return {
            "suggestions": [
                {
                    "bullet_id": "exp_1_bullet_1",
                    "rewritten_text": (
                        "Built Python APIs and deployed services to Kubernetes."
                    ),
                    "requirement_ids": ["req_1", "req_3"],
                }
            ]
        }

    result = tailor_resume_to_job_agentic(
        resume_text="resume text",
        jd_text="Backend Engineer JD",
        resume_parser=fake_resume_parser,
        job_analysis_provider=fake_job_analysis_provider,
        rewrite_provider=fake_rewrite_provider,
        max_attempts=2,
    )

    assert result.status == "failed_validation"
    assert result.final_result.status == "failed_validation"
    assert result.final_result.rewrite_suggestions == []
    assert [attempt.status for attempt in result.attempts] == [
        "rejected",
        "rejected",
    ]
    assert result.rejected_requirement_ids == ["req_1", "req_3"]


def test_agentic_tailoring_returns_no_candidate_result_without_supported_evidence():
    def missing_only_job_analysis_provider(jd_text: str):
        return JobAnalysis(
            job_title="Platform Engineer",
            requirements=[
                JobRequirement(
                    id="req_1",
                    text="Deploy services to Kubernetes.",
                    priority="must_have",
                )
            ],
        ).model_dump()

    def fake_rewrite_provider(candidates, feedback):
        raise AssertionError("Rewrite provider should not run without candidates.")

    result = tailor_resume_to_job_agentic(
        resume_text="resume text",
        jd_text="Backend Engineer JD",
        resume_parser=fake_resume_parser,
        job_analysis_provider=missing_only_job_analysis_provider,
        rewrite_provider=fake_rewrite_provider,
    )

    assert result.status == "no_rewrite_candidates"
    assert result.final_result.status == "success"
    assert result.attempts == []
    assert [step.tool_name for step in result.steps[-3:]] == [
        "rewrite_generation",
        "claim_checker",
        "validation",
    ]
    assert [step.status for step in result.steps[-3:]] == [
        "skipped",
        "skipped",
        "skipped",
    ]
    assert result.missing_requirement_ids == ["req_1"]


def test_agentic_tailoring_rejects_invalid_max_attempts():
    with pytest.raises(ValueError, match="max_attempts"):
        tailor_resume_to_job_agentic(
            resume_text="resume text",
            jd_text="Backend Engineer JD",
            resume_parser=fake_resume_parser,
            job_analysis_provider=fake_job_analysis_provider,
            rewrite_provider=lambda candidates, feedback: valid_rewrite_payload(),
            max_attempts=0,
        )
