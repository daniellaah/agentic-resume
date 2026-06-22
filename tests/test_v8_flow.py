from pathlib import Path

from app.tailoring_agent import tailor_resume_to_job_agentic

ROOT_DIR = Path(__file__).resolve().parents[1]


def fake_job_analysis_provider(jd_text: str):
    assert "Backend Engineer" in jd_text
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
                "text": "Design REST services with FastAPI or similar frameworks.",
                "priority": "must_have",
            },
            {
                "id": "req_3",
                "text": "Work with PostgreSQL-backed application data.",
                "priority": "must_have",
            },
            {
                "id": "req_4",
                "text": "Write automated tests for backend services.",
                "priority": "must_have",
            },
            {
                "id": "req_5",
                "text": "Deploy containerized services to Kubernetes.",
                "priority": "nice_to_have",
            },
        ],
    }


def fake_agent_rewrite_provider(candidates, feedback):
    assert feedback == []
    assert [candidate.bullet_id for candidate in candidates] == [
        "exp_1_bullet_1",
        "exp_1_bullet_2",
        "exp_1_bullet_3",
    ]

    return {
        "suggestions": [
            {
                "bullet_id": "exp_1_bullet_1",
                "rewritten_text": (
                    "Built Python and FastAPI REST APIs for internal analyst workflows."
                ),
                "requirement_ids": ["req_1", "req_2"],
            },
            {
                "bullet_id": "exp_1_bullet_2",
                "rewritten_text": (
                    "Designed PostgreSQL-backed reporting data models and "
                    "queries for customer reporting workflows."
                ),
                "requirement_ids": ["req_3"],
            },
            {
                "bullet_id": "exp_1_bullet_3",
                "rewritten_text": (
                    "Added pytest coverage for backend service validation and "
                    "API error handling."
                ),
                "requirement_ids": ["req_4"],
            },
        ]
    }


def test_v8_flow_returns_agentic_trace_without_network_access():
    resume_text = (ROOT_DIR / "data" / "sample_resume.txt").read_text()
    jd_text = (ROOT_DIR / "data" / "sample_jd.txt").read_text()

    result = tailor_resume_to_job_agentic(
        resume_text=resume_text,
        jd_text=jd_text,
        job_analysis_provider=fake_job_analysis_provider,
        rewrite_provider=fake_agent_rewrite_provider,
    )

    assert result.status == "success"
    assert result.metadata.workflow_version == "v8"
    assert result.final_result.status == "success"
    assert result.final_result.validation_issues == []
    assert [attempt.status for attempt in result.attempts] == ["accepted"]
    assert result.missing_requirement_ids == ["req_5"]
    assert result.accepted_requirement_ids == ["req_1", "req_2", "req_3", "req_4"]
    assert result.rejected_requirement_ids == []
