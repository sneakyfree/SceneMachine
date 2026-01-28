"""Tests for Lip Sync API routes."""

import pytest
import pytest_asyncio
from uuid import uuid4, UUID

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.api.main import app
from scenemachine.models.asset import Asset, AssetType, AssetStatus
from scenemachine.database import get_db_manager


class TestLipSyncRoutes:
    """Tests for Lip Sync API endpoints."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncClient:
        """Create a test client."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest_asyncio.fixture
    async def db_session(self) -> AsyncSession:
        """Create a test database session."""
        db_manager = get_db_manager()
        async with db_manager.session() as session:
            yield session

    @pytest_asyncio.fixture
    async def video_asset(self, db_session: AsyncSession) -> Asset:
        """Create a test video asset."""
        project_id = uuid4()
        asset = Asset(
            id=uuid4(),
            project_id=project_id,
            asset_type=AssetType.SHOT_VIDEO,
            status=AssetStatus.READY,
            filename="test_video.mp4",
            file_path="/tmp/test_video.mp4",
            file_size_bytes=1024000,
            mime_type="video/mp4",
        )
        db_session.add(asset)
        await db_session.commit()
        await db_session.refresh(asset)
        return asset

    @pytest_asyncio.fixture
    async def audio_asset(self, db_session: AsyncSession) -> Asset:
        """Create a test audio asset."""
        project_id = uuid4()
        asset = Asset(
            id=uuid4(),
            project_id=project_id,
            asset_type=AssetType.SHOT_AUDIO,
            status=AssetStatus.READY,
            filename="test_audio.wav",
            file_path="/tmp/test_audio.wav",
            file_size_bytes=512000,
            mime_type="audio/wav",
        )
        db_session.add(asset)
        await db_session.commit()
        await db_session.refresh(asset)
        return asset

    @pytest.mark.asyncio
    async def test_start_lipsync_video_not_found(self, client: AsyncClient):
        """Test POST /lipsync/ returns 404 for missing video_id."""
        nonexistent_video_id = str(uuid4())
        audio_id = str(uuid4())
        
        response = await client.post(
            "/api/lipsync/",
            json={
                "video_id": nonexistent_video_id,
                "audio_id": audio_id,
                "provider": "mock",
            },
        )

        assert response.status_code == 404
        assert "video asset" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_start_lipsync_audio_not_found(
        self, client: AsyncClient, video_asset: Asset
    ):
        """Test POST /lipsync/ returns 404 for missing audio_id."""
        nonexistent_audio_id = str(uuid4())
        
        response = await client.post(
            "/api/lipsync/",
            json={
                "video_id": str(video_asset.id),
                "audio_id": nonexistent_audio_id,
                "provider": "mock",
            },
        )

        assert response.status_code == 404
        assert "audio asset" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_start_lipsync_invalid_video_id_format(self, client: AsyncClient):
        """Test POST /lipsync/ returns 400 for invalid video_id format."""
        response = await client.post(
            "/api/lipsync/",
            json={
                "video_id": "not-a-uuid",
                "audio_id": str(uuid4()),
                "provider": "mock",
            },
        )

        assert response.status_code == 400
        assert "invalid video_id format" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_start_lipsync_invalid_audio_id_format(self, client: AsyncClient):
        """Test POST /lipsync/ returns 400 for invalid audio_id format."""
        response = await client.post(
            "/api/lipsync/",
            json={
                "video_id": str(uuid4()),
                "audio_id": "not-a-uuid",
                "provider": "mock",
            },
        )

        assert response.status_code == 400
        assert "invalid audio_id format" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_start_lipsync_wrong_asset_type_video(
        self, client: AsyncClient, audio_asset: Asset
    ):
        """Test POST /lipsync/ returns 400 if video_id points to non-video asset."""
        # Use audio asset ID as video_id (wrong type)
        response = await client.post(
            "/api/lipsync/",
            json={
                "video_id": str(audio_asset.id),
                "audio_id": str(uuid4()),
                "provider": "mock",
            },
        )

        assert response.status_code == 400
        assert "not a video" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_start_lipsync_wrong_asset_type_audio(
        self, client: AsyncClient, video_asset: Asset
    ):
        """Test POST /lipsync/ returns 400 if audio_id points to non-audio asset."""
        # Use video asset ID as audio_id (wrong type)
        response = await client.post(
            "/api/lipsync/",
            json={
                "video_id": str(video_asset.id),
                "audio_id": str(video_asset.id),
                "provider": "mock",
            },
        )

        assert response.status_code == 400
        assert "not an audio file" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_start_lipsync_invalid_provider(
        self, client: AsyncClient, video_asset: Asset, audio_asset: Asset
    ):
        """Test POST /lipsync/ returns 400 for invalid provider."""
        response = await client.post(
            "/api/lipsync/",
            json={
                "video_id": str(video_asset.id),
                "audio_id": str(audio_asset.id),
                "provider": "invalid_provider",
            },
        )

        assert response.status_code == 400
        assert "invalid provider" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_providers(self, client: AsyncClient):
        """Test GET /lipsync/providers returns available providers."""
        response = await client.get("/api/lipsync/providers")

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert isinstance(data["providers"], list)

    @pytest.mark.asyncio
    async def test_list_jobs(self, client: AsyncClient):
        """Test GET /lipsync/jobs returns list of jobs."""
        response = await client.get("/api/lipsync/jobs")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, client: AsyncClient):
        """Test GET /lipsync/jobs/{job_id} returns 404 for non-existent job."""
        response = await client.get("/api/lipsync/jobs/nonexistent-job-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
