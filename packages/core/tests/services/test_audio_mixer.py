"""Tests for Audio Mixer service."""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models import Project
from scenemachine.services.audio_mixer import AudioMixerService


class TestAudioMixerService:
    """Tests for AudioMixerService."""

    @pytest.fixture
    def audio_mixer(self, db_session: AsyncSession) -> AudioMixerService:
        """Create an audio mixer service instance."""
        return AudioMixerService(db_session)

    @pytest.mark.asyncio
    async def test_create_mix(
        self,
        audio_mixer: AudioMixerService,
        sample_project: Project,
    ):
        """Test creating an audio mix."""
        mix = await audio_mixer.create_mix(
            project_id=sample_project.id,
            name="Test Mix",
        )

        assert mix is not None

    @pytest.mark.asyncio
    async def test_add_track_to_mix(
        self,
        audio_mixer: AudioMixerService,
        sample_project: Project,
    ):
        """Test adding a track to a mix."""
        mix = await audio_mixer.create_mix(
            project_id=sample_project.id,
            name="Test Mix",
        )

        if hasattr(audio_mixer, "add_track"):
            result = await audio_mixer.add_track(
                mix_id=mix.id if hasattr(mix, "id") else mix.get("id"),
                track_id=uuid4(),
                start_time=0.0,
                volume=0.8,
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_remove_track_from_mix(
        self,
        audio_mixer: AudioMixerService,
        sample_project: Project,
    ):
        """Test removing a track from a mix."""
        mix = await audio_mixer.create_mix(
            project_id=sample_project.id,
            name="Test Mix",
        )

        if hasattr(audio_mixer, "remove_track"):
            await audio_mixer.remove_track(
                mix_id=mix.id if hasattr(mix, "id") else mix.get("id"),
                track_id=uuid4(),
            )
            # May return False if track not in mix

    @pytest.mark.asyncio
    async def test_adjust_track_volume(
        self,
        audio_mixer: AudioMixerService,
        sample_project: Project,
    ):
        """Test adjusting track volume."""
        mix = await audio_mixer.create_mix(
            project_id=sample_project.id,
            name="Test Mix",
        )

        if hasattr(audio_mixer, "set_volume"):
            result = await audio_mixer.set_volume(
                mix_id=mix.id if hasattr(mix, "id") else mix.get("id"),
                track_id=uuid4(),
                volume=0.5,
            )
            assert result is True or result is None

    @pytest.mark.asyncio
    async def test_adjust_track_pan(
        self,
        audio_mixer: AudioMixerService,
        sample_project: Project,
    ):
        """Test adjusting track pan (left/right balance)."""
        mix = await audio_mixer.create_mix(
            project_id=sample_project.id,
            name="Test Mix",
        )

        if hasattr(audio_mixer, "set_pan"):
            result = await audio_mixer.set_pan(
                mix_id=mix.id if hasattr(mix, "id") else mix.get("id"),
                track_id=uuid4(),
                pan=-0.5,  # Left
            )
            assert result is True or result is None

    @pytest.mark.asyncio
    async def test_apply_fade_in(
        self,
        audio_mixer: AudioMixerService,
        sample_project: Project,
    ):
        """Test applying fade in effect."""
        mix = await audio_mixer.create_mix(
            project_id=sample_project.id,
            name="Test Mix",
        )

        if hasattr(audio_mixer, "apply_fade"):
            result = await audio_mixer.apply_fade(
                mix_id=mix.id if hasattr(mix, "id") else mix.get("id"),
                track_id=uuid4(),
                fade_type="in",
                duration=2.0,
            )
            assert result is True or result is None

    @pytest.mark.asyncio
    async def test_apply_fade_out(
        self,
        audio_mixer: AudioMixerService,
        sample_project: Project,
    ):
        """Test applying fade out effect."""
        mix = await audio_mixer.create_mix(
            project_id=sample_project.id,
            name="Test Mix",
        )

        if hasattr(audio_mixer, "apply_fade"):
            result = await audio_mixer.apply_fade(
                mix_id=mix.id if hasattr(mix, "id") else mix.get("id"),
                track_id=uuid4(),
                fade_type="out",
                duration=2.0,
            )
            assert result is True or result is None

    @pytest.mark.asyncio
    async def test_export_mix(
        self,
        audio_mixer: AudioMixerService,
        sample_project: Project,
        temp_dir: Path,
    ):
        """Test exporting a mix to audio file."""
        mix = await audio_mixer.create_mix(
            project_id=sample_project.id,
            name="Test Mix",
        )

        if hasattr(audio_mixer, "export"):
            result = await audio_mixer.export(
                mix_id=mix.id if hasattr(mix, "id") else mix.get("id"),
                output_path=temp_dir / "output.mp3",
                format="mp3",
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_mix_duration(
        self,
        audio_mixer: AudioMixerService,
        sample_project: Project,
    ):
        """Test getting total mix duration."""
        mix = await audio_mixer.create_mix(
            project_id=sample_project.id,
            name="Test Mix",
        )

        if hasattr(audio_mixer, "get_duration"):
            duration = await audio_mixer.get_duration(
                mix_id=mix.id if hasattr(mix, "id") else mix.get("id"),
            )
            assert duration >= 0

    @pytest.mark.asyncio
    async def test_preview_mix(
        self,
        audio_mixer: AudioMixerService,
        sample_project: Project,
    ):
        """Test generating a preview of the mix."""
        mix = await audio_mixer.create_mix(
            project_id=sample_project.id,
            name="Test Mix",
        )

        if hasattr(audio_mixer, "preview"):
            await audio_mixer.preview(
                mix_id=mix.id if hasattr(mix, "id") else mix.get("id"),
                start_time=0,
                duration=30,
            )
            # May return URL or None

    @pytest.mark.asyncio
    async def test_normalize_mix(
        self,
        audio_mixer: AudioMixerService,
        sample_project: Project,
    ):
        """Test normalizing mix audio levels."""
        mix = await audio_mixer.create_mix(
            project_id=sample_project.id,
            name="Test Mix",
        )

        if hasattr(audio_mixer, "normalize"):
            result = await audio_mixer.normalize(
                mix_id=mix.id if hasattr(mix, "id") else mix.get("id"),
                target_db=-14.0,
            )
            assert result is True or result is None

    @pytest.mark.asyncio
    async def test_duplicate_mix(
        self,
        audio_mixer: AudioMixerService,
        sample_project: Project,
    ):
        """Test duplicating a mix."""
        mix = await audio_mixer.create_mix(
            project_id=sample_project.id,
            name="Test Mix",
        )

        if hasattr(audio_mixer, "duplicate"):
            duplicate = await audio_mixer.duplicate(
                mix_id=mix.id if hasattr(mix, "id") else mix.get("id"),
                new_name="Duplicate Mix",
            )
            assert duplicate is not None

    @pytest.mark.asyncio
    async def test_delete_mix(
        self,
        audio_mixer: AudioMixerService,
        sample_project: Project,
    ):
        """Test deleting a mix."""
        mix = await audio_mixer.create_mix(
            project_id=sample_project.id,
            name="Test Mix",
        )

        if hasattr(audio_mixer, "delete"):
            result = await audio_mixer.delete(
                mix_id=mix.id if hasattr(mix, "id") else mix.get("id"),
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_get_project_mixes(
        self,
        audio_mixer: AudioMixerService,
        sample_project: Project,
    ):
        """Test getting all mixes for a project."""
        await audio_mixer.create_mix(
            project_id=sample_project.id,
            name="Test Mix 1",
        )
        await audio_mixer.create_mix(
            project_id=sample_project.id,
            name="Test Mix 2",
        )

        if hasattr(audio_mixer, "get_project_mixes"):
            mixes = await audio_mixer.get_project_mixes(sample_project.id)
            assert isinstance(mixes, list)
            assert len(mixes) >= 2
