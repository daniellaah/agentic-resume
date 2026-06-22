from pathlib import Path

import pytest

from app.parsers import parse_sample_resume

ROOT_DIR = Path(__file__).resolve().parents[1]


def read_sample_resume() -> str:
    return (ROOT_DIR / "data" / "sample_resume.txt").read_text()


def test_parse_sample_resume_extracts_summary_and_skills():
    resume = parse_sample_resume(read_sample_resume())

    assert resume.summary == (
        "Backend-focused software engineer with experience building Python "
        "services, internal APIs, and data-backed product workflows."
    )
    assert resume.skills == [
        "Python",
        "FastAPI",
        "PostgreSQL",
        "pytest",
        "Docker",
        "React",
    ]


def test_parse_sample_resume_extracts_experience_sections():
    resume = parse_sample_resume(read_sample_resume())

    assert len(resume.experience) == 2
    assert resume.experience[0].id == "exp_1"
    assert resume.experience[0].company == "Acme Analytics"
    assert resume.experience[0].title == "Software Engineer"
    assert resume.experience[0].start_date == "2024-01"
    assert resume.experience[0].end_date is None
    assert resume.experience[1].id == "exp_2"
    assert resume.experience[1].company == "Campus Projects"
    assert resume.experience[1].title == "Full-Stack Developer"
    assert resume.experience[1].start_date == "2023-01"
    assert resume.experience[1].end_date == "2023-12"


def test_parse_sample_resume_preserves_stable_bullet_ids():
    resume = parse_sample_resume(read_sample_resume())

    first_experience_bullets = resume.experience[0].bullets
    second_experience_bullets = resume.experience[1].bullets

    assert [bullet.id for bullet in first_experience_bullets] == [
        "exp_1_bullet_1",
        "exp_1_bullet_2",
        "exp_1_bullet_3",
    ]
    assert second_experience_bullets[0].id == "exp_2_bullet_1"
    assert first_experience_bullets[0].text == (
        "Built internal REST APIs using Python and FastAPI to support analyst "
        "workflows."
    )


def test_parse_sample_resume_rejects_missing_required_heading():
    with pytest.raises(ValueError, match="Missing required heading: Skills"):
        parse_sample_resume(
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


def test_parse_sample_resume_rejects_invalid_experience_header():
    with pytest.raises(ValueError, match="Invalid experience header"):
        parse_sample_resume(
            """
            Sample Candidate

            Summary
            Backend engineer.

            Skills
            Python

            Experience
            Acme Engineer
            2024-01 - Present
            - [exp_1_bullet_1] Built APIs.
            """
        )
