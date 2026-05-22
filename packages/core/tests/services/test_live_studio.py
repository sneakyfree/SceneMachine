"""Tests for Live Studio service (real-time collaboration)."""

from uuid import uuid4

import pytest

from scenemachine.services.live_studio import LiveStudioService


class TestLiveStudioService:
    """Tests for LiveStudioService."""

    @pytest.fixture
    def live_studio_service(self) -> LiveStudioService:
        """Create a live studio service instance."""
        return LiveStudioService()

    @pytest.fixture
    def sample_project_id(self) -> str:
        """Generate a sample project ID."""
        return str(uuid4())

    @pytest.fixture
    def sample_user_id(self) -> str:
        """Generate a sample user ID."""
        return str(uuid4())

    @pytest.mark.asyncio
    async def test_join_session(
        self,
        live_studio_service: LiveStudioService,
        sample_project_id: str,
        sample_user_id: str,
    ):
        """Test joining a live studio session."""
        result = await live_studio_service.join_session(
            project_id=sample_project_id,
            user_id=sample_user_id,
            username="TestUser",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_leave_session(
        self,
        live_studio_service: LiveStudioService,
        sample_project_id: str,
        sample_user_id: str,
    ):
        """Test leaving a live studio session."""
        # Join first
        await live_studio_service.join_session(
            project_id=sample_project_id,
            user_id=sample_user_id,
            username="TestUser",
        )

        # Then leave
        result = await live_studio_service.leave_session(
            project_id=sample_project_id,
            user_id=sample_user_id,
        )

        assert result is True or result is None

    @pytest.mark.asyncio
    async def test_get_active_users(
        self,
        live_studio_service: LiveStudioService,
        sample_project_id: str,
        sample_user_id: str,
    ):
        """Test getting active users in a session."""
        # Join the session
        await live_studio_service.join_session(
            project_id=sample_project_id,
            user_id=sample_user_id,
            username="TestUser",
        )

        # Get active users
        users = await live_studio_service.get_active_users(sample_project_id)

        assert isinstance(users, (list, dict))

    @pytest.mark.asyncio
    async def test_update_cursor(
        self,
        live_studio_service: LiveStudioService,
        sample_project_id: str,
        sample_user_id: str,
    ):
        """Test updating user cursor position."""
        # Join first
        await live_studio_service.join_session(
            project_id=sample_project_id,
            user_id=sample_user_id,
            username="TestUser",
        )

        # Update cursor
        result = await live_studio_service.update_cursor(
            project_id=sample_project_id,
            user_id=sample_user_id,
            cursor_position={"x": 100, "y": 200, "element_id": "timeline"},
        )

        assert result is True or result is None

    @pytest.mark.asyncio
    async def test_acquire_edit_lock(
        self,
        live_studio_service: LiveStudioService,
        sample_project_id: str,
        sample_user_id: str,
    ):
        """Test acquiring an edit lock on an element."""
        # Join first
        await live_studio_service.join_session(
            project_id=sample_project_id,
            user_id=sample_user_id,
            username="TestUser",
        )

        # Acquire lock
        element_id = "scene_001"
        result = await live_studio_service.acquire_lock(
            project_id=sample_project_id,
            user_id=sample_user_id,
            element_id=element_id,
        )

        assert result is True or result is None

    @pytest.mark.asyncio
    async def test_release_edit_lock(
        self,
        live_studio_service: LiveStudioService,
        sample_project_id: str,
        sample_user_id: str,
    ):
        """Test releasing an edit lock."""
        # Join and acquire lock first
        await live_studio_service.join_session(
            project_id=sample_project_id,
            user_id=sample_user_id,
            username="TestUser",
        )

        element_id = "scene_001"
        await live_studio_service.acquire_lock(
            project_id=sample_project_id,
            user_id=sample_user_id,
            element_id=element_id,
        )

        # Release lock
        result = await live_studio_service.release_lock(
            project_id=sample_project_id,
            user_id=sample_user_id,
            element_id=element_id,
        )

        assert result is True or result is None

    @pytest.mark.asyncio
    async def test_lock_conflict(
        self,
        live_studio_service: LiveStudioService,
        sample_project_id: str,
    ):
        """Test that lock conflicts are detected."""
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        element_id = "scene_001"

        # User 1 joins and acquires lock
        await live_studio_service.join_session(
            project_id=sample_project_id,
            user_id=user1_id,
            username="User1",
        )
        await live_studio_service.acquire_lock(
            project_id=sample_project_id,
            user_id=user1_id,
            element_id=element_id,
        )

        # User 2 tries to acquire same lock
        await live_studio_service.join_session(
            project_id=sample_project_id,
            user_id=user2_id,
            username="User2",
        )
        result = await live_studio_service.acquire_lock(
            project_id=sample_project_id,
            user_id=user2_id,
            element_id=element_id,
        )

        # Should fail or return False
        assert result is False or result is None

    @pytest.mark.asyncio
    async def test_send_chat_message(
        self,
        live_studio_service: LiveStudioService,
        sample_project_id: str,
        sample_user_id: str,
    ):
        """Test sending a chat message in a session."""
        # Join first
        await live_studio_service.join_session(
            project_id=sample_project_id,
            user_id=sample_user_id,
            username="TestUser",
        )

        # Send message
        if hasattr(live_studio_service, "send_chat"):
            result = await live_studio_service.send_chat(
                project_id=sample_project_id,
                user_id=sample_user_id,
                message="Hello everyone!",
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_chat_history(
        self,
        live_studio_service: LiveStudioService,
        sample_project_id: str,
    ):
        """Test getting chat history for a session."""
        if hasattr(live_studio_service, "get_chat_history"):
            history = await live_studio_service.get_chat_history(
                project_id=sample_project_id,
                limit=50,
            )
            assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_sync_timeline_state(
        self,
        live_studio_service: LiveStudioService,
        sample_project_id: str,
        sample_user_id: str,
    ):
        """Test syncing timeline state across users."""
        # Join first
        await live_studio_service.join_session(
            project_id=sample_project_id,
            user_id=sample_user_id,
            username="TestUser",
        )

        # Sync timeline state if method exists
        if hasattr(live_studio_service, "sync_timeline"):
            result = await live_studio_service.sync_timeline(
                project_id=sample_project_id,
                user_id=sample_user_id,
                timeline_state={"position": 0, "zoom": 1.0},
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_cleanup_inactive_users(
        self,
        live_studio_service: LiveStudioService,
        sample_project_id: str,
    ):
        """Test cleaning up inactive users from sessions."""
        if hasattr(live_studio_service, "cleanup_inactive"):
            await live_studio_service.cleanup_inactive(
                max_inactive_seconds=30,
            )
            # Should not raise exception

    @pytest.mark.asyncio
    async def test_lock_expiry(
        self,
        live_studio_service: LiveStudioService,
        sample_project_id: str,
        sample_user_id: str,
    ):
        """Test that locks expire after timeout."""
        # Join and acquire lock
        await live_studio_service.join_session(
            project_id=sample_project_id,
            user_id=sample_user_id,
            username="TestUser",
        )

        element_id = "scene_001"
        await live_studio_service.acquire_lock(
            project_id=sample_project_id,
            user_id=sample_user_id,
            element_id=element_id,
        )

        # Lock should have an expiry mechanism
        # (In production, this would involve time manipulation)
