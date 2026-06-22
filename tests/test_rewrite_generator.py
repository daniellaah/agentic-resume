import pytest

import app.llm_backend as llm_backend_module
import app.rewrite_generator as rewrite_generator_module
from app.models import (
    EvidenceMatch,
    JobAnalysis,
    JobRequirement,
    Resume,
    ResumeBullet,
    ResumeExperience,
    RewriteSuggestion,
)
from app.rewrite_generator import (
    MissingOpenAIAPIKeyError,
    RewriteOutputError,
    UnsafeRewriteError,
    build_rewrite_candidates,
    generate_rewrite_suggestions,
    parse_rewrite_payload,
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
                    ),
                    ResumeBullet(
                        id="exp_1_bullet_2",
                        text="Designed PostgreSQL tables and queries.",
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
                text="Design REST services with FastAPI.",
                priority="must_have",
            ),
            JobRequirement(
                id="req_3",
                text="Deploy services to Kubernetes.",
                priority="nice_to_have",
            ),
        ],
    )


def make_evidence_matches() -> list[EvidenceMatch]:
    return [
        EvidenceMatch(
            requirement_id="req_1",
            bullet_ids=["exp_1_bullet_1"],
            status="strong",
        ),
        EvidenceMatch(
            requirement_id="req_2",
            bullet_ids=["exp_1_bullet_1"],
            status="strong",
        ),
        EvidenceMatch(
            requirement_id="req_3",
            bullet_ids=[],
            status="missing",
        ),
    ]


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


def test_build_rewrite_candidates_groups_supported_requirements_by_bullet():
    candidates = build_rewrite_candidates(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
        evidence_matches=make_evidence_matches(),
    )

    assert len(candidates) == 1
    assert candidates[0].bullet_id == "exp_1_bullet_1"
    assert [requirement.id for requirement in candidates[0].requirements] == [
        "req_1",
        "req_2",
    ]


def test_build_rewrite_candidates_ignores_missing_evidence():
    candidates = build_rewrite_candidates(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
        evidence_matches=make_evidence_matches(),
    )

    candidate_requirement_ids = {
        requirement.id
        for candidate in candidates
        for requirement in candidate.requirements
    }

    assert "req_3" not in candidate_requirement_ids


def test_generate_rewrite_suggestions_uses_fake_provider():
    provider_calls = {}

    def fake_provider(candidates):
        provider_calls["candidates"] = candidates
        return valid_rewrite_payload()

    suggestions = generate_rewrite_suggestions(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
        evidence_matches=make_evidence_matches(),
        payload_provider=fake_provider,
    )

    assert provider_calls["candidates"][0].bullet_id == "exp_1_bullet_1"
    assert suggestions == [
        RewriteSuggestion(
            bullet_id="exp_1_bullet_1",
            rewritten_text="Built Python and FastAPI REST APIs for internal workflows.",
            requirement_ids=["req_1", "req_2"],
        )
    ]


def test_generate_rewrite_suggestions_returns_empty_without_candidates():
    def fake_provider(candidates):
        raise AssertionError("Provider should not be called without candidates.")

    suggestions = generate_rewrite_suggestions(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
        evidence_matches=[
            EvidenceMatch(
                requirement_id="req_3",
                bullet_ids=[],
                status="missing",
            )
        ],
        payload_provider=fake_provider,
    )

    assert suggestions == []


def test_parse_rewrite_payload_rejects_invalid_schema():
    with pytest.raises(RewriteOutputError, match="RewriteSuggestionBatch schema"):
        parse_rewrite_payload(
            {
                "suggestions": [
                    {
                        "bullet_id": "exp_1_bullet_1",
                        "rewritten_text": "",
                        "requirement_ids": ["req_1"],
                    }
                ]
            }
        )


def test_parse_rewrite_payload_rejects_empty_suggestions():
    with pytest.raises(RewriteOutputError, match="at least one suggestion"):
        parse_rewrite_payload({"suggestions": []})


def test_generate_rewrite_suggestions_rejects_unexpected_requirement():
    def fake_provider(candidates):
        return {
            "suggestions": [
                {
                    "bullet_id": "exp_1_bullet_1",
                    "rewritten_text": "Built APIs and deployed services to Kubernetes.",
                    "requirement_ids": ["req_1", "req_3"],
                }
            ]
        }

    with pytest.raises(RewriteOutputError, match="outside its evidence candidate"):
        generate_rewrite_suggestions(
            resume=make_resume(),
            job_analysis=make_job_analysis(),
            evidence_matches=make_evidence_matches(),
            payload_provider=fake_provider,
        )


