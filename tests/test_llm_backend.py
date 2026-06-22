import json
import urllib.error

import pytest

import app.llm_backend as llm_backend_module
from app.llm_backend import (
    LLMBackendConfigurationError,
    LLMProviderOutputError,
    LLMProviderRequestError,
    MissingOpenAIAPIKeyError,
    call_structured_llm,
)
from app.models import JobAnalysis


def valid_job_analysis_payload() -> dict:
    return {
        "job_title": "Backend Engineer",
        "requirements": [
            {
                "id": "req_1",
                "text": "Build backend APIs using Python.",
                "priority": "must_have",
            }
        ],
    }


def test_structured_llm_uses_openai_by_default(monkeypatch):
    calls = {}

    class FakeResponses:
        def parse(self, *, model, input, text_format):
            calls["model"] = model
            calls["input"] = input
            calls["text_format"] = text_format

            class FakeResponse:
                output_parsed = JobAnalysis.model_validate(valid_job_analysis_payload())

            return FakeResponse()

    class FakeOpenAI:
        def __init__(self, *, api_key):
            calls["api_key"] = api_key
            self.responses = FakeResponses()

    monkeypatch.delenv("LLM_BACKEND", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("OPENAI_MODEL_NAME", "test-openai-model")
    monkeypatch.setattr(llm_backend_module, "OpenAI", FakeOpenAI)

    payload = call_structured_llm(
        system_prompt="system prompt",
        user_content="user content",
        response_model=JobAnalysis,
    )

    assert payload == valid_job_analysis_payload()
    assert calls["api_key"] == "test-api-key"
    assert calls["model"] == "test-openai-model"
    assert calls["text_format"] is JobAnalysis
    assert calls["input"] == [
        {
            "role": "system",
            "content": "system prompt",
        },
        {
            "role": "user",
            "content": "user content",
        },
    ]


def test_structured_llm_openai_rejects_missing_api_key(monkeypatch):
    class FakeOpenAI:
        def __init__(self, *, api_key):
            raise AssertionError("OpenAI client should not be created.")

    monkeypatch.setenv("LLM_BACKEND", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(llm_backend_module, "OpenAI", FakeOpenAI)

    with pytest.raises(MissingOpenAIAPIKeyError, match="OPENAI_API_KEY"):
        call_structured_llm(
            system_prompt="system prompt",
            user_content="user content",
            response_model=JobAnalysis,
        )


def test_structured_llm_rejects_unknown_backend(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "unknown")

    with pytest.raises(LLMBackendConfigurationError, match="Unsupported LLM backend"):
        call_structured_llm(
            system_prompt="system prompt",
            user_content="user content",
            response_model=JobAnalysis,
        )


def test_structured_llm_ollama_posts_chat_request(monkeypatch):
    calls = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def read(self):
            return json.dumps(
                {
                    "message": {
                        "content": json.dumps(valid_job_analysis_payload()),
                    }
                }
            ).encode("utf-8")

    def fake_urlopen(request, *, timeout):
        calls["url"] = request.full_url
        calls["timeout"] = timeout
        calls["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setenv("LLM_BACKEND", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.test:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:latest")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "7.5")
    monkeypatch.setattr(llm_backend_module.urllib.request, "urlopen", fake_urlopen)

    payload = call_structured_llm(
        system_prompt="system prompt",
        user_content="user content",
        response_model=JobAnalysis,
    )

    assert payload == valid_job_analysis_payload()
    assert calls["url"] == "http://ollama.test:11434/api/chat"
    assert calls["timeout"] == 7.5
    assert calls["payload"]["model"] == "llama3.2:latest"
    assert calls["payload"]["stream"] is False
    assert calls["payload"]["format"] == "json"
    assert calls["payload"]["options"] == {"temperature": 0}
    assert calls["payload"]["messages"][0]["role"] == "system"
    assert "system prompt" in calls["payload"]["messages"][0]["content"]
    assert "JSON schema" in calls["payload"]["messages"][0]["content"]
    assert calls["payload"]["messages"][1] == {
        "role": "user",
        "content": "user content",
    }


def test_structured_llm_ollama_rejects_invalid_content_json(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def read(self):
            return json.dumps({"message": {"content": "not json"}}).encode("utf-8")

    monkeypatch.setenv("LLM_BACKEND", "ollama")
    monkeypatch.setattr(
        llm_backend_module.urllib.request,
        "urlopen",
        lambda request, *, timeout: FakeResponse(),
    )

    with pytest.raises(LLMProviderOutputError, match="not valid JSON"):
        call_structured_llm(
            system_prompt="system prompt",
            user_content="user content",
            response_model=JobAnalysis,
        )


def test_structured_llm_ollama_maps_request_error(monkeypatch):
    def fake_urlopen(request, *, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setenv("LLM_BACKEND", "ollama")
    monkeypatch.setattr(llm_backend_module.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(LLMProviderRequestError, match="Ollama request failed"):
        call_structured_llm(
            system_prompt="system prompt",
            user_content="user content",
            response_model=JobAnalysis,
        )
