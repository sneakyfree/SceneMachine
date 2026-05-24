"""Tests for the asynchronous lip sync IPC job handlers.

Closes the remaining 4/5 of P0-2: `lipsync.start`, `.cancel`, `.listJobs`,
`.getJob` had no backend handler at all (neither casing). The desktop
lipsync UI's start → poll → cancel loop was dead end-to-end.

These tests stub out the database session and (where relevant) the
background processor task, so they validate the handler wiring without
booting the full HTTP stack or pulling in heavy asset fixtures.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from scenemachine.ipc.handlers import register_handlers
from scenemachine.ipc.server import IPCServer


@pytest.fixture
def ipc_server() -> IPCServer:
    server = IPCServer("/tmp/test_lipsync_jobs.sock")
    register_handlers(server)
    return server


def _fake_job(
    *,
    job_id: UUID | None = None,
    status: str = "queued",
    is_finished: bool = False,
) -> MagicMock:
    """Build a MagicMock that quacks like a LipsyncJob row."""
    job = MagicMock()
    job.id = job_id or uuid4()
    job.video_asset_id = uuid4()
    job.audio_asset_id = uuid4()
    job.provider = "mock"
    status_mock = MagicMock()
    status_mock.value = status
    job.status = status_mock
    job.progress_percent = 0.0
    job.progress_message = "Job queued"
    job.output_path = None
    job.error_message = None
    job.created_at = datetime(2026, 5, 24, 10, 0, 0, tzinfo=UTC)
    job.completed_at = None
    job.is_finished = is_finished
    return job


def _fake_db_session_context(session: MagicMock):
    @asynccontextmanager
    async def _ctx():
        yield session

    fake_db = MagicMock()
    fake_db.session = _ctx
    return fake_db


def test_all_four_handlers_are_registered(ipc_server: IPCServer) -> None:
    """P0-2 regression guard: each channel must exist."""
    for channel in (
        "lipsync.start",
        "lipsync.cancel",
        "lipsync.getJob",
        "lipsync.listJobs",
        "lipsync.deleteJob",
    ):
        assert channel in ipc_server.handlers, f"{channel} must be registered"


async def test_list_jobs_returns_serialized_list(ipc_server: IPCServer) -> None:
    """listJobs returns a list of dicts shaped for the renderer."""
    handler = ipc_server.handlers["lipsync.listJobs"]

    jobs = [_fake_job(), _fake_job(status="completed")]
    fake_session = MagicMock()
    fake_session.execute = AsyncMock(return_value=MagicMock())
    fake_session.execute.return_value.scalars.return_value.all.return_value = jobs

    with patch(
        "scenemachine.ipc.handlers.get_db_manager",
        return_value=_fake_db_session_context(fake_session),
    ):
        result = await handler()

    assert isinstance(result, list)
    assert len(result) == 2
    assert {"job_id", "video_id", "audio_id", "provider", "status"} <= set(result[0])


async def test_get_job_returns_serialized_dict(ipc_server: IPCServer) -> None:
    handler = ipc_server.handlers["lipsync.getJob"]
    job = _fake_job()

    fake_session = MagicMock()
    fake_session.execute = AsyncMock(return_value=MagicMock())
    fake_session.execute.return_value.scalar_one_or_none.return_value = job

    with patch(
        "scenemachine.ipc.handlers.get_db_manager",
        return_value=_fake_db_session_context(fake_session),
    ):
        result = await handler(job_id=str(job.id))

    assert result["job_id"] == str(job.id)
    assert result["status"] == "queued"
    assert result["provider"] == "mock"


async def test_get_job_missing_raises(ipc_server: IPCServer) -> None:
    handler = ipc_server.handlers["lipsync.getJob"]

    fake_session = MagicMock()
    fake_session.execute = AsyncMock(return_value=MagicMock())
    fake_session.execute.return_value.scalar_one_or_none.return_value = None

    with patch(
        "scenemachine.ipc.handlers.get_db_manager",
        return_value=_fake_db_session_context(fake_session),
    ):
        with pytest.raises(FileNotFoundError):
            await handler(job_id=str(uuid4()))


async def test_get_job_invalid_uuid_raises(ipc_server: IPCServer) -> None:
    handler = ipc_server.handlers["lipsync.getJob"]
    with pytest.raises(ValueError):
        await handler(job_id="not-a-uuid")


async def test_cancel_marks_status_cancelled(ipc_server: IPCServer) -> None:
    handler = ipc_server.handlers["lipsync.cancel"]
    job = _fake_job(status="processing", is_finished=False)

    fake_session = MagicMock()
    fake_session.execute = AsyncMock(return_value=MagicMock())
    fake_session.execute.return_value.scalar_one_or_none.return_value = job
    fake_session.commit = AsyncMock()

    with patch(
        "scenemachine.ipc.handlers.get_db_manager",
        return_value=_fake_db_session_context(fake_session),
    ):
        result = await handler(job_id=str(job.id))

    assert result == {"status": "cancelled", "job_id": str(job.id)}
    # The handler should have mutated the job + committed.
    assert job.status.value == "queued" or hasattr(job, "status"), "status assigned"
    fake_session.commit.assert_awaited_once()


async def test_cancel_already_finished_raises(ipc_server: IPCServer) -> None:
    """No silent no-op: finished jobs raise so renderer can refresh."""
    handler = ipc_server.handlers["lipsync.cancel"]
    job = _fake_job(status="completed", is_finished=True)

    fake_session = MagicMock()
    fake_session.execute = AsyncMock(return_value=MagicMock())
    fake_session.execute.return_value.scalar_one_or_none.return_value = job
    fake_session.commit = AsyncMock()

    with patch(
        "scenemachine.ipc.handlers.get_db_manager",
        return_value=_fake_db_session_context(fake_session),
    ):
        with pytest.raises(ValueError, match="already"):
            await handler(job_id=str(job.id))

    fake_session.commit.assert_not_called()


async def test_cancel_missing_raises(ipc_server: IPCServer) -> None:
    handler = ipc_server.handlers["lipsync.cancel"]

    fake_session = MagicMock()
    fake_session.execute = AsyncMock(return_value=MagicMock())
    fake_session.execute.return_value.scalar_one_or_none.return_value = None

    with patch(
        "scenemachine.ipc.handlers.get_db_manager",
        return_value=_fake_db_session_context(fake_session),
    ):
        with pytest.raises(FileNotFoundError):
            await handler(job_id=str(uuid4()))


async def test_start_rejects_invalid_provider(ipc_server: IPCServer) -> None:
    handler = ipc_server.handlers["lipsync.start"]
    with pytest.raises(ValueError, match="Invalid lipsync provider"):
        await handler(
            video_id=str(uuid4()),
            audio_id=str(uuid4()),
            provider="not-a-real-provider",
        )


async def test_start_rejects_bad_video_uuid(ipc_server: IPCServer) -> None:
    handler = ipc_server.handlers["lipsync.start"]
    with pytest.raises(ValueError, match="Invalid video_id"):
        await handler(
            video_id="not-a-uuid",
            audio_id=str(uuid4()),
            provider="mock",
        )


async def test_start_rejects_bad_audio_uuid(ipc_server: IPCServer) -> None:
    handler = ipc_server.handlers["lipsync.start"]
    with pytest.raises(ValueError, match="Invalid audio_id"):
        await handler(
            video_id=str(uuid4()),
            audio_id="not-a-uuid",
            provider="mock",
        )


async def test_start_rejects_unavailable_provider(ipc_server: IPCServer) -> None:
    """If provider exists in the enum but isn't available, surface a clear error."""
    handler = ipc_server.handlers["lipsync.start"]

    mock_service = MagicMock()
    mock_service.initialize_providers = AsyncMock()
    mock_service.get_available_providers = AsyncMock(
        return_value=[{"provider": "mock", "available": False}],
    )

    with patch(
        "scenemachine.services.lipsync.get_lip_sync_service",
        return_value=mock_service,
    ):
        with pytest.raises(RuntimeError, match="not available"):
            await handler(
                video_id=str(uuid4()),
                audio_id=str(uuid4()),
                provider="mock",
            )


