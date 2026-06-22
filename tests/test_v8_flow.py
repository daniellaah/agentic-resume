from pathlib import Path

from app.tailoring_agent import AGENT_WORKFLOW_VERSION, tailor_resume_to_job_agentic

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


def test_v14_flow_returns_agentic_plan_and_tool_trace_without_network_access():
    resume_text = (ROOT_DIR / "data" / "sample_resume.txt").read_text()
    jd_text = (ROOT_DIR / "data" / "sample_jd.txt").read_text()

    result = tailor_resume_to_job_agentic(
        resume_text=resume_text,
        jd_text=jd_text,
        job_analysis_provider=fake_job_analysis_provider,
        rewrite_provider=fake_agent_rewrite_provider,
    )

    assert result.status == "success"
    assert result.metadata.workflow_version == AGENT_WORKFLOW_VERSION
    assert result.plan is not None
    assert result.plan.plan_id == "resume_tailoring_v14"
    assert result.plan.orchestrator_agent == "resume_tailoring_orchestrator_agent"
    assert result.final_result.status == "success"
    assert result.final_result.validation_issues == []
    assert [decision.decision_type for decision in result.decisions] == [
        "plan",
        "accept",
    ]
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
    assert [step.step_number for step in result.steps] == [1, 2, 3, 4, 5, 6, 7]
    assert result.steps[-1].output_summary == (
        "0 validation issues (critical=0, warning=0)"
    )
    assert result.missing_requirement_ids == ["req_5"]
    assert result.accepted_requirement_ids == ["req_1", "req_2", "req_3", "req_4"]
    assert result.rejected_requirement_ids == []
