import asyncio
import logging
from typing import Any, Dict
from celery import Task

from app.database.session import AsyncSessionLocal
from app.services.aging_service import AgingService
from app.services.cadence_service import CadenceService
from app.workers.celery_app import celery_app

logger = logging.getLogger("app.workers.cadence")


async def _async_recalculate_aging() -> Dict[str, Any]:
    """Asynchronously evaluate all active invoices and update aging bucket snapshots."""
    async with AsyncSessionLocal() as session:
        service = AgingService(session)
        result = await service.recalculate_all_active_invoices()
        await session.commit()
        return result


async def _async_dispatch_cadences() -> Dict[str, Any]:
    """Asynchronously evaluate active reminder rules and dispatch queued emails."""
    async with AsyncSessionLocal() as session:
        service = CadenceService(session)
        summary = await service.evaluate_and_dispatch_cadences()
        await session.commit()
        return summary.model_dump()


@celery_app.task(
    name="app.workers.tasks_cadence.recalculate_aging_nightly",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def recalculate_aging_nightly(self: Task) -> Dict[str, Any]:
    """
    Nightly Celery Beat task to recompute days overdue and assign invoices
    to aging buckets across the entire active ledger.
    """
    logger.info("Starting scheduled nightly aging recalculation batch...")
    try:
        result = asyncio.run(_async_recalculate_aging())
        logger.info(f"Nightly aging recalculation completed successfully: {result}")
        return result
    except Exception as exc:
        logger.exception(f"Nightly aging recalculation encountered failure: {str(exc)}")
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.workers.tasks_cadence.dispatch_scheduled_cadences",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def dispatch_scheduled_cadences(self: Task) -> Dict[str, Any]:
    """
    Scheduled Celery Beat task to evaluate active cadence rules,
    throttle duplicate notices, and dispatch automated reminder emails.
    """
    logger.info("Starting scheduled cadence reminder dispatch batch...")
    try:
        result = asyncio.run(_async_dispatch_cadences())
        logger.info(f"Cadence dispatch batch completed successfully: {result}")
        return result
    except Exception as exc:
        logger.exception(f"Cadence dispatch batch encountered failure: {str(exc)}")
        raise self.retry(exc=exc)