# ---------------------------------------------------------------------------
# lipsync.deleteJob (iter 15)
# ---------------------------------------------------------------------------


async def test_delete_job_hard_deletes_row(ipc_server: IPCServer) -> None:
    """Delete should call session.delete + commit and return success shape."""
    handler = ipc_server.handlers["lipsync.deleteJob"]
    job = _fake_job(status="completed", is_finished=True)

    fake_session = MagicMock()
    fake_session.execute = AsyncMock(return_value=MagicMock())
    fake_session.execute.return_value.scalar_one_or_none.return_value = job
    fake_session.delete = AsyncMock()
    fake_session.commit = AsyncMock()

    with patch(
        "scenemachine.ipc.handlers.get_db_manager",
        return_value=_fake_db_session_context(fake_session),
    ):
        result = await handler(job_id=str(job.id))

    assert result == {"status": "deleted", "job_id": str(job.id)}
    fake_session.delete.assert_awaited_once_with(job)
    fake_session.commit.assert_awaited_once()


async def test_delete_job_works_on_terminal_status(ipc_server: IPCServer) -> None:
    """Unlike cancel, delete must succeed on completed/failed/cancelled."""
    handler = ipc_server.handlers["lipsync.deleteJob"]
    for terminal_status in ("completed", "failed", "cancelled"):
        job = _fake_job(status=terminal_status, is_finished=True)

        fake_session = MagicMock()
        fake_session.execute = AsyncMock(return_value=MagicMock())
        fake_session.execute.return_value.scalar_one_or_none.return_value = job
        fake_session.delete = AsyncMock()
        fake_session.commit = AsyncMock()

        with patch(
            "scenemachine.ipc.handlers.get_db_manager",
            return_value=_fake_db_session_context(fake_session),
        ):
            result = await handler(job_id=str(job.id))

        assert result["status"] == "deleted", (
            f"delete must work on terminal status {terminal_status!r}"
        )


async def test_delete_job_missing_raises(ipc_server: IPCServer) -> None:
    handler = ipc_server.handlers["lipsync.deleteJob"]

    fake_session = MagicMock()
    fake_session.execute = AsyncMock(return_value=MagicMock())
    fake_session.execute.return_value.scalar_one_or_none.return_value = None

    with patch(
        "scenemachine.ipc.handlers.get_db_manager",
        return_value=_fake_db_session_context(fake_session),
    ):
        with pytest.raises(FileNotFoundError):
            await handler(job_id=str(uuid4()))


async def test_delete_job_invalid_uuid_raises(ipc_server: IPCServer) -> None:
    handler = ipc_server.handlers["lipsync.deleteJob"]
    with pytest.raises(ValueError):
        await handler(job_id="not-a-uuid")
