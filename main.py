import asyncio
import logging
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.asyncio import AsyncioIntegration

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlmodel import Session

from app.core.database import engine
from app.orchestrator import Orchestrator
from config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()]
)

sentry_sdk.init(
    dsn=config.sentry_dsn,
    integrations=[
        LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        AsyncioIntegration(),
    ],
    traces_sample_rate=0.2,
)

async def main():
    async def run_cycle():
        with Session(engine) as session:
            await Orchestrator(session).run()
        
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_cycle,
        'interval',
        minutes=config.polling_interval,
        max_instances=1,
        misfire_grace_time=30
    )
    scheduler.start()
    logging.info("Agent started, waiting for emails...")

    await asyncio.Event().wait()

asyncio.run(main())
