from pathlib import Path

import pytest

from app.resume_input import (
    SUPPORTED_RESUME_INPUT_FORMAT,
    ResumeInputError,
    parse_resume_text,
)

ROOT_DIR = Path(__file__).resolve().parents[1]


def read_sample_resume() -> str:
    return (ROOT_DIR / "data" / "sample_resume.txt").read_text()


def test_parse_resume_text_accepts_supported_structured_text_format():
    resume = parse_resume_text(read_sample_resume())

    assert SUPPORTED_RESUME_INPUT_FORMAT == "structured_text_v1"
    assert resume.summary is not None
    assert resume.experience[0].bullets[0].id == "exp_1_bullet_1"


def test_parse_resume_text_rejects_empty_text():
    with pytest.raises(ResumeInputError, match="must not be empty"):
        parse_resume_text(" ")


def test_parse_resume_text_wraps_parser_errors():
    with pytest.raises(ResumeInputError, match="structured_text_v1 format"):
        parse_resume_text(
            """
            Sample Candidate

            Summary
            Backend engineer.

            Experience
            Acme - Engineer
            2024-01 - Present
            - [exp_1_bullet_1] Built APIs.
            """
        )
