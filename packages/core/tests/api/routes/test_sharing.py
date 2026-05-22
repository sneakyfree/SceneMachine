"""Tests for sharing API routes."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.routes import sharing
from scenemachine.models import Project, ProjectState
from scenemachine.models.share import SharePermission, ShareStatus
from scenemachine.services.sharing import ShareInfo, ShareResult


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(sharing.router, prefix="/api/v1/sharing")
    return app


@pytest.fixture
async def project(db_session: AsyncSession) -> Project:
    """Create a test project."""
    project = Project(
        name="Sharing Test Project",
        description="A test project for sharing tests",
        state=ProjectState.COMPLETE,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


class TestCreateShareEndpoint:
    """Tests for create share endpoint."""

    @pytest.mark.asyncio
    async def test_create_share_success(
        self, app: FastAPI, db_session: AsyncSession, project: Project
    ) -> None:
        """Test creating a share successfully."""
        mock_result = ShareResult(
            success=True,
            share_id=str(uuid4()),
            share_code="abc123",
            share_url="http://localhost/share/abc123",
        )

        with patch(
            "scenemachine.api.routes.sharing.SharingService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.create_share.return_value = mock_result
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db
                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.post(
                    "/api/v1/sharing",
                    json={
                        "project_id": str(project.id),
                        "permission": "view",
                    },
                )

                assert response.status_code == 201
                data = response.json()
                assert data["success"] is True
                assert data["shareCode"] == "abc123"

    @pytest.mark.asyncio
    async def test_create_share_with_recipient(
        self, app: FastAPI, db_session: AsyncSession, project: Project
    ) -> None:
        """Test creating a share with recipient info."""
        mock_result = ShareResult(
            success=True,
            share_id=str(uuid4()),
            share_code="xyz789",
            share_url="http://localhost/share/xyz789",
        )

        with patch(
            "scenemachine.api.routes.sharing.SharingService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.create_share.return_value = mock_result
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db
                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.post(
                    "/api/v1/sharing",
                    json={
                        "project_id": str(project.id),
                        "permission": "comment",
                        "recipient_email": "test@example.com",
                        "recipient_name": "Test User",
                        "message": "Check this out!",
                        "expires_in_days": 7,
                    },
                )

                assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_share_invalid_permission(
        self, app: FastAPI, db_session: AsyncSession, project: Project
    ) -> None:
        """Test creating a share with invalid permission."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            from scenemachine.api.dependencies import get_db
            app.dependency_overrides[get_db] = lambda: db_session

            response = await client.post(
                "/api/v1/sharing",
                json={
                    "project_id": str(project.id),
                    "permission": "invalid_permission",
                },
            )

            assert response.status_code == 400
            assert "Invalid permission" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_share_project_not_found(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test creating a share for nonexistent project."""
        mock_result = ShareResult(
            success=False,
            error="Project not found",
        )

        with patch(
            "scenemachine.api.routes.sharing.SharingService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.create_share.return_value = mock_result
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db
                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.post(
                    "/api/v1/sharing",
                    json={
                        "project_id": str(uuid4()),
                        "permission": "view",
                    },
                )

                assert response.status_code == 400


class TestGetSharesEndpoint:
    """Tests for get shares endpoints."""

    @pytest.mark.asyncio
    async def test_get_project_shares(
        self, app: FastAPI, db_session: AsyncSession, project: Project
    ) -> None:
        """Test getting shares for a project."""
        mock_shares = [
            ShareInfo(
                id=str(uuid4()),
                project_id=str(project.id),
                project_name=project.name,
                share_code="abc123",
                permission="view",
                status="active",
                is_public=False,
                created_at="2024-01-01T00:00:00",
                access_count=5,
            ),
            ShareInfo(
                id=str(uuid4()),
                project_id=str(project.id),
                project_name=project.name,
                share_code="def456",
                permission="edit",
                status="active",
                is_public=True,
                created_at="2024-01-02T00:00:00",
                access_count=3,
            ),
        ]

        with patch(
            "scenemachine.api.routes.sharing.SharingService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.get_project_shares.return_value = mock_shares
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db
                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.get(
                    f"/api/v1/sharing/project/{project.id}"
                )

                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_share_by_code(
        self, app: FastAPI, db_session: AsyncSession, project: Project
    ) -> None:
        """Test getting a share by code."""
        mock_share = MagicMock()
        mock_share.share_code = "abc123"
        mock_share.project_id = project.id
        mock_share.project = project
        mock_share.permission = SharePermission.VIEW
        mock_share.status = ShareStatus.ACTIVE
        mock_share.is_public = False
        mock_share.expires_at = None
        mock_share.is_valid.return_value = True

        with patch(
            "scenemachine.api.routes.sharing.SharingService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.get_share_by_code.return_value = mock_share
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db
                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.get("/api/v1/sharing/code/abc123")

                assert response.status_code == 200
                data = response.json()
                assert data["shareCode"] == "abc123"

    @pytest.mark.asyncio
    async def test_get_share_by_code_not_found(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test getting a nonexistent share."""
        with patch(
            "scenemachine.api.routes.sharing.SharingService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.get_share_by_code.return_value = None
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db
                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.get("/api/v1/sharing/code/invalid")

                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_share_by_code_expired(
        self, app: FastAPI, db_session: AsyncSession, project: Project
    ) -> None:
        """Test getting an expired share."""
        mock_share = MagicMock()
        mock_share.is_valid.return_value = False

        with patch(
            "scenemachine.api.routes.sharing.SharingService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.get_share_by_code.return_value = mock_share
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db
                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.get("/api/v1/sharing/code/expired")

                assert response.status_code == 410


class TestAcceptShareEndpoint:
    """Tests for accept share endpoint."""

    @pytest.mark.asyncio
    async def test_accept_share_success(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test accepting a share successfully."""
        mock_result = {
            "success": True,
            "projectId": str(uuid4()),
            "projectName": "Test Project",
            "permission": "view",
        }

        with patch(
            "scenemachine.api.routes.sharing.SharingService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.accept_share.return_value = mock_result
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db
                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.post("/api/v1/sharing/code/abc123/accept")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    @pytest.mark.asyncio
    async def test_accept_share_failure(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test accepting an invalid share."""
        mock_result = {"success": False, "error": "Share not found or expired"}

        with patch(
            "scenemachine.api.routes.sharing.SharingService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.accept_share.return_value = mock_result
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db
                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.post(
                    "/api/v1/sharing/code/invalid/accept"
                )

                assert response.status_code == 400


class TestRevokeShareEndpoint:
    """Tests for revoke share endpoint."""

    @pytest.mark.asyncio
    async def test_revoke_share_success(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test revoking a share successfully."""
        share_id = uuid4()

        with patch(
            "scenemachine.api.routes.sharing.SharingService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.revoke_share.return_value = True
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db
                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.delete(f"/api/v1/sharing/{share_id}")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    @pytest.mark.asyncio
    async def test_revoke_share_not_found(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test revoking a nonexistent share."""
        share_id = uuid4()

        with patch(
            "scenemachine.api.routes.sharing.SharingService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.revoke_share.return_value = False
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db
                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.delete(f"/api/v1/sharing/{share_id}")

                assert response.status_code == 404


class TestCommentsEndpoint:
    """Tests for comments endpoints."""

    @pytest.mark.asyncio
    async def test_add_comment(
        self, app: FastAPI, db_session: AsyncSession, project: Project
    ) -> None:
        """Test adding a comment."""
        mock_comment = MagicMock()
        mock_comment.id = uuid4()
        mock_comment.project_id = project.id
        mock_comment.shot_id = None
        mock_comment.author_name = "Test User"
        mock_comment.content = "Great work!"
        mock_comment.created_at = datetime.now(UTC)

        with patch(
            "scenemachine.api.routes.sharing.SharingService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.add_comment.return_value = mock_comment
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db
                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.post(
                    f"/api/v1/sharing/projects/{project.id}/comments",
                    json={
                        "author_name": "Test User",
                        "content": "Great work!",
                    },
                )

                assert response.status_code == 201
                data = response.json()
                assert data["authorName"] == "Test User"
                assert data["content"] == "Great work!"

    @pytest.mark.asyncio
    async def test_get_project_comments(
        self, app: FastAPI, db_session: AsyncSession, project: Project
    ) -> None:
        """Test getting project comments."""
        mock_comments = [
            {
                "id": str(uuid4()),
                "projectId": str(project.id),
                "authorName": "User 1",
                "content": "Comment 1",
                "isResolved": False,
                "createdAt": "2024-01-01T00:00:00",
            },
            {
                "id": str(uuid4()),
                "projectId": str(project.id),
                "authorName": "User 2",
                "content": "Comment 2",
                "isResolved": True,
                "createdAt": "2024-01-02T00:00:00",
            },
        ]

        with patch(
            "scenemachine.api.routes.sharing.SharingService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.get_project_comments.return_value = mock_comments
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db
                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.get(
                    f"/api/v1/sharing/projects/{project.id}/comments"
                )

                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2

    @pytest.mark.asyncio
    async def test_resolve_comment(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test resolving a comment."""
        comment_id = uuid4()

        with patch(
            "scenemachine.api.routes.sharing.SharingService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.resolve_comment.return_value = True
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db
                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.post(
                    f"/api/v1/sharing/comments/{comment_id}/resolve"
                )

                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_comment(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test deleting a comment."""
        comment_id = uuid4()

        with patch(
            "scenemachine.api.routes.sharing.SharingService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.delete_comment.return_value = True
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db
                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.delete(
                    f"/api/v1/sharing/comments/{comment_id}"
                )

                assert response.status_code == 200


class TestCleanupExpiredSharesEndpoint:
    """Tests for cleanup expired shares endpoint."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_shares(
        self, app: FastAPI, db_session: AsyncSession
    ) -> None:
        """Test cleanup of expired shares."""
        with patch(
            "scenemachine.api.routes.sharing.SharingService"
        ) as MockService:
            mock_service = AsyncMock()
            mock_service.cleanup_expired_shares.return_value = 5
            MockService.return_value = mock_service

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                from scenemachine.api.dependencies import get_db
                app.dependency_overrides[get_db] = lambda: db_session

                response = await client.post("/api/v1/sharing/cleanup-expired")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["expiredCount"] == 5
