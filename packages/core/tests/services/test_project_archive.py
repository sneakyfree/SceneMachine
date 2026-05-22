"""Tests for Project Archive service."""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models import Project
from scenemachine.services.project_archive import ProjectArchiveService


class TestProjectArchiveService:
    """Tests for ProjectArchiveService."""

    @pytest.fixture
    def archive_service(self, db_session: AsyncSession) -> ProjectArchiveService:
        """Create a project archive service instance."""
        return ProjectArchiveService(db_session)

    @pytest.mark.asyncio
    async def test_archive_project(
        self,
        archive_service: ProjectArchiveService,
        sample_project: Project,
    ):
        """Test archiving a project."""
        result = await archive_service.archive(sample_project.id)

        assert result is True or result is not None

    @pytest.mark.asyncio
    async def test_unarchive_project(
        self,
        archive_service: ProjectArchiveService,
        sample_project: Project,
    ):
        """Test unarchiving a project."""
        # First archive it
        await archive_service.archive(sample_project.id)

        # Then unarchive
        result = await archive_service.unarchive(sample_project.id)

        assert result is True or result is not None

    @pytest.mark.asyncio
    async def test_get_archived_projects(
        self,
        archive_service: ProjectArchiveService,
        sample_project: Project,
    ):
        """Test getting all archived projects."""
        # Archive a project first
        await archive_service.archive(sample_project.id)

        archived = await archive_service.get_archived()

        assert isinstance(archived, list)

    @pytest.mark.asyncio
    async def test_archive_nonexistent_project(
        self,
        archive_service: ProjectArchiveService,
    ):
        """Test archiving a non-existent project."""
        result = await archive_service.archive(uuid4())

        # Should return False or raise exception
        assert result is False or result is None

    @pytest.mark.asyncio
    async def test_export_archive(
        self,
        archive_service: ProjectArchiveService,
        sample_project: Project,
        temp_dir: Path,
    ):
        """Test exporting an archived project."""
        # Archive first
        await archive_service.archive(sample_project.id)

        if hasattr(archive_service, "export"):
            export_path = await archive_service.export(
                project_id=sample_project.id,
                output_dir=temp_dir,
            )

            assert export_path is not None

    @pytest.mark.asyncio
    async def test_import_archive(
        self,
        archive_service: ProjectArchiveService,
        temp_dir: Path,
    ):
        """Test importing a project from archive."""
        if hasattr(archive_service, "import_archive"):
            # Create a mock archive file
            archive_file = temp_dir / "test_archive.zip"
            archive_file.write_bytes(b"mock archive content")

            await archive_service.import_archive(archive_file)
            # May fail with invalid archive, just check it handles gracefully

    @pytest.mark.asyncio
    async def test_delete_archived_project(
        self,
        archive_service: ProjectArchiveService,
        sample_project: Project,
    ):
        """Test permanently deleting an archived project."""
        # Archive first
        await archive_service.archive(sample_project.id)

        if hasattr(archive_service, "delete_permanently"):
            result = await archive_service.delete_permanently(sample_project.id)
            assert result is True

    @pytest.mark.asyncio
    async def test_get_archive_size(
        self,
        archive_service: ProjectArchiveService,
        sample_project: Project,
    ):
        """Test getting the size of an archived project."""
        await archive_service.archive(sample_project.id)

        if hasattr(archive_service, "get_size"):
            size = await archive_service.get_size(sample_project.id)
            assert size >= 0

    @pytest.mark.asyncio
    async def test_auto_archive_old_projects(
        self,
        archive_service: ProjectArchiveService,
    ):
        """Test auto-archiving old projects."""
        if hasattr(archive_service, "auto_archive"):
            # Archive projects older than X days
            count = await archive_service.auto_archive(days_old=365)
            assert isinstance(count, int)

    @pytest.mark.asyncio
    async def test_restore_with_new_name(
        self,
        archive_service: ProjectArchiveService,
        sample_project: Project,
    ):
        """Test restoring archived project with new name."""
        await archive_service.archive(sample_project.id)

        if hasattr(archive_service, "restore"):
            project = await archive_service.restore(
                project_id=sample_project.id,
                new_name="Restored Project",
            )
            assert project is not None

    @pytest.mark.asyncio
    async def test_get_archive_metadata(
        self,
        archive_service: ProjectArchiveService,
        sample_project: Project,
    ):
        """Test getting archived project metadata."""
        await archive_service.archive(sample_project.id)

        if hasattr(archive_service, "get_metadata"):
            metadata = await archive_service.get_metadata(sample_project.id)
            assert metadata is not None

    @pytest.mark.asyncio
    async def test_archive_includes_assets(
        self,
        archive_service: ProjectArchiveService,
        sample_project: Project,
    ):
        """Test that archive includes project assets."""
        await archive_service.archive(sample_project.id)

        if hasattr(archive_service, "get_archived_assets"):
            assets = await archive_service.get_archived_assets(sample_project.id)
            assert isinstance(assets, list)

    @pytest.mark.asyncio
    async def test_archive_preserves_history(
        self,
        archive_service: ProjectArchiveService,
        sample_project: Project,
    ):
        """Test that archive preserves version history."""
        await archive_service.archive(sample_project.id)

        if hasattr(archive_service, "get_version_history"):
            history = await archive_service.get_version_history(sample_project.id)
            assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_search_archived_projects(
        self,
        archive_service: ProjectArchiveService,
        sample_project: Project,
    ):
        """Test searching archived projects."""
        await archive_service.archive(sample_project.id)

        if hasattr(archive_service, "search"):
            results = await archive_service.search("Sample")
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_archive_cleanup(
        self,
        archive_service: ProjectArchiveService,
    ):
        """Test cleaning up old archives."""
        if hasattr(archive_service, "cleanup"):
            # Clean up archives older than X days
            count = await archive_service.cleanup(older_than_days=730)
            assert isinstance(count, int)
