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
    assert "LLM_BACKEND: ${LLM_BACKEND:-openai}" in compose
    assert "OLLAMA_BASE_URL: ${OLLAMA_BASE_URL:-http://host.docker.internal:11434}" in (
        compose
    )
    assert "OLLAMA_MODEL: ${OLLAMA_MODEL:-llama3.2:latest}" in compose
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
    assert '"@tanstack/react-query":' in package_json


def test_frontend_defines_agent_run_intake_flow():
    workspace = (ROOT_DIR / "frontend" / "app" / "agent-run-workspace.tsx").read_text()
    route_handler = (
        ROOT_DIR / "frontend" / "app" / "agent-runs" / "route.ts"
    ).read_text()
    api_client = (ROOT_DIR / "frontend" / "lib" / "api.ts").read_text()

    assert 'action="/agent-runs"' in workspace
    assert 'name="resumeText"' in workspace
    assert 'name="jobDescriptionText"' in workspace
    assert 'name="maxAttempts"' in workspace
    assert "createAgentRun" in route_handler
    assert 'url.searchParams.set("jobId", result.job.job_id)' in route_handler
    assert "POST" in api_client
    assert "`${API_URL}/agent-runs`" in api_client


def test_frontend_defines_live_trace_monitoring_flow():
    workspace = (ROOT_DIR / "frontend" / "app" / "agent-run-workspace.tsx").read_text()
    layout = (ROOT_DIR / "frontend" / "app" / "layout.tsx").read_text()
    query_provider = (ROOT_DIR / "frontend" / "app" / "query-provider.tsx").read_text()
    proxy_route = (
        ROOT_DIR / "frontend" / "app" / "agent-runs" / "[jobId]" / "trace" / "route.ts"
    ).read_text()
    client_api = (ROOT_DIR / "frontend" / "lib" / "client-api.ts").read_text()

    assert "QueryProvider" in layout
    assert "QueryClientProvider" in query_provider
    assert "useQuery<TraceLoadResult>" in workspace
    assert "TRACE_REFETCH_INTERVAL_MS" in workspace
    assert 'status === "queued" || status === "running"' in workspace
    assert "loadAgentRunTraceFromClient" in workspace
    assert "/agent-runs/${encodeURIComponent(normalizedJobId)}/trace" in client_api
    assert "loadAgentRunTrace(jobId)" in proxy_route


def test_frontend_dockerfile_builds_standalone_next_app():
    dockerfile = (ROOT_DIR / "frontend" / "Dockerfile").read_text()

    assert "node:24-alpine" in dockerfile
    assert "npm ci" in dockerfile
    assert "npm run build" in dockerfile
    assert 'CMD ["node", "server.js"]' in dockerfile


def test_env_example_includes_runtime_connection_settings():
    env_example = (ROOT_DIR / ".env.example").read_text()

    assert "LLM_BACKEND=openai" in env_example
    assert "OLLAMA_BASE_URL=http://host.docker.internal:11434" in env_example
    assert "OLLAMA_MODEL=llama3.2:latest" in env_example
    assert "OLLAMA_TIMEOUT_SECONDS=120" in env_example
    assert "RUN_OLLAMA_INTEGRATION=0" in env_example
    assert "DATABASE_URL=sqlite:///agentic_resume.db" in env_example
    assert "REDIS_URL=redis://localhost:6379/0" in env_example
    assert "AGENT_JOB_QUEUE_NAME=agentic-tailoring" in env_example
    assert "AGENTIC_RESUME_API_URL=http://127.0.0.1:8000" in env_example


def test_dockerignore_excludes_local_state_and_secrets():
    dockerignore = (ROOT_DIR / ".dockerignore").read_text()

    for ignored_path in (".env", ".venv", ".git", "data/private"):
        assert ignored_path in dockerignore
