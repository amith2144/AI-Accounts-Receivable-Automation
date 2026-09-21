from app.workers.celery_app import celery_app, ping_task


def test_celery_configuration_and_serialization():
    # 1. Assert JSON serialization strictly configured
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert "json" in celery_app.conf.accept_content

    # 2. Assert reliability settings
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.task_time_limit == 600

    # 3. Assert ping task callable
    assert ping_task() == "pong"

    # 4. Assert Celery Beat periodic schedules
    beat_schedule = celery_app.conf.beat_schedule
    assert "nightly-aging-recalculation" in beat_schedule
    assert beat_schedule["nightly-aging-recalculation"]["task"] == "app.workers.tasks_cadence.recalculate_aging_nightly"
    assert "daily-cadence-reminder-dispatch" in beat_schedule
    assert beat_schedule["daily-cadence-reminder-dispatch"]["task"] == "app.workers.tasks_cadence.dispatch_scheduled_cadences"
