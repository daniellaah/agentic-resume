from pydantic import ValidationError

from app.models import Resume
from app.parsers import parse_sample_resume

SUPPORTED_RESUME_INPUT_FORMAT = "structured_text_v1"


class ResumeInputError(ValueError):
    """Raised when resume input cannot be parsed with the supported format."""


def parse_resume_text(text: str) -> Resume:
    if not text.strip():
        raise ResumeInputError("Resume text must not be empty.")

    try:
        return parse_sample_resume(text)
    except (ValueError, ValidationError) as error:
        raise ResumeInputError(
            "Resume text must use the structured_text_v1 format with Summary, "
            "Skills, Experience, dated experience entries, and stable bullet IDs."
        ) from error
