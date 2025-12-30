"""Tests for the sharing service."""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models import Project, ProjectState
from scenemachine.models.share import ProjectShare, SharePermission, ShareStatus
from scenemachine.services.sharing import SharingService


@pytest.fixture
async def project(db_session: AsyncSession) -> Project:
    """Create a test project."""
    project = Project(
        name="Test Project",
        description="A test project for sharing tests",
        state=ProjectState.SCREENPLAY_PARSED,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
def sharing_service(db_session: AsyncSession) -> SharingService:
    """Create a sharing service instance."""
    return SharingService(db_session)


class TestCreateShare:
    """Tests for creating shares."""

    @pytest.mark.asyncio
    async def test_create_share_success(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test creating a basic share."""
        result = await sharing_service.create_share(
            project_id=project.id,
            permission=SharePermission.VIEW,
        )

        assert result.success is True
        assert result.share_id is not None
        assert result.share_code is not None
        assert result.share_url is not None
        assert result.error is None

    @pytest.mark.asyncio
    async def test_create_share_with_recipient(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test creating a share with recipient info."""
        result = await sharing_service.create_share(
            project_id=project.id,
            permission=SharePermission.COMMENT,
            recipient_email="test@example.com",
            recipient_name="Test User",
            message="Check out this project!",
        )

        assert result.success is True
        assert result.share_code is not None

    @pytest.mark.asyncio
    async def test_create_share_with_expiration(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test creating a share with expiration."""
        result = await sharing_service.create_share(
            project_id=project.id,
            permission=SharePermission.VIEW,
            expires_in_days=7,
        )

        assert result.success is True

        # Verify the share has an expiration date
        share = await sharing_service.get_share_by_code(result.share_code)
        assert share is not None
        assert share.expires_at is not None
        assert share.expires_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_create_share_public(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test creating a public share."""
        result = await sharing_service.create_share(
            project_id=project.id,
            permission=SharePermission.VIEW,
            is_public=True,
        )

        assert result.success is True

        share = await sharing_service.get_share_by_code(result.share_code)
        assert share is not None
        assert share.is_public is True

    @pytest.mark.asyncio
    async def test_create_share_nonexistent_project(
        self, sharing_service: SharingService
    ) -> None:
        """Test creating a share for nonexistent project fails."""
        result = await sharing_service.create_share(
            project_id=uuid4(),
            permission=SharePermission.VIEW,
        )

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()


class TestGetShare:
    """Tests for retrieving shares."""

    @pytest.mark.asyncio
    async def test_get_share_by_code(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test getting a share by code."""
        # Create share
        result = await sharing_service.create_share(
            project_id=project.id,
            permission=SharePermission.VIEW,
        )

        # Get share
        share = await sharing_service.get_share_by_code(result.share_code)

        assert share is not None
        assert share.share_code == result.share_code
        assert share.permission == SharePermission.VIEW
        assert share.project.id == project.id

    @pytest.mark.asyncio
    async def test_get_share_invalid_code(
        self, sharing_service: SharingService
    ) -> None:
        """Test getting a share with invalid code returns None."""
        share = await sharing_service.get_share_by_code("invalid_code")
        assert share is None

    @pytest.mark.asyncio
    async def test_get_project_shares(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test getting all shares for a project."""
        # Create multiple shares
        await sharing_service.create_share(
            project_id=project.id,
            permission=SharePermission.VIEW,
        )
        await sharing_service.create_share(
            project_id=project.id,
            permission=SharePermission.EDIT,
        )

        shares = await sharing_service.get_project_shares(project.id)

        assert len(shares) == 2
        assert all(s.project_id == str(project.id) for s in shares)


class TestAcceptShare:
    """Tests for accepting shares."""

    @pytest.mark.asyncio
    async def test_accept_share_success(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test accepting a share."""
        result = await sharing_service.create_share(
            project_id=project.id,
            permission=SharePermission.COMMENT,
        )

        accept_result = await sharing_service.accept_share(result.share_code)

        assert accept_result["success"] is True
        assert accept_result["projectId"] == str(project.id)
        assert accept_result["permission"] == "comment"

    @pytest.mark.asyncio
    async def test_accept_share_updates_status(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test accepting a share updates its status."""
        result = await sharing_service.create_share(
            project_id=project.id,
            permission=SharePermission.VIEW,
        )

        await sharing_service.accept_share(result.share_code)

        share = await sharing_service.get_share_by_code(result.share_code)
        assert share.status == ShareStatus.ACCEPTED
        assert share.access_count > 0

    @pytest.mark.asyncio
    async def test_accept_invalid_share(
        self, sharing_service: SharingService
    ) -> None:
        """Test accepting invalid share fails."""
        result = await sharing_service.accept_share("invalid_code")
        assert result["success"] is False


class TestRevokeShare:
    """Tests for revoking shares."""

    @pytest.mark.asyncio
    async def test_revoke_share(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test revoking a share."""
        result = await sharing_service.create_share(
            project_id=project.id,
            permission=SharePermission.VIEW,
        )

        revoked = await sharing_service.revoke_share(result.share_id)
        assert revoked is True

        share = await sharing_service.get_share_by_code(result.share_code)
        assert share.status == ShareStatus.REVOKED

    @pytest.mark.asyncio
    async def test_revoke_share_makes_invalid(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test revoked share is no longer valid."""
        result = await sharing_service.create_share(
            project_id=project.id,
            permission=SharePermission.VIEW,
        )

        await sharing_service.revoke_share(result.share_id)

        share = await sharing_service.get_share_by_code(result.share_code)
        assert share.is_valid() is False


class TestUpdatePermission:
    """Tests for updating share permissions."""

    @pytest.mark.asyncio
    async def test_update_permission(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test updating share permission."""
        result = await sharing_service.create_share(
            project_id=project.id,
            permission=SharePermission.VIEW,
        )

        updated = await sharing_service.update_share_permission(
            share_id=result.share_id,
            permission=SharePermission.EDIT,
        )

        assert updated is True

        share = await sharing_service.get_share_by_code(result.share_code)
        assert share.permission == SharePermission.EDIT


class TestComments:
    """Tests for comment functionality."""

    @pytest.mark.asyncio
    async def test_add_comment(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test adding a comment to a project."""
        comment = await sharing_service.add_comment(
            project_id=project.id,
            author_name="Test User",
            content="Great work on this scene!",
        )

        assert comment is not None
        assert comment.content == "Great work on this scene!"
        assert comment.author_name == "Test User"

    @pytest.mark.asyncio
    async def test_get_project_comments(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test getting comments for a project."""
        await sharing_service.add_comment(
            project_id=project.id,
            author_name="User 1",
            content="Comment 1",
        )
        await sharing_service.add_comment(
            project_id=project.id,
            author_name="User 2",
            content="Comment 2",
        )

        comments = await sharing_service.get_project_comments(project.id)

        assert len(comments) == 2

    @pytest.mark.asyncio
    async def test_resolve_comment(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test resolving a comment."""
        comment = await sharing_service.add_comment(
            project_id=project.id,
            author_name="Test User",
            content="Fix this issue",
        )

        resolved = await sharing_service.resolve_comment(comment.id)
        assert resolved is True

        comments = await sharing_service.get_project_comments(
            project.id, include_resolved=True
        )
        resolved_comment = next(c for c in comments if c["id"] == str(comment.id))
        assert resolved_comment["isResolved"] is True

    @pytest.mark.asyncio
    async def test_delete_comment(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test deleting a comment."""
        comment = await sharing_service.add_comment(
            project_id=project.id,
            author_name="Test User",
            content="Delete me",
        )

        deleted = await sharing_service.delete_comment(comment.id)
        assert deleted is True

        comments = await sharing_service.get_project_comments(project.id)
        assert len(comments) == 0


class TestSharePermissions:
    """Tests for share permission checking."""

    @pytest.mark.asyncio
    async def test_view_permission_allows_viewing(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test view permission allows viewing."""
        result = await sharing_service.create_share(
            project_id=project.id,
            permission=SharePermission.VIEW,
        )

        share = await sharing_service.get_share_by_code(result.share_code)
        assert share.can_view() is True
        assert share.can_comment() is False
        assert share.can_edit() is False
        assert share.can_admin() is False

    @pytest.mark.asyncio
    async def test_comment_permission(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test comment permission allows viewing and commenting."""
        result = await sharing_service.create_share(
            project_id=project.id,
            permission=SharePermission.COMMENT,
        )

        share = await sharing_service.get_share_by_code(result.share_code)
        assert share.can_view() is True
        assert share.can_comment() is True
        assert share.can_edit() is False

    @pytest.mark.asyncio
    async def test_edit_permission(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test edit permission allows all except admin."""
        result = await sharing_service.create_share(
            project_id=project.id,
            permission=SharePermission.EDIT,
        )

        share = await sharing_service.get_share_by_code(result.share_code)
        assert share.can_view() is True
        assert share.can_comment() is True
        assert share.can_edit() is True
        assert share.can_admin() is False

    @pytest.mark.asyncio
    async def test_admin_permission(
        self, sharing_service: SharingService, project: Project
    ) -> None:
        """Test admin permission allows everything."""
        result = await sharing_service.create_share(
            project_id=project.id,
            permission=SharePermission.ADMIN,
        )

        share = await sharing_service.get_share_by_code(result.share_code)
        assert share.can_view() is True
        assert share.can_comment() is True
        assert share.can_edit() is True
        assert share.can_admin() is True
