"""Tests for settings API routes."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.routes import settings
from scenemachine.services.settings import ProviderStatus, StorageStats


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(settings.router, prefix="/api/v1/settings")
    return app


class TestGetSettingsEndpoint:
    """Tests for get settings endpoint."""

    @pytest.mark.asyncio
    async def test_get_settings(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test getting current settings."""
        mock_settings = MagicMock()
        mock_settings.to_dict.return_value = {
            "llmProvider": "anthropic",
            "videoProvider": "replicate",
            "maxConcurrentGenerations": 3,
            "themeMode": "dark",
        }

        with patch("scenemachine.api.routes.settings.SettingsService") as MockService:
            mock_service = AsyncMock()
            mock_service.get_settings.return_value = mock_settings
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.get("/api/v1/settings")

                assert response.status_code == 200
                data = response.json()
                assert data["llmProvider"] == "anthropic"
                assert data["themeMode"] == "dark"


class TestUpdateSettingsEndpoint:
    """Tests for update settings endpoint."""

    @pytest.mark.asyncio
    async def test_update_settings(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test updating settings."""
        mock_settings = MagicMock()
        mock_settings.to_dict.return_value = {
            "llmProvider": "openai",
            "videoProvider": "fal",
            "maxConcurrentGenerations": 5,
            "themeMode": "light",
        }

        with patch("scenemachine.api.routes.settings.SettingsService") as MockService:
            mock_service = AsyncMock()
            mock_service.update_settings.return_value = mock_settings
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.patch(
                    "/api/v1/settings",
                    json={
                        "llm_provider": "openai",
                        "video_provider": "fal",
                        "max_concurrent_generations": 5,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["llmProvider"] == "openai"

    @pytest.mark.asyncio
    async def test_update_settings_invalid_value(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test updating settings with invalid value."""
        with patch("scenemachine.api.routes.settings.SettingsService") as MockService:
            mock_service = AsyncMock()
            mock_service.update_settings.side_effect = ValueError("Invalid provider: invalid")
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.patch(
                    "/api/v1/settings",
                    json={"llm_provider": "invalid"},
                )

                assert response.status_code == 400


class TestApiKeysEndpoint:
    """Tests for API keys endpoints."""

    @pytest.mark.asyncio
    async def test_set_api_key(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test setting an API key."""
        with patch("scenemachine.api.routes.settings.SettingsService") as MockService:
            mock_service = AsyncMock()
            mock_service.set_api_key.return_value = None
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.post(
                    "/api/v1/settings/api-keys",
                    json={
                        "provider": "anthropic",
                        "api_key": "sk-test-key",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_remove_api_key(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test removing an API key."""
        with patch("scenemachine.api.routes.settings.SettingsService") as MockService:
            mock_service = AsyncMock()
            mock_service.remove_api_key.return_value = None
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.delete("/api/v1/settings/api-keys/anthropic")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    @pytest.mark.asyncio
    async def test_validate_api_key(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test validating an API key."""
        mock_status = ProviderStatus(
            provider="anthropic",
            name="Anthropic",
            available=True,
            configured=True,
            message="API key is valid",
            latency_ms=150,
        )

        with patch("scenemachine.api.routes.settings.SettingsService") as MockService:
            mock_service = AsyncMock()
            mock_service.validate_api_key.return_value = mock_status
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.post("/api/v1/settings/api-keys/anthropic/validate")

                assert response.status_code == 200
                data = response.json()
                assert data["available"] is True
                assert data["configured"] is True


class TestProvidersEndpoint:
    """Tests for providers endpoints."""

    @pytest.mark.asyncio
    async def test_check_all_providers(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test checking status of all providers."""
        mock_statuses = [
            ProviderStatus(
                provider="anthropic",
                name="Anthropic",
                available=True,
                configured=True,
                message="Ready",
                latency_ms=100,
            ),
            ProviderStatus(
                provider="openai",
                name="OpenAI",
                available=False,
                configured=False,
                message="Not configured",
            ),
        ]

        with patch("scenemachine.api.routes.settings.SettingsService") as MockService:
            mock_service = AsyncMock()
            mock_service.check_all_providers.return_value = mock_statuses
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.get("/api/v1/settings/providers/status")

                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
                assert data[0]["provider"] == "anthropic"
                assert data[0]["available"] is True

    @pytest.mark.asyncio
    async def test_get_llm_providers(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test getting LLM providers."""
        mock_providers = [
            {
                "id": "anthropic",
                "name": "Anthropic",
                "models": ["claude-3-sonnet", "claude-3-opus"],
                "configured": True,
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "models": ["gpt-4", "gpt-4-turbo"],
                "configured": False,
            },
        ]

        with patch("scenemachine.api.routes.settings.SettingsService") as MockService:
            mock_service = AsyncMock()
            mock_service.get_available_llm_providers.return_value = mock_providers
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.get("/api/v1/settings/providers/llm")

                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_video_providers(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test getting video providers."""
        mock_providers = [
            {
                "id": "replicate",
                "name": "Replicate",
                "models": ["stable-video-diffusion"],
                "configured": True,
            },
        ]

        with patch("scenemachine.api.routes.settings.SettingsService") as MockService:
            mock_service = AsyncMock()
            mock_service.get_available_video_providers.return_value = mock_providers
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.get("/api/v1/settings/providers/video")

                assert response.status_code == 200


class TestStorageEndpoint:
    """Tests for storage endpoints."""

    @pytest.mark.asyncio
    async def test_get_storage_stats(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test getting storage statistics."""
        mock_stats = StorageStats(
            data_dir="/data",
            upload_dir="/data/uploads",
            output_dir="/data/outputs",
            cache_dir="/data/cache",
            total_size_bytes=10737418240,  # 10 GB
            upload_size_bytes=1073741824,  # 1 GB
            output_size_bytes=5368709120,  # 5 GB
            cache_size_bytes=4294967296,  # 4 GB
            temp_files_count=15,
        )

        with patch("scenemachine.api.routes.settings.SettingsService") as MockService:
            mock_service = AsyncMock()
            mock_service.get_storage_stats.return_value = mock_stats
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.get("/api/v1/settings/storage")

                assert response.status_code == 200
                data = response.json()
                assert data["totalSizeBytes"] == 10737418240
                assert data["tempFilesCount"] == 15

    @pytest.mark.asyncio
    async def test_clear_cache(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test clearing cache."""
        mock_result = {
            "model_cache": True,
            "temp_files": True,
            "bytes_freed": 1073741824,
        }

        with patch("scenemachine.api.routes.settings.SettingsService") as MockService:
            mock_service = AsyncMock()
            mock_service.clear_cache.return_value = mock_result
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.post("/api/v1/settings/storage/clear-cache?cache_type=all")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["bytesFreed"] == 1073741824


class TestExportImportSettingsEndpoint:
    """Tests for export/import settings endpoints."""

    @pytest.mark.asyncio
    async def test_export_settings(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test exporting settings."""
        mock_export = {
            "version": "1.0.0",
            "settings": {
                "llmProvider": "anthropic",
                "videoProvider": "replicate",
            },
        }

        with patch("scenemachine.api.routes.settings.SettingsService") as MockService:
            mock_service = AsyncMock()
            mock_service.export_settings.return_value = mock_export
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.get("/api/v1/settings/export")

                assert response.status_code == 200
                data = response.json()
                assert "settings" in data

    @pytest.mark.asyncio
    async def test_import_settings(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test importing settings."""
        mock_settings = MagicMock()
        mock_settings.to_dict.return_value = {
            "llmProvider": "anthropic",
            "videoProvider": "replicate",
        }

        with patch("scenemachine.api.routes.settings.SettingsService") as MockService:
            mock_service = AsyncMock()
            mock_service.import_settings.return_value = mock_settings
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.post(
                    "/api/v1/settings/import",
                    json={
                        "settings": {
                            "llmProvider": "anthropic",
                            "videoProvider": "replicate",
                        }
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    @pytest.mark.asyncio
    async def test_import_settings_invalid(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test importing invalid settings."""
        with patch("scenemachine.api.routes.settings.SettingsService") as MockService:
            mock_service = AsyncMock()
            mock_service.import_settings.side_effect = ValueError("Invalid settings format")
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.post(
                    "/api/v1/settings/import",
                    json={"settings": {"invalid": "data"}},
                )

                assert response.status_code == 400
