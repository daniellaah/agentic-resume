import pytest

import app.llm_backend as llm_backend_module
from app.job_analysis import (
    EmptyJobDescriptionError,
    JobAnalysisOutputError,
    MissingOpenAIAPIKeyError,
    analyze_job_description,
    parse_job_analysis_payload,
)
from app.models import JobAnalysis


def valid_job_analysis_payload():
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
                "text": "Work with PostgreSQL-backed application data.",
                "priority": "nice_to_have",
            },
        ],
    }


def test_analyze_job_description_uses_fake_provider():
    def fake_provider(jd_text: str):
        assert jd_text == "Backend Engineer JD"
        return valid_job_analysis_payload()

    analysis = analyze_job_description(
        "  Backend Engineer JD  ",
        payload_provider=fake_provider,
    )

    assert analysis.job_title == "Backend Engineer"
    assert [requirement.id for requirement in analysis.requirements] == [
        "req_1",
        "req_2",
    ]


def test_analyze_job_description_rejects_empty_input():
    def fake_provider(jd_text: str):
        raise AssertionError("Provider should not be called for empty input.")

    with pytest.raises(EmptyJobDescriptionError):
        analyze_job_description("   ", payload_provider=fake_provider)


def test_parse_job_analysis_payload_accepts_valid_payload():
    analysis = parse_job_analysis_payload(valid_job_analysis_payload())

    assert analysis.requirements[0].text == "Build backend APIs using Python."
    assert analysis.requirements[0].priority == "must_have"


def test_parse_job_analysis_payload_rejects_invalid_schema():
    payload = valid_job_analysis_payload()
    payload["requirements"][0]["priority"] = "required"

    with pytest.raises(JobAnalysisOutputError, match="JobAnalysis schema"):
        parse_job_analysis_payload(payload)


def test_parse_job_analysis_payload_rejects_empty_requirements():
    with pytest.raises(JobAnalysisOutputError, match="at least one requirement"):
        parse_job_analysis_payload(
            {
                "job_title": "Backend Engineer",
                "requirements": [],
            }
        )


def test_parse_job_analysis_payload_rejects_non_deterministic_requirement_ids():
    payload = valid_job_analysis_payload()
    payload["requirements"][0]["id"] = "backend_python"

    with pytest.raises(JobAnalysisOutputError, match="deterministic"):
        parse_job_analysis_payload(payload)


def test_analyze_job_description_uses_default_openai_provider(monkeypatch):
    calls = {}

    class FakeResponses:
        def parse(self, *, model, input, text_format):
            calls["model"] = model
            calls["input"] = input
            calls["text_format"] = text_format

            class FakeResponse:
                output_parsed = parse_job_analysis_payload(valid_job_analysis_payload())

            return FakeResponse()

    class FakeOpenAI:
        def __init__(self, *, api_key):
            calls["api_key"] = api_key
            self.responses = FakeResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("OPENAI_MODEL_NAME", "test-model")
    monkeypatch.setenv("LLM_BACKEND", "openai")
    monkeypatch.setattr(llm_backend_module, "OpenAI", FakeOpenAI)

    analysis = analyze_job_description("  Backend Engineer JD  ")

    assert analysis.job_title == "Backend Engineer"
    assert calls["api_key"] == "test-api-key"
    assert calls["model"] == "test-model"
    assert calls["text_format"] is JobAnalysis
    assert calls["input"][0]["role"] == "system"
    assert calls["input"][1] == {
        "role": "user",
        "content": "Backend Engineer JD",
    }


def test_analyze_job_description_default_provider_rejects_missing_api_key(
    monkeypatch,
):
    class FakeOpenAI:
        def __init__(self, *, api_key):
            raise AssertionError("OpenAI client should not be created without a key.")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_BACKEND", "openai")
    monkeypatch.setattr(llm_backend_module, "OpenAI", FakeOpenAI)

    with pytest.raises(MissingOpenAIAPIKeyError, match="OPENAI_API_KEY"):
        analyze_job_description("Backend Engineer JD")


def test_analyze_job_description_default_provider_uses_default_model(monkeypatch):
    calls = {}

    class FakeResponses:
        def parse(self, *, model, input, text_format):
            calls["model"] = model

            class FakeResponse:
                output_parsed = parse_job_analysis_payload(valid_job_analysis_payload())

            return FakeResponse()

    class FakeOpenAI:
        def __init__(self, *, api_key):
            self.responses = FakeResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.delenv("OPENAI_MODEL_NAME", raising=False)
    monkeypatch.setenv("LLM_BACKEND", "openai")
    monkeypatch.setattr(llm_backend_module, "OpenAI", FakeOpenAI)

    analyze_job_description("Backend Engineer JD")

    assert calls["model"] == "gpt-5.5"
