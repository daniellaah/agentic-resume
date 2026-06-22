from collections.abc import Mapping
from dataclasses import dataclass
from os import environ

from redis import Redis
from rq import Queue, Worker

DEFAULT_AGENT_JOB_QUEUE_NAME = "agentic-tailoring"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"


@dataclass(frozen=True)
class WorkerSettings:
    queue_name: str
    redis_url: str


def get_worker_settings(
    env: Mapping[str, str] = environ,
) -> WorkerSettings:
    return WorkerSettings(
        queue_name=env.get("AGENT_JOB_QUEUE_NAME", DEFAULT_AGENT_JOB_QUEUE_NAME),
        redis_url=env.get("REDIS_URL", DEFAULT_REDIS_URL),
    )


def build_worker(settings: WorkerSettings) -> Worker:
    connection = Redis.from_url(settings.redis_url)
    queue = Queue(settings.queue_name, connection=connection)
    return Worker([queue], connection=connection)


def main() -> None:
    build_worker(get_worker_settings()).work()


if __name__ == "__main__":
    main()
