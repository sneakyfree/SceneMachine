"""Tests for analytics.setBudget + analytics.getBudget IPC handlers.

Closes the regression window on P0-8: both handlers were absent and
the desktop cost-dashboard's budget widget hit "unknown method" on
mount AND on save. The persistence side is tested by
`tests/integration/test_migration_008_cost_budget.py`; this file
covers handler wiring + validation.
"""

from __future__ import annotations

import pytest

from scenemachine.ipc.handlers import register_handlers
from scenemachine.ipc.server import IPCServer


@pytest.fixture
def ipc_server() -> IPCServer:
    server = IPCServer("/tmp/test_analytics_budget.sock")
    register_handlers(server)
    return server


def test_both_handlers_registered(ipc_server: IPCServer) -> None:
    """P0-8 regression guard: both channels must exist."""
    assert "analytics.getBudget" in ipc_server.handlers
    assert "analytics.setBudget" in ipc_server.handlers


async def test_set_budget_rejects_zero_or_negative(ipc_server: IPCServer) -> None:
    handler = ipc_server.handlers["analytics.setBudget"]
    with pytest.raises(ValueError, match="must be > 0"):
        await handler(limit_usd=0.0)
    with pytest.raises(ValueError, match="must be > 0"):
        await handler(limit_usd=-10.0)


async def test_set_budget_rejects_out_of_range_period(ipc_server: IPCServer) -> None:
    handler = ipc_server.handlers["analytics.setBudget"]
    with pytest.raises(ValueError, match="period_days"):
        await handler(limit_usd=100.0, period_days=0)
    with pytest.raises(ValueError, match="period_days"):
        await handler(limit_usd=100.0, period_days=400)


async def test_get_budget_uses_default_when_no_settings_row(
    ipc_server: IPCServer, db_session
) -> None:
    """Fresh DB with no user_settings row: getBudget returns has_budget=False."""
    from contextlib import asynccontextmanager
    from unittest.mock import MagicMock, patch

    @asynccontextmanager
    async def _session_cm():
        yield db_session

    fake_db = MagicMock()
    fake_db.session = _session_cm

    handler = ipc_server.handlers["analytics.getBudget"]
    with patch(
        "scenemachine.ipc.handlers.get_db_manager",
        return_value=fake_db,
    ):
        result = await handler()

    assert result["budget"]["has_budget"] is False
    assert result["budget"]["limit_usd"] is None
    assert result["budget"]["status"] == "no_budget"
    assert result["currentSpend"] == 0.0
    assert result["budgetAlert"] is None


async def test_set_then_get_roundtrip(ipc_server: IPCServer, db_session) -> None:
    """setBudget persists; getBudget reads back the same value."""
    from contextlib import asynccontextmanager
    from unittest.mock import MagicMock, patch

    @asynccontextmanager
    async def _session_cm():
        yield db_session

    fake_db = MagicMock()
    fake_db.session = _session_cm

    set_handler = ipc_server.handlers["analytics.setBudget"]
    get_handler = ipc_server.handlers["analytics.getBudget"]

    with patch(
        "scenemachine.ipc.handlers.get_db_manager",
        return_value=fake_db,
    ):
        set_result = await set_handler(limit_usd=150.0, period_days=14)
        assert set_result == {
            "success": True,
            "limit_usd": 150.0,
            "period_days": 14,
        }

        get_result = await get_handler()

    assert get_result["budget"]["has_budget"] is True
    assert get_result["budget"]["limit_usd"] == 150.0
    assert get_result["budget"]["period_days"] == 14
    # No spend yet → percent_used should be 0
    assert get_result["budget"]["percent_used"] == 0.0
    assert get_result["budget"]["remaining_usd"] == 150.0
    assert get_result["budget"]["status"] == "ok"


async def test_set_budget_overwrites_existing(ipc_server: IPCServer, db_session) -> None:
    """Calling setBudget twice updates the same row (no duplicate inserts)."""
    from contextlib import asynccontextmanager
    from unittest.mock import MagicMock, patch

    from sqlalchemy import func, select

    from scenemachine.models.settings import UserSettings

    @asynccontextmanager
    async def _session_cm():
        yield db_session

    fake_db = MagicMock()
    fake_db.session = _session_cm

    set_handler = ipc_server.handlers["analytics.setBudget"]
    with patch(
        "scenemachine.ipc.handlers.get_db_manager",
        return_value=fake_db,
    ):
        await set_handler(limit_usd=100.0)
        await set_handler(limit_usd=200.0)
        await set_handler(limit_usd=300.0, period_days=7)

    count = (
        await db_session.execute(
            select(func.count(UserSettings.id)).where(
                UserSettings.settings_key == "default",
            ),
        )
    ).scalar()
    assert count == 1, "should have exactly one default settings row"

    row = (
        await db_session.execute(
            select(UserSettings).where(UserSettings.settings_key == "default"),
        )
    ).scalar_one()
    assert row.cost_budget_limit_usd == 300.0
    assert row.cost_budget_period_days == 7
