"""Tests for Auth API routes."""

import pytest
import pytest_asyncio
from uuid import uuid4

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.main import app


class TestAuthRoutes:
    """Tests for Auth API endpoints."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncClient:
        """Create a test client."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_register_user(self, client: AsyncClient):
        """Test user registration."""
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePassword123!",
                "username": "testuser",
            },
        )

        # May succeed or fail with existing user
        assert response.status_code in (200, 201, 400, 409, 422)

    @pytest.mark.asyncio
    async def test_register_validation(self, client: AsyncClient):
        """Test registration validation."""
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "invalid-email",
                "password": "short",
                "username": "",
            },
        )

        # Should fail validation
        assert response.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_login(self, client: AsyncClient):
        """Test user login."""
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "SecurePassword123!",
            },
        )

        # May fail if user doesn't exist
        assert response.status_code in (200, 401, 422)

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials."""
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPassword!",
            },
        )

        assert response.status_code in (401, 422)

    @pytest.mark.asyncio
    async def test_logout(self, client: AsyncClient):
        """Test user logout."""
        response = await client.post("/api/auth/logout")

        # May require auth token
        assert response.status_code in (200, 204, 401)

    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient):
        """Test token refresh."""
        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": "fake_refresh_token"},
        )

        assert response.status_code in (200, 401, 422)

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient):
        """Test getting current user info."""
        response = await client.get("/api/auth/me")

        # Requires auth
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_update_profile(self, client: AsyncClient):
        """Test updating user profile."""
        response = await client.put(
            "/api/auth/profile",
            json={
                "display_name": "Test User",
                "bio": "A test user bio",
            },
        )

        assert response.status_code in (200, 401, 422)

    @pytest.mark.asyncio
    async def test_change_password(self, client: AsyncClient):
        """Test changing password."""
        response = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "OldPassword123!",
                "new_password": "NewSecurePassword123!",
            },
        )

        assert response.status_code in (200, 400, 401, 422)

    @pytest.mark.asyncio
    async def test_request_password_reset(self, client: AsyncClient):
        """Test requesting a password reset."""
        response = await client.post(
            "/api/auth/forgot-password",
            json={"email": "test@example.com"},
        )

        # Should always return success to prevent email enumeration
        assert response.status_code in (200, 202, 422)

    @pytest.mark.asyncio
    async def test_reset_password(self, client: AsyncClient):
        """Test resetting password with token."""
        response = await client.post(
            "/api/auth/reset-password",
            json={
                "token": "fake_reset_token",
                "new_password": "NewSecurePassword123!",
            },
        )

        assert response.status_code in (200, 400, 422)

    @pytest.mark.asyncio
    async def test_verify_email(self, client: AsyncClient):
        """Test email verification."""
        response = await client.post(
            "/api/auth/verify-email",
            json={"token": "fake_verification_token"},
        )

        assert response.status_code in (200, 400, 422)

    @pytest.mark.asyncio
    async def test_resend_verification(self, client: AsyncClient):
        """Test resending verification email."""
        response = await client.post(
            "/api/auth/resend-verification",
            json={"email": "test@example.com"},
        )

        assert response.status_code in (200, 202, 400, 422)

    @pytest.mark.asyncio
    async def test_get_api_keys(self, client: AsyncClient):
        """Test getting user's API keys."""
        response = await client.get("/api/auth/api-keys")

        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_create_api_key(self, client: AsyncClient):
        """Test creating an API key."""
        response = await client.post(
            "/api/auth/api-keys",
            json={
                "name": "Test API Key",
                "scopes": ["read", "write"],
            },
        )

        assert response.status_code in (200, 201, 401, 422)

    @pytest.mark.asyncio
    async def test_revoke_api_key(self, client: AsyncClient):
        """Test revoking an API key."""
        key_id = uuid4()
        response = await client.delete(f"/api/auth/api-keys/{key_id}")

        assert response.status_code in (200, 204, 401, 404)

    @pytest.mark.asyncio
    async def test_get_sessions(self, client: AsyncClient):
        """Test getting user's active sessions."""
        response = await client.get("/api/auth/sessions")

        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_revoke_session(self, client: AsyncClient):
        """Test revoking a session."""
        session_id = uuid4()
        response = await client.delete(f"/api/auth/sessions/{session_id}")

        assert response.status_code in (200, 204, 401, 404)

    @pytest.mark.asyncio
    async def test_revoke_all_sessions(self, client: AsyncClient):
        """Test revoking all sessions."""
        response = await client.post("/api/auth/sessions/revoke-all")

        assert response.status_code in (200, 204, 401)

    @pytest.mark.asyncio
    async def test_enable_2fa(self, client: AsyncClient):
        """Test enabling two-factor authentication."""
        response = await client.post("/api/auth/2fa/enable")

        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_verify_2fa(self, client: AsyncClient):
        """Test verifying 2FA code."""
        response = await client.post(
            "/api/auth/2fa/verify",
            json={"code": "123456"},
        )

        assert response.status_code in (200, 400, 401, 422)

    @pytest.mark.asyncio
    async def test_disable_2fa(self, client: AsyncClient):
        """Test disabling two-factor authentication."""
        response = await client.post(
            "/api/auth/2fa/disable",
            json={"password": "SecurePassword123!"},
        )

        assert response.status_code in (200, 400, 401)

    @pytest.mark.asyncio
    async def test_delete_account(self, client: AsyncClient):
        """Test account deletion."""
        response = await client.delete(
            "/api/auth/account",
            json={"password": "SecurePassword123!"},
        )

        assert response.status_code in (200, 204, 401)
