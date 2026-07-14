"""In-app scheduler for the deployed environment (Render free tier).

Locally these jobs are owned by the Airflow DAGs instead — enable with
ENABLE_SCHEDULER=true (set on Render, unset in docker-compose).
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.session import AsyncSessionLocal
from app.services.data_refresh import refresh_sample_data

log = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


async def _reindex_schema_job() -> None:
    from app.services.rag_service import reindex_schema

    async with AsyncSessionLocal() as db:
        count = await reindex_schema(db)
    log.info("Schema embeddings reindexed: %d docs", count)


def start_scheduler() -> None:
    scheduler.add_job(
        refresh_sample_data,
        CronTrigger(hour=3, minute=0),  # daily 03:00 UTC, mirrors the Airflow DAG
        id="refresh_sample_data",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _reindex_schema_job,
        CronTrigger(day_of_week="sun", hour=4, minute=0),  # weekly, mirrors the DAG
        id="schema_embedding_refresh",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    log.info("APScheduler started (daily data refresh, weekly embedding refresh)")
