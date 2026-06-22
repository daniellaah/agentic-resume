from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_dockerfile_uses_uv_and_starts_api():
    dockerfile = (ROOT_DIR / "Dockerfile").read_text()

    assert "ghcr.io/astral-sh/uv:python3.12" in dockerfile
    assert "uv sync --frozen --no-dev" in dockerfile
    assert 'CMD ["uvicorn", "app.api:app"' in dockerfile


def test_docker_compose_defines_api_worker_redis_and_postgres_services():
    compose = (ROOT_DIR / "docker-compose.yml").read_text()

    for service_name in (
        "api:",
        "frontend:",
        "worker:",
        "migrate:",
        "redis:",
        "postgres:",
    ):
        assert service_name in compose

    assert "python -m app.worker" in compose
    assert "alembic upgrade head" in compose
    assert "AGENTIC_RESUME_API_URL: http://api:8000" in compose
    assert '"3000:3000"' in compose
    assert "postgresql+psycopg://agentic_resume" in compose
    assert "redis://redis:6379/0" in compose
    assert "pg_isready -U agentic_resume -d agentic_resume" in compose


def test_frontend_package_defines_trace_viewer_runtime_scripts():
    package_json = (ROOT_DIR / "frontend" / "package.json").read_text()

    assert '"dev": "next dev --hostname 0.0.0.0 --port 3000"' in package_json
    assert '"build": "next build"' in package_json
    assert '"typecheck": "next typegen && tsc --noEmit"' in package_json
    assert '"next":' in package_json
    assert '"lucide-react":' in package_json


def test_frontend_defines_agent_run_intake_flow():
    page = (ROOT_DIR / "frontend" / "app" / "page.tsx").read_text()
    route_handler = (
        ROOT_DIR / "frontend" / "app" / "agent-runs" / "route.ts"
    ).read_text()
    api_client = (ROOT_DIR / "frontend" / "lib" / "api.ts").read_text()

    assert 'action="/agent-runs"' in page
    assert 'name="resumeText"' in page
    assert 'name="jobDescriptionText"' in page
    assert 'name="maxAttempts"' in page
    assert "createAgentRun" in route_handler
    assert 'url.searchParams.set("jobId", result.job.job_id)' in route_handler
    assert "POST" in api_client
    assert "`${API_URL}/agent-runs`" in api_client


def test_frontend_dockerfile_builds_standalone_next_app():
    dockerfile = (ROOT_DIR / "frontend" / "Dockerfile").read_text()

    assert "node:24-alpine" in dockerfile
    assert "npm ci" in dockerfile
    assert "npm run build" in dockerfile
    assert 'CMD ["node", "server.js"]' in dockerfile


def test_env_example_includes_runtime_connection_settings():
    env_example = (ROOT_DIR / ".env.example").read_text()

    assert "DATABASE_URL=sqlite:///agentic_resume.db" in env_example
    assert "REDIS_URL=redis://localhost:6379/0" in env_example
    assert "AGENT_JOB_QUEUE_NAME=agentic-tailoring" in env_example
    assert "AGENTIC_RESUME_API_URL=http://127.0.0.1:8000" in env_example


def test_dockerignore_excludes_local_state_and_secrets():
    dockerignore = (ROOT_DIR / ".dockerignore").read_text()

    for ignored_path in (".env", ".venv", ".git", "data/private"):
        assert ignored_path in dockerignore
