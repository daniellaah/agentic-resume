import os
from pathlib import Path

import pytest

from app.evidence_matcher import match_evidence
from app.job_analysis import analyze_job_description
from app.parsers import parse_sample_resume
from app.rewrite_generator import generate_rewrite_suggestions
from app.validator import validate_resume_tailoring


ROOT_DIR = Path(__file__).resolve().parents[2]


pytestmark = pytest.mark.integration


def should_run_openai_integration() -> bool:
    return (
        os.environ.get("RUN_OPENAI_INTEGRATION") == "1"
        and bool(os.environ.get("OPENAI_API_KEY"))
    )


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


@pytest.mark.skipif(
    not should_run_openai_integration(),
    reason="Set RUN_OPENAI_INTEGRATION=1 and OPENAI_API_KEY to run.",
)
def test_openai_rewrite_generator_returns_validator_safe_suggestions():
    resume_text = (ROOT_DIR / "data" / "sample_resume.txt").read_text()
    jd_text = (ROOT_DIR / "data" / "sample_jd.txt").read_text()

    resume = parse_sample_resume(resume_text)
    job_analysis = analyze_job_description(
        jd_text,
        payload_provider=fake_job_analysis_provider,
    )
    evidence_matches = match_evidence(resume, job_analysis)
    suggestions = generate_rewrite_suggestions(
        resume=resume,
        job_analysis=job_analysis,
        evidence_matches=evidence_matches,
    )
    issues = validate_resume_tailoring(
        resume=resume,
        job_analysis=job_analysis,
        evidence_matches=evidence_matches,
        rewrite_suggestions=suggestions,
    )

    assert suggestions
    assert issues == []
    assert all(
        "req_5" not in suggestion.requirement_ids
        for suggestion in suggestions
    )
