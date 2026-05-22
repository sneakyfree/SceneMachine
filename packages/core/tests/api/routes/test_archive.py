"""Tests for archive API routes."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.routes import archive
from scenemachine.models import Project, ProjectState
from scenemachine.services.project_archive import ArchiveManifest, ExportResult, ImportResult


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(archive.router, prefix="/api/v1/archive")
    return app


@pytest.fixture
async def project(db_session: AsyncSession) -> Project:
    """Create a test project."""
    project = Project(
        name="Archive Test Project",
        description="A test project for archive tests",
        state=ProjectState.COMPLETE,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


class TestExportEndpoint:
    """Tests for export endpoint."""

    @pytest.mark.asyncio
    async def test_export_project_success(
        self, app: FastAPI, db_session: AsyncSession, project: Project
    ) -> None:
        """Test exporting a project successfully."""
        mock_manifest = ArchiveManifest(
            version="1.0.0",
            created_at="2024-01-01T00:00:00",
            project_id=str(project.id),
            project_name=project.name,
            includes_assets=True,
            includes_outputs=True,
            file_count=10,
            total_size_bytes=1024000,
        )
        mock_result = ExportResult(
            success=True,
            archive_path="/tmp/test.smproject",
            file_size_bytes=1024000,
            manifest=mock_manifest,
        )

        with patch("scenemachine.api.routes.archive.ProjectArchiveService") as MockService:
            mock_service = AsyncMock()
            mock_service.export_project.return_value = mock_result
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.post(
                    "/api/v1/archive/export",
                    json={
                        "project_id": str(project.id),
                        "include_assets": True,
                        "include_outputs": True,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["archivePath"] is not None

    @pytest.mark.asyncio
    async def test_export_project_failure(
        self, app: FastAPI, db_session: AsyncSession, project: Project
    ) -> None:
        """Test exporting a project that fails."""
        mock_result = ExportResult(
            success=False,
            error="Project has no exportable data",
        )

        with patch("scenemachine.api.routes.archive.ProjectArchiveService") as MockService:
            mock_service = AsyncMock()
            mock_service.export_project.return_value = mock_result
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.post(
                    "/api/v1/archive/export",
                    json={"project_id": str(project.id)},
                )

                assert response.status_code == 400


class TestImportEndpoint:
    """Tests for import endpoint."""

    @pytest.mark.asyncio
    async def test_import_invalid_file_type(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test importing with invalid file type."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            from scenemachine.api.dependencies import get_db

            app.dependency_overrides[get_db] = lambda: db_session

            response = await client.post(
                "/api/v1/archive/import",
                files={"file": ("test.zip", b"test content", "application/zip")},
            )

            assert response.status_code == 400
            assert "Invalid file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_import_project_success(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test importing a project successfully."""
        mock_result = ImportResult(
            success=True,
            project_id=str(uuid4()),
            project_name="Imported Project",
            scenes_imported=5,
            shots_imported=25,
            characters_imported=3,
            assets_imported=10,
        )

        with (
            patch("scenemachine.api.routes.archive.ProjectArchiveService") as MockService,
            patch("scenemachine.api.routes.archive.get_settings") as mock_settings,
        ):
            mock_service = AsyncMock()
            mock_service.import_project.return_value = mock_result
            MockService.return_value = mock_service

            mock_settings_obj = MagicMock()
            mock_settings_obj.data_dir = Path(tempfile.gettempdir())
            mock_settings.return_value = mock_settings_obj

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.post(
                    "/api/v1/archive/import",
                    files={
                        "file": (
                            "test.smproject",
                            b"test content",
                            "application/zip",
                        )
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["projectName"] == "Imported Project"


class TestListExportsEndpoint:
    """Tests for list exports endpoint."""

    @pytest.mark.asyncio
    async def test_list_exports(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test listing exported archives."""
        mock_archives = [
            {
                "path": "/exports/project1.smproject",
                "filename": "project1.smproject",
                "size_bytes": 1024000,
                "created_at": "2024-01-01T00:00:00",
                "manifest": {
                    "version": "1.0.0",
                    "project_id": str(uuid4()),
                    "project_name": "Project 1",
                },
            },
            {
                "path": "/exports/project2.smproject",
                "filename": "project2.smproject",
                "size_bytes": 2048000,
                "created_at": "2024-01-02T00:00:00",
                "manifest": None,
            },
        ]

        with patch("scenemachine.api.routes.archive.ProjectArchiveService") as MockService:
            mock_service = AsyncMock()
            mock_service.list_exports.return_value = mock_archives
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db

                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.get("/api/v1/archive/list")

                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2


class TestArchiveInfoEndpoint:
    """Tests for archive info endpoint."""

    @pytest.mark.asyncio
    async def test_get_archive_info_not_found(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test getting info for nonexistent archive."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            from scenemachine.api.dependencies import get_db

            app.dependency_overrides[get_db] = lambda: db_session

            response = await client.get("/api/v1/archive/info?path=/nonexistent/path.smproject")

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_archive_info_success(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test getting archive info successfully."""
        mock_manifest = ArchiveManifest(
            version="1.0.0",
            created_at="2024-01-01T00:00:00",
            project_id=str(uuid4()),
            project_name="Test Project",
            includes_assets=True,
            includes_outputs=True,
            file_count=15,
            total_size_bytes=2048000,
        )

        with tempfile.NamedTemporaryFile(suffix=".smproject", delete=False) as f:
            temp_path = f.name
            f.write(b"test content")

        try:
            with patch("scenemachine.api.routes.archive.ProjectArchiveService") as MockService:
                mock_service = AsyncMock()
                mock_service.get_archive_info.return_value = mock_manifest
                MockService.return_value = mock_service

                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    from scenemachine.api.dependencies import get_db

                    app.dependency_overrides[get_db] = lambda: db_session

                    response = await client.get(f"/api/v1/archive/info?path={temp_path}")

                    assert response.status_code == 200
                    data = response.json()
                    assert data["projectName"] == "Test Project"
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestDeleteExportEndpoint:
    """Tests for delete export endpoint."""

    @pytest.mark.asyncio
    async def test_delete_export_not_found(self, app: FastAPI, db_session: AsyncSession) -> None:
        """Test deleting nonexistent export."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            from scenemachine.api.dependencies import get_db

            app.dependency_overrides[get_db] = lambda: db_session

            response = await client.delete(
                "/api/v1/archive/export?path=/nonexistent/path.smproject"
            )

            assert response.status_code == 404
