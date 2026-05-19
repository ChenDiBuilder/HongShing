"""Background worker entrypoint — processes jobs from SQS."""

import asyncio
import logging
import os

log = logging.getLogger("worker")
log.setLevel(logging.INFO)


async def main():
    """Main worker loop. In v0.1, runs jobs on a timer without SQS."""
    from app.config import get_settings

    settings = get_settings()

    if settings.app_env in ("development", "testing"):
        log.info("Worker running in dev mode — using timer loop")

    while True:
        # Placeholder: in production, poll SQS instead of timer
        await asyncio.sleep(60)
        log.debug("Worker tick")


if __name__ == "__main__":
    asyncio.run(main())
