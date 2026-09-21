import logging
from celery import Celery
from app.core.config import settings

logger = logging.getLogger("app.workers.celery")

# Initialize Celery application with Redis broker and result backend
celery_app = Celery(
    "ar_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

from celery.schedules import crontab

# Production Celery Configuration
celery_app.conf.update(
    # Serialization & Security: JSON strictly enforced (no pickle)
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,

    # Reliability & Execution Controls
    task_track_started=True,
    task_acks_late=True,                 # Re-queue task if worker dies mid-execution
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,        # Prevents worker greedily starving parallel workers
    task_time_limit=600,                 # Hard 10-minute timeout for CPU-bound OCR
    task_soft_time_limit=540,            # 9-minute soft warning threshold

    # Queue Routing
    task_routes={
        "app.workers.tasks_extraction.*": {"queue": "document_extraction"},
        "app.workers.tasks_cadence.*": {"queue": "cadence_automation"},
    },

    # Celery Beat Periodic Schedules
    beat_schedule={
        "nightly-aging-recalculation": {
            "task": "app.workers.tasks_cadence.recalculate_aging_nightly",
            "schedule": crontab(hour=0, minute=5),
        },
        "daily-cadence-reminder-dispatch": {
            "task": "app.workers.tasks_cadence.dispatch_scheduled_cadences",
            "schedule": crontab(hour=8, minute=0),
        },
    },
)

# Autodiscover background task modules
celery_app.autodiscover_tasks(["app.workers"])


@celery_app.task(name="app.workers.celery_app.ping")
def ping_task() -> str:
    """Worker liveness and connectivity verification probe."""
    return "pong"
