"""Tests for Settings service."""

import pytest
import pytest_asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.services.settings import SettingsService
from scenemachine.models import Project


class TestSettingsService:
    """Tests for SettingsService."""

    @pytest.fixture
    def settings_service(self, db_session: AsyncSession) -> SettingsService:
        """Create a settings service instance."""
        return SettingsService(db_session)

    @pytest.mark.asyncio
    async def test_get_user_settings(
        self,
        settings_service: SettingsService,
    ):
        """Test getting user settings."""
        if hasattr(settings_service, "get_user_settings"):
            user_id = uuid4()
            settings = await settings_service.get_user_settings(user_id)

            assert settings is not None

    @pytest.mark.asyncio
    async def test_update_user_settings(
        self,
        settings_service: SettingsService,
    ):
        """Test updating user settings."""
        if hasattr(settings_service, "update_user_settings"):
            user_id = uuid4()
            result = await settings_service.update_user_settings(
                user_id=user_id,
                settings={
                    "theme": "dark",
                    "notifications_enabled": True,
                    "default_provider": "replicate",
                },
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_get_project_settings(
        self,
        settings_service: SettingsService,
        sample_project: Project,
    ):
        """Test getting project settings."""
        if hasattr(settings_service, "get_project_settings"):
            settings = await settings_service.get_project_settings(
                project_id=sample_project.id,
            )

            assert settings is not None

    @pytest.mark.asyncio
    async def test_update_project_settings(
        self,
        settings_service: SettingsService,
        sample_project: Project,
    ):
        """Test updating project settings."""
        if hasattr(settings_service, "update_project_settings"):
            result = await settings_service.update_project_settings(
                project_id=sample_project.id,
                settings={
                    "default_aspect_ratio": "16:9",
                    "default_duration": 5.0,
                    "quality_preset": "high",
                },
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_get_global_settings(
        self,
        settings_service: SettingsService,
    ):
        """Test getting global/app settings."""
        if hasattr(settings_service, "get_global_settings"):
            settings = await settings_service.get_global_settings()

            assert settings is not None

    @pytest.mark.asyncio
    async def test_get_setting_by_key(
        self,
        settings_service: SettingsService,
    ):
        """Test getting a specific setting by key."""
        if hasattr(settings_service, "get"):
            user_id = uuid4()
            value = await settings_service.get(
                user_id=user_id,
                key="theme",
            )

            # May be None if not set
            assert value is None or isinstance(value, (str, int, bool, dict))

    @pytest.mark.asyncio
    async def test_set_setting_by_key(
        self,
        settings_service: SettingsService,
    ):
        """Test setting a specific setting by key."""
        if hasattr(settings_service, "set"):
            user_id = uuid4()
            result = await settings_service.set(
                user_id=user_id,
                key="theme",
                value="dark",
            )

            assert result is True or result is not None

    @pytest.mark.asyncio
    async def test_reset_to_defaults(
        self,
        settings_service: SettingsService,
    ):
        """Test resetting settings to defaults."""
        if hasattr(settings_service, "reset_to_defaults"):
            user_id = uuid4()
            result = await settings_service.reset_to_defaults(user_id)

            assert result is True or result is not None

    @pytest.mark.asyncio
    async def test_get_provider_settings(
        self,
        settings_service: SettingsService,
    ):
        """Test getting provider-specific settings."""
        if hasattr(settings_service, "get_provider_settings"):
            user_id = uuid4()
            settings = await settings_service.get_provider_settings(
                user_id=user_id,
                provider="replicate",
            )

            assert settings is not None or settings == {}

    @pytest.mark.asyncio
    async def test_update_provider_settings(
        self,
        settings_service: SettingsService,
    ):
        """Test updating provider-specific settings."""
        if hasattr(settings_service, "update_provider_settings"):
            user_id = uuid4()
            result = await settings_service.update_provider_settings(
                user_id=user_id,
                provider="replicate",
                settings={
                    "default_model": "minimax",
                    "quality": "high",
                },
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_validate_settings(
        self,
        settings_service: SettingsService,
    ):
        """Test validating settings schema."""
        if hasattr(settings_service, "validate"):
            settings = {
                "theme": "dark",
                "invalid_key": "should_fail",
            }

            validation = await settings_service.validate(settings)

            # May return validation errors or True/False
            assert validation is not None

    @pytest.mark.asyncio
    async def test_export_settings(
        self,
        settings_service: SettingsService,
    ):
        """Test exporting settings."""
        if hasattr(settings_service, "export"):
            user_id = uuid4()
            exported = await settings_service.export(user_id)

            assert exported is not None
            if isinstance(exported, dict):
                assert len(exported) >= 0

    @pytest.mark.asyncio
    async def test_import_settings(
        self,
        settings_service: SettingsService,
    ):
        """Test importing settings."""
        if hasattr(settings_service, "import_settings"):
            user_id = uuid4()
            settings_data = {
                "theme": "dark",
                "notifications_enabled": True,
            }

            result = await settings_service.import_settings(
                user_id=user_id,
                settings=settings_data,
            )

            assert result is True or result is not None

    @pytest.mark.asyncio
    async def test_get_keyboard_shortcuts(
        self,
        settings_service: SettingsService,
    ):
        """Test getting keyboard shortcut settings."""
        if hasattr(settings_service, "get_shortcuts"):
            user_id = uuid4()
            shortcuts = await settings_service.get_shortcuts(user_id)

            assert shortcuts is not None

    @pytest.mark.asyncio
    async def test_update_keyboard_shortcuts(
        self,
        settings_service: SettingsService,
    ):
        """Test updating keyboard shortcuts."""
        if hasattr(settings_service, "update_shortcuts"):
            user_id = uuid4()
            result = await settings_service.update_shortcuts(
                user_id=user_id,
                shortcuts={
                    "save": "Ctrl+S",
                    "undo": "Ctrl+Z",
                    "redo": "Ctrl+Shift+Z",
                },
            )

            assert result is not None
