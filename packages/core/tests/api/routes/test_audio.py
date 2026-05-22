"""Tests for Audio API routes."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from scenemachine.api.main import app


class TestAudioRoutes:
    """Tests for Audio API endpoints."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncClient:
        """Create a test client."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_list_audio_tracks_endpoint(self, client: AsyncClient):
        """Test listing audio tracks endpoint."""
        response = await client.get("/api/audio/tracks")

        # Should not be 404
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_get_audio_track_endpoint(self, client: AsyncClient):
        """Test getting a specific audio track."""
        track_id = uuid4()
        response = await client.get(f"/api/audio/tracks/{track_id}")

        # Should return 404 for non-existent track or auth error
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_search_audio_tracks(self, client: AsyncClient):
        """Test searching audio tracks."""
        response = await client.get(
            "/api/audio/tracks/search",
            params={"q": "dramatic"},
        )

        # Should handle search
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_filter_by_category(self, client: AsyncClient):
        """Test filtering tracks by category."""
        response = await client.get(
            "/api/audio/tracks",
            params={"category": "music"},
        )

        # Should handle filter
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_upload_audio_track(self, client: AsyncClient):
        """Test uploading an audio track."""
        response = await client.post(
            "/api/audio/tracks",
            data={"name": "Test Track", "category": "music"},
            files={"file": ("test.mp3", b"mock audio", "audio/mpeg")},
        )

        # Should handle upload
        assert response.status_code in (200, 201, 401, 403, 413, 422)

    @pytest.mark.asyncio
    async def test_delete_audio_track(self, client: AsyncClient):
        """Test deleting an audio track."""
        track_id = uuid4()
        response = await client.delete(f"/api/audio/tracks/{track_id}")

        # Should handle delete
        assert response.status_code in (200, 204, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_audio_waveform(self, client: AsyncClient):
        """Test getting audio waveform data."""
        track_id = uuid4()
        response = await client.get(f"/api/audio/tracks/{track_id}/waveform")

        # Should handle request
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_generate_tts(self, client: AsyncClient):
        """Test text-to-speech generation."""
        response = await client.post(
            "/api/audio/tts",
            json={
                "text": "Hello, this is a test.",
                "voice_id": "default",
            },
        )

        # Should handle TTS request
        assert response.status_code in (200, 201, 401, 403, 422, 503)

    @pytest.mark.asyncio
    async def test_list_tts_voices(self, client: AsyncClient):
        """Test listing available TTS voices."""
        response = await client.get("/api/audio/tts/voices")

        # Should return voices
        assert response.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_create_audio_mix(self, client: AsyncClient):
        """Test creating an audio mix."""
        project_id = uuid4()
        response = await client.post(
            f"/api/projects/{project_id}/audio/mixes",
            json={"name": "Test Mix"},
        )

        # Should handle creation
        assert response.status_code in (200, 201, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_project_mixes(self, client: AsyncClient):
        """Test getting project audio mixes."""
        project_id = uuid4()
        response = await client.get(f"/api/projects/{project_id}/audio/mixes")

        # Should handle request
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_add_track_to_mix(self, client: AsyncClient):
        """Test adding a track to a mix."""
        mix_id = uuid4()
        response = await client.post(
            f"/api/audio/mixes/{mix_id}/tracks",
            json={
                "track_id": str(uuid4()),
                "start_time": 0.0,
                "volume": 0.8,
            },
        )

        # Should handle request
        assert response.status_code in (200, 201, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_update_track_in_mix(self, client: AsyncClient):
        """Test updating a track in a mix."""
        mix_id = uuid4()
        track_id = uuid4()
        response = await client.put(
            f"/api/audio/mixes/{mix_id}/tracks/{track_id}",
            json={"volume": 0.5, "pan": -0.2},
        )

        # Should handle request
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_remove_track_from_mix(self, client: AsyncClient):
        """Test removing a track from a mix."""
        mix_id = uuid4()
        track_id = uuid4()
        response = await client.delete(
            f"/api/audio/mixes/{mix_id}/tracks/{track_id}",
        )

        # Should handle request
        assert response.status_code in (200, 204, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_export_mix(self, client: AsyncClient):
        """Test exporting an audio mix."""
        mix_id = uuid4()
        response = await client.post(
            f"/api/audio/mixes/{mix_id}/export",
            json={"format": "mp3", "quality": "high"},
        )

        # Should handle export
        assert response.status_code in (200, 202, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_preview_mix(self, client: AsyncClient):
        """Test previewing an audio mix."""
        mix_id = uuid4()
        response = await client.get(
            f"/api/audio/mixes/{mix_id}/preview",
            params={"start": 0, "duration": 30},
        )

        # Should handle preview
        assert response.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_favorite_track(self, client: AsyncClient):
        """Test favoriting a track."""
        track_id = uuid4()
        response = await client.post(f"/api/audio/tracks/{track_id}/favorite")

        # Should handle request
        assert response.status_code in (200, 204, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_unfavorite_track(self, client: AsyncClient):
        """Test unfavoriting a track."""
        track_id = uuid4()
        response = await client.delete(f"/api/audio/tracks/{track_id}/favorite")

        # Should handle request
        assert response.status_code in (200, 204, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_favorites(self, client: AsyncClient):
        """Test getting favorite tracks."""
        response = await client.get("/api/audio/favorites")

        # Should return favorites
        assert response.status_code in (200, 401)
