import os
from pathlib import Path

import pytest

from app.job_analysis import analyze_job_description

ROOT_DIR = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.integration


def should_run_ollama_integration() -> bool:
    return os.environ.get("RUN_OLLAMA_INTEGRATION") == "1"


@pytest.mark.skipif(
    not should_run_ollama_integration(),
    reason="Set RUN_OLLAMA_INTEGRATION=1 and LLM_BACKEND=ollama to run.",
)
def test_ollama_job_analysis_for_sample_jd_returns_requirement(monkeypatch):
    jd_text = (ROOT_DIR / "data" / "sample_jd.txt").read_text()
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    monkeypatch.setenv(
        "OLLAMA_MODEL",
        os.environ.get("OLLAMA_MODEL", "llama3.2:latest"),
    )

    analysis = analyze_job_description(jd_text)

    assert analysis.requirements
    assert analysis.requirements[0].id == "req_1"
    assert analysis.requirements[0].text
