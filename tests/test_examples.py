import json
from pathlib import Path

from app.api import TailorRequest
from app.resume_input import parse_resume_text

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_tailor_request_example_matches_api_request_schema():
    payload = json.loads((ROOT_DIR / "examples" / "tailor_request.json").read_text())

    request = TailorRequest.model_validate(payload)

    assert "Backend Engineer" in request.job_description_text
    assert parse_resume_text(request.resume_text).experience


def test_curl_tailor_example_targets_tailor_endpoint():
    script = (ROOT_DIR / "examples" / "curl_tailor.sh").read_text()

    assert "examples/tailor_request.json" in script
    assert "${API_URL}/tailor" in script
    assert "Content-Type: application/json" in script
