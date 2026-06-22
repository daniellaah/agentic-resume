import re

from app.models import Resume, ResumeBullet, ResumeExperience

BULLET_PATTERN = re.compile(r"^- \[(?P<id>[^\]]+)\] (?P<text>.+)$")


def parse_sample_resume(text: str) -> Resume:
    lines = [line.strip() for line in text.splitlines()]

    summary_start = _find_heading(lines, "Summary") + 1
    skills_start = _find_heading(lines, "Skills")
    experience_start = _find_heading(lines, "Experience")

    summary = _join_section_lines(lines[summary_start:skills_start])
    skills = _parse_skills(lines[skills_start + 1 : experience_start])
    experience = _parse_experience(lines[experience_start + 1 :])

    return Resume(summary=summary, skills=skills, experience=experience)


def _find_heading(lines: list[str], heading: str) -> int:
    try:
        return lines.index(heading)
    except ValueError as error:
        raise ValueError(f"Missing required heading: {heading}") from error


def _join_section_lines(lines: list[str]) -> str | None:
    content = " ".join(line for line in lines if line)
    return content or None


def _parse_skills(lines: list[str]) -> list[str]:
    skills_text = " ".join(line for line in lines if line)
    if not skills_text:
        return []

    return [skill.strip() for skill in skills_text.split(",") if skill.strip()]


def _parse_experience(lines: list[str]) -> list[ResumeExperience]:
    experiences: list[ResumeExperience] = []
    current_header: str | None = None
    current_dates: str | None = None
    current_bullets: list[ResumeBullet] = []

    for line in [line for line in lines if line]:
        bullet_match = BULLET_PATTERN.match(line)
        if bullet_match:
            current_bullets.append(
                ResumeBullet(
                    id=bullet_match.group("id"),
                    text=bullet_match.group("text"),
                )
            )
            continue

        if current_header is None:
            current_header = line
            continue

        if current_dates is None:
            current_dates = line
            continue

        experiences.append(
            _build_experience(
                index=len(experiences) + 1,
                header=current_header,
                dates=current_dates,
                bullets=current_bullets,
            )
        )
        current_header = line
        current_dates = None
        current_bullets = []

    if current_header is not None and current_dates is not None:
        experiences.append(
            _build_experience(
                index=len(experiences) + 1,
                header=current_header,
                dates=current_dates,
                bullets=current_bullets,
            )
        )

    return experiences


def _build_experience(
    index: int,
    header: str,
    dates: str,
    bullets: list[ResumeBullet],
) -> ResumeExperience:
    company, title = _parse_experience_header(header)
    start_date, end_date = _parse_date_range(dates)

    return ResumeExperience(
        id=f"exp_{index}",
        company=company,
        title=title,
        start_date=start_date,
        end_date=end_date,
        bullets=bullets,
    )


def _parse_experience_header(header: str) -> tuple[str, str]:
    if " - " not in header:
        raise ValueError(f"Invalid experience header: {header}")

    company, title = header.split(" - ", maxsplit=1)
    return company, title


def _parse_date_range(dates: str) -> tuple[str, str | None]:
    if " - " not in dates:
        raise ValueError(f"Invalid date range: {dates}")

    start_date, end_date = dates.split(" - ", maxsplit=1)
    return start_date, None if end_date == "Present" else end_date
