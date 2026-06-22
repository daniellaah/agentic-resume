from app.worker import (
    DEFAULT_AGENT_JOB_QUEUE_NAME,
    DEFAULT_REDIS_URL,
    get_worker_settings,
)


def test_get_worker_settings_uses_defaults():
    settings = get_worker_settings({})

    assert settings.queue_name == DEFAULT_AGENT_JOB_QUEUE_NAME
    assert settings.redis_url == DEFAULT_REDIS_URL


def test_get_worker_settings_reads_environment_overrides():
    settings = get_worker_settings(
        {
            "AGENT_JOB_QUEUE_NAME": "custom-agent-queue",
            "REDIS_URL": "redis://redis:6379/2",
        }
    )

    assert settings.queue_name == "custom-agent-queue"
    assert settings.redis_url == "redis://redis:6379/2"
