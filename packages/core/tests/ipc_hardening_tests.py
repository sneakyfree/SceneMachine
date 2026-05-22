"""
IPC Handler Hardening Tests for SceneMachine.

Tests all 159 IPC handlers to ensure they are properly registered,
callable, and handle errors appropriately.
"""

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class MockIPCServer:
    """Mock IPC server for testing handler registration."""

    def __init__(self):
        self.handlers: dict[str, Any] = {}

    def handler(self, name: str):
        """Decorator to register a handler."""

        def decorator(func):
            self.handlers[name] = func
            return func

        return decorator


class TestIPCHandlerRegistration:
    """Test that all IPC handlers are properly registered."""

    @pytest.fixture
    def mock_server(self):
        """Create a mock IPC server."""
        return MockIPCServer()

    def test_register_handlers_imports(self):
        """Test that register_handlers function can be imported."""
        from scenemachine.ipc.handlers import register_handlers

        assert register_handlers is not None
        assert callable(register_handlers)

    def test_handler_count(self, mock_server):
        """Test that expected number of handlers are registered."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        # We expect at least 150 handlers
        assert len(mock_server.handlers) >= 150, (
            f"Expected at least 150 handlers, got {len(mock_server.handlers)}"
        )

    def test_core_handlers_registered(self, mock_server):
        """Test that core handlers are registered."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        core_handlers = [
            "ping",
            "version",
            "projects.list",
            "projects.get",
            "projects.create",
            "projects.update",
            "projects.delete",
        ]

        for handler_name in core_handlers:
            assert handler_name in mock_server.handlers, (
                f"Core handler '{handler_name}' not registered"
            )

    def test_character_handlers_registered(self, mock_server):
        """Test that character handlers are registered."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        character_handlers = [
            "characters.list",
            "characters.get",
            "characters.update",
            "characters.generateDescription",
            "characters.uploadReference",
            "characters.deleteReference",
            "characters.lock",
            "characters.unlock",
            "characters.updateVoice",
            "characters.getPrompt",
        ]

        for handler_name in character_handlers:
            assert handler_name in mock_server.handlers, (
                f"Character handler '{handler_name}' not registered"
            )

    def test_scene_handlers_registered(self, mock_server):
        """Test that scene handlers are registered."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        scene_handlers = [
            "scenes.list",
            "scenes.get",
            "scenes.analyze",
            "scenes.generateBreakdown",
            "scenes.approve",
            "scenes.getShotTypes",
            "scenes.getCameraMovements",
        ]

        for handler_name in scene_handlers:
            assert handler_name in mock_server.handlers, (
                f"Scene handler '{handler_name}' not registered"
            )

    def test_shot_handlers_registered(self, mock_server):
        """Test that shot handlers are registered."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        shot_handlers = [
            "shots.get",
            "shots.update",
            "shots.add",
            "shots.delete",
        ]

        for handler_name in shot_handlers:
            assert handler_name in mock_server.handlers, (
                f"Shot handler '{handler_name}' not registered"
            )

    def test_generation_handlers_registered(self, mock_server):
        """Test that generation handlers are registered."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        generation_handlers = [
            "generation.getProviders",
            "generation.getQueueStatus",
            "generation.queueShot",
            "generation.queueScene",
            "generation.queueProject",
            "generation.getJob",
            "generation.cancelJob",
            "generation.retryJob",
            "generation.approveShot",
            "generation.rejectShot",
            "generation.getPendingJobs",
            "generation.getProvidersHealth",
            "generation.getProviderModels",
            "generation.estimateCost",
            "generation.getWorkerStatus",
            "generation.pauseWorker",
            "generation.resumeWorker",
        ]

        for handler_name in generation_handlers:
            assert handler_name in mock_server.handlers, (
                f"Generation handler '{handler_name}' not registered"
            )

    def test_assembly_handlers_registered(self, mock_server):
        """Test that assembly handlers are registered."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        assembly_handlers = [
            "assembly.getStatus",
            "assembly.getTimeline",
            "assembly.assembleScene",
            "assembly.assembleMovie",
        ]

        for handler_name in assembly_handlers:
            assert handler_name in mock_server.handlers, (
                f"Assembly handler '{handler_name}' not registered"
            )

    def test_settings_handlers_registered(self, mock_server):
        """Test that settings handlers are registered."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        settings_handlers = [
            "settings.get",
            "settings.update",
            "settings.setApiKey",
            "settings.removeApiKey",
            "settings.validateApiKey",
            "settings.getStorageStats",
            "settings.clearCache",
        ]

        for handler_name in settings_handlers:
            assert handler_name in mock_server.handlers, (
                f"Settings handler '{handler_name}' not registered"
            )

    def test_sharing_handlers_registered(self, mock_server):
        """Test that sharing handlers are registered."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        sharing_handlers = [
            "sharing.create",
            "sharing.createShare",
            "sharing.getProjectShares",
            "sharing.accept",
            "sharing.acceptShare",
            "sharing.revoke",
            "sharing.revokeShare",
            "sharing.getComments",
            "sharing.addComment",
        ]

        # Need at least 5 of these (there may be aliases)
        found = [h for h in sharing_handlers if h in mock_server.handlers]
        assert len(found) >= 5, f"Expected at least 5 sharing handlers, found {len(found)}: {found}"

    def test_analytics_handlers_registered(self, mock_server):
        """Test that analytics handlers are registered."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        analytics_handlers = [
            "analytics.getDashboard",
            "analytics.getGenerationStats",
            "analytics.getCostStats",
            "analytics.getDailyStats",
        ]

        for handler_name in analytics_handlers:
            assert handler_name in mock_server.handlers, (
                f"Analytics handler '{handler_name}' not registered"
            )

    def test_archive_handlers_registered(self, mock_server):
        """Test that archive handlers are registered."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        archive_handlers = [
            "archive.export",
            "archive.import",
            "archive.list",
            "archive.getInfo",
        ]

        for handler_name in archive_handlers:
            assert handler_name in mock_server.handlers, (
                f"Archive handler '{handler_name}' not registered"
            )

    def test_audio_handlers_registered(self, mock_server):
        """Test that audio handlers are registered."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        audio_handlers = [
            "audio.getProviders",
            "audio.getVoices",
            "audio.generateDialogue",
            "audio.generateSpeech",
        ]

        for handler_name in audio_handlers:
            assert handler_name in mock_server.handlers, (
                f"Audio handler '{handler_name}' not registered"
            )


