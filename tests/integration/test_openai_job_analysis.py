import os
from pathlib import Path

import pytest

from app.job_analysis import analyze_job_description

ROOT_DIR = Path(__file__).resolve().parents[2]


pytestmark = pytest.mark.integration


def should_run_openai_integration() -> bool:
    return os.environ.get("RUN_OPENAI_INTEGRATION") == "1" and bool(
        os.environ.get("OPENAI_API_KEY")
    )


@pytest.mark.skipif(
    not should_run_openai_integration(),
    reason="Set RUN_OPENAI_INTEGRATION=1 and OPENAI_API_KEY to run.",
)
def test_openai_job_analysis_for_sample_jd_returns_valid_job_analysis():
    jd_text = (ROOT_DIR / "data" / "sample_jd.txt").read_text()

    analysis = analyze_job_description(jd_text)

    assert analysis.job_title
    assert analysis.requirements
    assert [requirement.id for requirement in analysis.requirements] == [
        f"req_{index}" for index in range(1, len(analysis.requirements) + 1)
    ]
    assert all(
        requirement.priority in {"must_have", "nice_to_have"}
        for requirement in analysis.requirements
    )
