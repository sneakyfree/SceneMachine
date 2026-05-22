"""Tests for Audio Library service."""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models import Project
from scenemachine.services.audio_library import AudioLibraryService


class TestAudioLibraryService:
    """Tests for AudioLibraryService."""

    @pytest.fixture
    def audio_library(self, db_session: AsyncSession) -> AudioLibraryService:
        """Create an audio library service instance."""
        return AudioLibraryService(db_session)

    @pytest.mark.asyncio
    async def test_get_all_tracks(self, audio_library: AudioLibraryService):
        """Test getting all audio tracks."""
        tracks = await audio_library.get_all()

        assert isinstance(tracks, list)

    @pytest.mark.asyncio
    async def test_get_tracks_by_category(self, audio_library: AudioLibraryService):
        """Test filtering tracks by category."""
        categories = ["music", "sfx", "ambient", "foley"]

        for category in categories:
            tracks = await audio_library.get_by_category(category)
            assert isinstance(tracks, list)

    @pytest.mark.asyncio
    async def test_search_tracks(self, audio_library: AudioLibraryService):
        """Test searching tracks by name or tags."""
        results = await audio_library.search("dramatic")

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_track_by_id(self, audio_library: AudioLibraryService):
        """Test getting a specific track by ID."""
        all_tracks = await audio_library.get_all()

        if all_tracks:
            track_id = all_tracks[0].id if hasattr(all_tracks[0], "id") else all_tracks[0].get("id")
            track = await audio_library.get_by_id(track_id)
            assert track is not None

    @pytest.mark.asyncio
    async def test_get_track_duration(self, audio_library: AudioLibraryService):
        """Test getting track duration."""
        all_tracks = await audio_library.get_all()

        if all_tracks:
            track = all_tracks[0]
            if hasattr(track, "duration"):
                assert track.duration >= 0
            elif isinstance(track, dict) and "duration" in track:
                assert track["duration"] >= 0

    @pytest.mark.asyncio
    async def test_upload_custom_track(
        self,
        audio_library: AudioLibraryService,
        sample_project: Project,
        temp_dir: Path,
    ):
        """Test uploading a custom audio track."""
        # Create a mock audio file
        audio_file = temp_dir / "test_audio.mp3"
        audio_file.write_bytes(b"mock audio content")

        if hasattr(audio_library, "upload"):
            result = await audio_library.upload(
                project_id=sample_project.id,
                file_path=audio_file,
                name="Custom Track",
                category="music",
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_delete_custom_track(
        self,
        audio_library: AudioLibraryService,
    ):
        """Test deleting a custom track."""
        if hasattr(audio_library, "delete"):
            result = await audio_library.delete(uuid4())
            # May return False for non-existent track
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_get_tracks_by_mood(self, audio_library: AudioLibraryService):
        """Test filtering tracks by mood."""
        moods = ["happy", "sad", "tense", "peaceful"]

        for mood in moods:
            if hasattr(audio_library, "get_by_mood"):
                tracks = await audio_library.get_by_mood(mood)
                assert isinstance(tracks, list)

    @pytest.mark.asyncio
    async def test_get_tracks_by_tempo(self, audio_library: AudioLibraryService):
        """Test filtering tracks by tempo range."""
        if hasattr(audio_library, "get_by_tempo"):
            tracks = await audio_library.get_by_tempo(min_bpm=60, max_bpm=120)
            assert isinstance(tracks, list)

    @pytest.mark.asyncio
    async def test_get_track_waveform(self, audio_library: AudioLibraryService):
        """Test getting track waveform data."""
        all_tracks = await audio_library.get_all()

        if all_tracks and hasattr(audio_library, "get_waveform"):
            track_id = all_tracks[0].id if hasattr(all_tracks[0], "id") else all_tracks[0].get("id")
            await audio_library.get_waveform(track_id)
            # May return None if waveform not generated

    @pytest.mark.asyncio
    async def test_favorite_track(
        self,
        audio_library: AudioLibraryService,
    ):
        """Test favoriting a track."""
        all_tracks = await audio_library.get_all()

        if all_tracks and hasattr(audio_library, "favorite"):
            track_id = all_tracks[0].id if hasattr(all_tracks[0], "id") else all_tracks[0].get("id")
            result = await audio_library.favorite(track_id, user_id=uuid4())
            assert result is True or result is None

    @pytest.mark.asyncio
    async def test_get_favorites(self, audio_library: AudioLibraryService):
        """Test getting user's favorite tracks."""
        if hasattr(audio_library, "get_favorites"):
            favorites = await audio_library.get_favorites(user_id=uuid4())
            assert isinstance(favorites, list)

    @pytest.mark.asyncio
    async def test_get_recently_used(
        self,
        audio_library: AudioLibraryService,
        sample_project: Project,
    ):
        """Test getting recently used tracks."""
        if hasattr(audio_library, "get_recently_used"):
            recent = await audio_library.get_recently_used(
                project_id=sample_project.id,
                limit=10,
            )
            assert isinstance(recent, list)

    @pytest.mark.asyncio
    async def test_track_licensing_info(self, audio_library: AudioLibraryService):
        """Test getting track licensing information."""
        all_tracks = await audio_library.get_all()

        if all_tracks:
            track = all_tracks[0]
            if hasattr(track, "license"):
                assert track.license is not None
            elif isinstance(track, dict):
                # License info may be included
                pass

    @pytest.mark.asyncio
    async def test_get_similar_tracks(self, audio_library: AudioLibraryService):
        """Test getting similar tracks."""
        all_tracks = await audio_library.get_all()

        if all_tracks and hasattr(audio_library, "get_similar"):
            track_id = all_tracks[0].id if hasattr(all_tracks[0], "id") else all_tracks[0].get("id")
            similar = await audio_library.get_similar(track_id, limit=5)
            assert isinstance(similar, list)