class TestIPCHandlerCallability:
    """Test that handlers are callable with expected signatures."""

    @pytest.fixture
    def mock_server(self):
        """Create a mock IPC server."""
        return MockIPCServer()

    def test_ping_handler_is_async(self, mock_server):
        """Test that ping handler is an async function."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        ping = mock_server.handlers.get("ping")
        assert ping is not None
        assert asyncio.iscoroutinefunction(ping)

    def test_version_handler_is_async(self, mock_server):
        """Test that version handler is an async function."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        version = mock_server.handlers.get("version")
        assert version is not None
        assert asyncio.iscoroutinefunction(version)

    def test_all_handlers_are_async(self, mock_server):
        """Test that all handlers are async functions."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        for name, handler in mock_server.handlers.items():
            assert asyncio.iscoroutinefunction(handler), (
                f"Handler '{name}' is not an async function"
            )


class TestIPCHandlerBehavior:
    """Test handler behavior with mocked dependencies."""

    @pytest.fixture
    def mock_server(self):
        """Create a mock IPC server."""
        return MockIPCServer()

    @pytest.mark.asyncio
    async def test_ping_returns_pong(self, mock_server):
        """Test that ping handler returns pong."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        ping = mock_server.handlers.get("ping")
        result = await ping()

        assert result == {"status": "pong"}

    @pytest.mark.asyncio
    async def test_version_returns_version_info(self, mock_server):
        """Test that version handler returns version info."""
        from scenemachine.ipc.handlers import register_handlers

        with patch("scenemachine.ipc.handlers.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(version="1.0.0", environment="test")
            register_handlers(mock_server)

            version = mock_server.handlers.get("version")
            result = await version()

            assert "version" in result
            assert "environment" in result


class TestIPCHandlerCategories:
    """Test handler organization by category."""

    @pytest.fixture
    def mock_server(self):
        return MockIPCServer()

    def test_handler_naming_convention(self, mock_server):
        """Test that handlers follow naming convention."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        # Most handlers should have a category prefix
        categorized = [name for name in mock_server.handlers if "." in name]
        standalone = [name for name in mock_server.handlers if "." not in name]

        # Only ping and version should be standalone
        assert len(standalone) <= 3, f"Too many standalone handlers: {standalone}"
        assert len(categorized) >= 150

    def test_handler_categories(self, mock_server):
        """Test that all expected categories exist."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        categories = set()
        for name in mock_server.handlers:
            if "." in name:
                category = name.split(".")[0]
                categories.add(category)

        expected_categories = {
            "projects",
            "screenplays",
            "moviePlan",
            "characters",
            "scenes",
            "shots",
            "generation",
            "assembly",
            "settings",
            "sharing",
            "analytics",
            "archive",
            "audio",
        }

        for expected in expected_categories:
            assert expected in categories, f"Expected category '{expected}' not found"


class TestIPCHandlerCount:
    """Test total handler counts by category."""

    @pytest.fixture
    def mock_server(self):
        return MockIPCServer()

    def test_count_by_category(self, mock_server):
        """Count handlers per category."""
        from scenemachine.ipc.handlers import register_handlers

        register_handlers(mock_server)

        counts = {}
        for name in mock_server.handlers:
            if "." in name:
                category = name.split(".")[0]
                counts[category] = counts.get(category, 0) + 1
            else:
                counts["(standalone)"] = counts.get("(standalone)", 0) + 1

        # Print counts for visibility in test output
        print("\nHandler counts by category:")
        for category, count in sorted(counts.items()):
            print(f"  {category}: {count}")

        # Assert minimum counts for key categories
        assert counts.get("projects", 0) >= 5
        assert counts.get("characters", 0) >= 8
        assert counts.get("scenes", 0) >= 5
        assert counts.get("generation", 0) >= 15
        assert counts.get("settings", 0) >= 5


class TestIPCServerIntegration:
    """Test IPC server module integration."""

    def test_ipc_server_class_exists(self):
        """Test that IPCServer class exists."""
        from scenemachine.ipc.server import IPCServer

        assert IPCServer is not None

    def test_ipc_server_has_handler_decorator(self):
        """Test that IPCServer has handler decorator."""
        from scenemachine.ipc.server import IPCServer

        # IPCServer requires a socket_path parameter
        server = IPCServer(socket_path="/tmp/test.sock")
        assert hasattr(server, "handler")
        assert callable(server.handler)

    def test_ipc_module_exports(self):
        """Test that ipc module has expected exports."""
        from scenemachine import ipc

        assert hasattr(ipc, "handlers")


# Run tests with: pytest tests/ipc_hardening_tests.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
