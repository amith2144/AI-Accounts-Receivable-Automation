from unittest.mock import AsyncMock, patch
import pytest

from app.schemas.cadence import CadenceDispatchSummary
from app.workers.tasks_cadence import (
    dispatch_scheduled_cadences,
    recalculate_aging_nightly,
)


@patch("app.workers.tasks_cadence._async_recalculate_aging")
def test_recalculate_aging_nightly_task(mock_async_recalc):
    mock_async_recalc.return_value = {
        "evaluated_total": 5,
        "overdue_total": 2,
        "bucket_counts": {"CURRENT": 3, "DAYS_1_30": 2},
    }

    result = recalculate_aging_nightly()
    assert result["evaluated_total"] == 5
    assert result["overdue_total"] == 2
    mock_async_recalc.assert_called_once()


@patch("app.workers.tasks_cadence._async_dispatch_cadences")
def test_dispatch_scheduled_cadences_task(mock_async_dispatch):
    mock_async_dispatch.return_value = {
        "evaluated_cadences": 2,
        "scanned_invoices": 10,
        "dispatched_count": 3,
        "skipped_paused": 1,
        "throttled_count": 2,
        "errors": [],
    }

    result = dispatch_scheduled_cadences()
    assert result["evaluated_cadences"] == 2
    assert result["dispatched_count"] == 3
    mock_async_dispatch.assert_called_once()
