import json
import os
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any, Literal

from openai import OpenAI
from pydantic import BaseModel

DEFAULT_LLM_BACKEND = "openai"
DEFAULT_OPENAI_MODEL = "gpt-5.5"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2:latest"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 120.0

LLM_BACKEND_ENV = "LLM_BACKEND"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_MODEL_ENV = "OPENAI_MODEL_NAME"
OLLAMA_BASE_URL_ENV = "OLLAMA_BASE_URL"
OLLAMA_MODEL_ENV = "OLLAMA_MODEL"
OLLAMA_TIMEOUT_SECONDS_ENV = "OLLAMA_TIMEOUT_SECONDS"

LLMBackendName = Literal["openai", "ollama"]


class LLMBackendError(Exception):
    """Base error for LLM backend failures."""


class LLMBackendConfigurationError(LLMBackendError, RuntimeError):
    """Raised when LLM backend configuration is invalid."""


class MissingOpenAIAPIKeyError(LLMBackendConfigurationError):
    """Raised when the OpenAI backend is used without an API key."""


class LLMProviderRequestError(LLMBackendError, RuntimeError):
    """Raised when an LLM backend request fails."""


class LLMProviderOutputError(LLMBackendError, ValueError):
    """Raised when an LLM backend returns unusable structured output."""


def call_structured_llm(
    *,
    system_prompt: str,
    user_content: str,
    response_model: type[BaseModel],
) -> dict[str, Any]:
    backend = _get_llm_backend()
    if backend == "openai":
        return _call_openai_structured_output(
            system_prompt=system_prompt,
            user_content=user_content,
            response_model=response_model,
        )
    if backend == "ollama":
        return _call_ollama_structured_output(
            system_prompt=system_prompt,
            user_content=user_content,
            response_model=response_model,
        )

    raise LLMBackendConfigurationError(f"Unsupported LLM backend: {backend}.")


def _get_llm_backend() -> str:
    return os.environ.get(LLM_BACKEND_ENV, DEFAULT_LLM_BACKEND).strip().lower()


def _call_openai_structured_output(
    *,
    system_prompt: str,
    user_content: str,
    response_model: type[BaseModel],
) -> dict[str, Any]:
    api_key = _get_openai_api_key()
    client = OpenAI(api_key=api_key)

    response = client.responses.parse(
        model=os.environ.get(OPENAI_MODEL_ENV, DEFAULT_OPENAI_MODEL),
        input=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_content,
            },
        ],
        text_format=response_model,
    )

    parsed_output = response.output_parsed
    if parsed_output is None:
        raise LLMProviderOutputError(
            "OpenAI response did not include parsed structured output."
        )

    return parsed_output.model_dump()


def _call_ollama_structured_output(
    *,
    system_prompt: str,
    user_content: str,
    response_model: type[BaseModel],
) -> dict[str, Any]:
    request_payload = {
        "model": os.environ.get(OLLAMA_MODEL_ENV, DEFAULT_OLLAMA_MODEL),
        "stream": False,
        "format": "json",
        "messages": [
            {
                "role": "system",
                "content": _ollama_system_prompt(system_prompt, response_model),
            },
            {
                "role": "user",
                "content": user_content,
            },
        ],
        "options": {
            "temperature": 0,
        },
    }
    request_body = json.dumps(request_payload).encode("utf-8")
    request = urllib.request.Request(
        _ollama_chat_url(),
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(  # noqa: S310 - URL is local/user-configured.
            request,
            timeout=_get_ollama_timeout_seconds(),
        ) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, TimeoutError) as error:
        raise LLMProviderRequestError(f"Ollama request failed: {error}") from error
    except json.JSONDecodeError as error:
        raise LLMProviderOutputError("Ollama response was not valid JSON.") from error

    content = _ollama_response_content(response_payload)
    try:
        parsed_content = json.loads(content)
    except json.JSONDecodeError as error:
        raise LLMProviderOutputError(
            "Ollama structured output was not valid JSON."
        ) from error

    if not isinstance(parsed_content, dict):
        raise LLMProviderOutputError("Ollama structured output must be a JSON object.")

    return parsed_content


def _get_openai_api_key() -> str:
    api_key = os.environ.get(OPENAI_API_KEY_ENV)
    if not api_key:
        raise MissingOpenAIAPIKeyError(
            f"{OPENAI_API_KEY_ENV} must be set when LLM_BACKEND=openai."
        )
    return api_key


def _ollama_system_prompt(
    system_prompt: str,
    response_model: type[BaseModel],
) -> str:
    return "\n\n".join(
        [
            system_prompt,
            "Return only valid JSON. Do not include markdown or commentary.",
            "The JSON object must match this JSON schema:",
            json.dumps(response_model.model_json_schema(), indent=2),
        ]
    )


def _ollama_chat_url() -> str:
    base_url = os.environ.get(OLLAMA_BASE_URL_ENV, DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    return f"{base_url}/api/chat"


def _get_ollama_timeout_seconds() -> float:
    raw_timeout = os.environ.get(OLLAMA_TIMEOUT_SECONDS_ENV)
    if raw_timeout is None:
        return DEFAULT_OLLAMA_TIMEOUT_SECONDS

    try:
        timeout = float(raw_timeout)
    except ValueError as error:
        raise LLMBackendConfigurationError(
            f"{OLLAMA_TIMEOUT_SECONDS_ENV} must be a number."
        ) from error

    if timeout <= 0:
        raise LLMBackendConfigurationError(
            f"{OLLAMA_TIMEOUT_SECONDS_ENV} must be greater than 0."
        )
    return timeout


def _ollama_response_content(response_payload: Mapping[str, Any]) -> str:
    message = response_payload.get("message")
    if not isinstance(message, Mapping):
        raise LLMProviderOutputError("Ollama response did not include a message.")

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise LLMProviderOutputError("Ollama response message did not include content.")

    return content
