"""Tests for the sharing.deleteComment IPC handler.

Closes the regression window on P0-6 — the renderer fired
`sharing.deleteComment` and got back an "unknown method" error because
only `sharing.resolveComment` was registered. Delete-comment buttons in
the desktop sharing panel were dead.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from scenemachine.ipc.handlers import register_handlers
from scenemachine.ipc.server import IPCServer


@pytest.fixture
def ipc_server() -> IPCServer:
    server = IPCServer("/tmp/test_sharing_delete.sock")
    register_handlers(server)
    return server


def test_handler_is_registered(ipc_server: IPCServer) -> None:
    """P0-6 regression guard: the channel must exist."""
    assert "sharing.deleteComment" in ipc_server.handlers, (
        "sharing.deleteComment handler must be registered — see P0-6"
    )


async def test_proxies_service_with_parsed_uuid(ipc_server: IPCServer) -> None:
    """Handler must parse the string UUID and call SharingService.delete_comment."""
    handler = ipc_server.handlers["sharing.deleteComment"]
    comment_id = uuid4()

    mock_service = MagicMock()
    mock_service.delete_comment = AsyncMock(return_value=True)

    fake_session = MagicMock()

    @asynccontextmanager
    async def fake_session_cm():
        yield fake_session

    fake_db = MagicMock()
    fake_db.session = fake_session_cm

    with (
        patch(
            "scenemachine.ipc.handlers.get_db_manager",
            return_value=fake_db,
        ),
        patch(
            "scenemachine.services.sharing.SharingService",
            return_value=mock_service,
        ),
    ):
        result = await handler(comment_id=str(comment_id))

    assert result == {"success": True}
    mock_service.delete_comment.assert_awaited_once()
    called_with = mock_service.delete_comment.await_args.args[0]
    assert isinstance(called_with, UUID)
    assert called_with == comment_id


async def test_returns_false_on_missing_comment(ipc_server: IPCServer) -> None:
    """If the comment doesn't exist, the service returns False — surface that."""
    handler = ipc_server.handlers["sharing.deleteComment"]

    mock_service = MagicMock()
    mock_service.delete_comment = AsyncMock(return_value=False)

    fake_session = MagicMock()

    @asynccontextmanager
    async def fake_session_cm():
        yield fake_session

    fake_db = MagicMock()
    fake_db.session = fake_session_cm

    with (
        patch(
            "scenemachine.ipc.handlers.get_db_manager",
            return_value=fake_db,
        ),
        patch(
            "scenemachine.services.sharing.SharingService",
            return_value=mock_service,
        ),
    ):
        result = await handler(comment_id=str(uuid4()))

    assert result == {"success": False}


async def test_rejects_invalid_uuid(ipc_server: IPCServer) -> None:
    """A non-UUID string must raise ValueError, not silently no-op."""
    handler = ipc_server.handlers["sharing.deleteComment"]
    with pytest.raises(ValueError):
        await handler(comment_id="not-a-uuid")