def test_generate_rewrite_suggestions_rejects_missing_candidate_output():
    def fake_provider(candidates):
        return {
            "suggestions": [
                {
                    "bullet_id": "exp_1_bullet_2",
                    "rewritten_text": "Designed PostgreSQL tables and queries.",
                    "requirement_ids": ["req_1"],
                }
            ]
        }

    with pytest.raises(RewriteOutputError, match="exactly one suggestion"):
        generate_rewrite_suggestions(
            resume=make_resume(),
            job_analysis=make_job_analysis(),
            evidence_matches=make_evidence_matches(),
            payload_provider=fake_provider,
        )


def test_generate_rewrite_suggestions_rejects_validator_critical_issue():
    def fake_provider(candidates):
        return {
            "suggestions": [
                {
                    "bullet_id": "unknown_bullet",
                    "rewritten_text": "Built Python and FastAPI REST APIs.",
                    "requirement_ids": ["req_1"],
                }
            ]
        }

    with pytest.raises(RewriteOutputError, match="exactly one suggestion"):
        generate_rewrite_suggestions(
            resume=make_resume(),
            job_analysis=make_job_analysis(),
            evidence_matches=make_evidence_matches(),
            payload_provider=fake_provider,
        )


def test_generate_rewrite_suggestions_raises_unsafe_rewrite_error_for_bad_evidence():
    def fake_provider(candidates):
        return valid_rewrite_payload()

    with pytest.raises(UnsafeRewriteError, match="multiple evidence matches"):
        generate_rewrite_suggestions(
            resume=make_resume(),
            job_analysis=make_job_analysis(),
            evidence_matches=[
                EvidenceMatch(
                    requirement_id="req_1",
                    bullet_ids=["exp_1_bullet_1"],
                    status="strong",
                ),
                EvidenceMatch(
                    requirement_id="req_1",
                    bullet_ids=["exp_1_bullet_1"],
                    status="weak",
                ),
                EvidenceMatch(
                    requirement_id="req_2",
                    bullet_ids=["exp_1_bullet_1"],
                    status="strong",
                ),
            ],
            payload_provider=fake_provider,
        )


def test_generate_rewrite_suggestions_default_provider_rejects_missing_api_key(
    monkeypatch,
):
    class FakeOpenAI:
        def __init__(self, *, api_key):
            raise AssertionError("OpenAI client should not be created without a key.")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_BACKEND", "openai")
    monkeypatch.setattr(llm_backend_module, "OpenAI", FakeOpenAI)

    with pytest.raises(MissingOpenAIAPIKeyError, match="OPENAI_API_KEY"):
        generate_rewrite_suggestions(
            resume=make_resume(),
            job_analysis=make_job_analysis(),
            evidence_matches=make_evidence_matches(),
        )


def test_generate_rewrite_suggestions_uses_default_openai_provider(monkeypatch):
    calls = {}

    class FakeResponses:
        def parse(self, *, model, input, text_format):
            calls["model"] = model
            calls["input"] = input
            calls["text_format"] = text_format

            class FakeResponse:
                output_parsed = rewrite_generator_module.RewriteSuggestionBatch(
                    **valid_rewrite_payload()
                )

            return FakeResponse()

    class FakeOpenAI:
        def __init__(self, *, api_key):
            calls["api_key"] = api_key
            self.responses = FakeResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("OPENAI_MODEL_NAME", "test-model")
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    monkeypatch.setattr(llm_backend_module, "OpenAI", FakeOpenAI)

    suggestions = generate_rewrite_suggestions(
        resume=make_resume(),
        job_analysis=make_job_analysis(),
        evidence_matches=make_evidence_matches(),
    )

    assert suggestions[0].bullet_id == "exp_1_bullet_1"
    assert calls["api_key"] == "test-api-key"
    assert calls["model"] == "test-model"
    assert calls["text_format"] is rewrite_generator_module.RewriteSuggestionBatch
    assert calls["input"][0]["role"] == "system"
    assert calls["input"][1]["role"] == "user"
