from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_dockerfile_uses_uv_and_starts_api():
    dockerfile = (ROOT_DIR / "Dockerfile").read_text()

    assert "ghcr.io/astral-sh/uv:python3.12" in dockerfile
    assert "uv sync --frozen --no-dev" in dockerfile
    assert 'CMD ["uvicorn", "app.api:app"' in dockerfile


def test_docker_compose_defines_api_worker_redis_and_postgres_services():
    compose = (ROOT_DIR / "docker-compose.yml").read_text()

    for service_name in ("api:", "worker:", "migrate:", "redis:", "postgres:"):
        assert service_name in compose

    assert "python -m app.worker" in compose
    assert "alembic upgrade head" in compose
    assert "postgresql+psycopg://agentic_resume" in compose
    assert "redis://redis:6379/0" in compose
    assert "pg_isready -U agentic_resume -d agentic_resume" in compose


def test_env_example_includes_runtime_connection_settings():
    env_example = (ROOT_DIR / ".env.example").read_text()

    assert "DATABASE_URL=sqlite:///agentic_resume.db" in env_example
    assert "REDIS_URL=redis://localhost:6379/0" in env_example
    assert "AGENT_JOB_QUEUE_NAME=agentic-tailoring" in env_example


def test_dockerignore_excludes_local_state_and_secrets():
    dockerignore = (ROOT_DIR / ".dockerignore").read_text()

    for ignored_path in (".env", ".venv", ".git", "data/private"):
        assert ignored_path in dockerignore
