# Agentic Resume

An agentic resume tailoring tool that generates evidence-grounded resume variants for different job descriptions.

## Local Setup

```bash
uv sync
```

Create a local `.env` file:

```text
OPENAI_API_KEY=...
OPENAI_MODEL_NAME=gpt-5.5
```

## Run the API

```bash
uv run --env-file .env uvicorn app.api:app --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Interactive API docs:

```text
http://127.0.0.1:8000/docs
```

Run a sample tailoring request:

```bash
bash examples/curl_tailor.sh
```

## Run the Trace Viewer

```bash
cd frontend
npm ci
AGENTIC_RESUME_API_URL=http://127.0.0.1:8000 npm run dev
```

Open:

```text
http://127.0.0.1:3000
```

## Test

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
cd frontend && npm run typecheck && npm run build
```
