"""
Timeline Service

Business logic for timeline editing - tracks, clips, trimming, splitting.
"""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scenemachine.models.track import TimelineClip, Track, TrackType


class TimelineServiceError(Exception):
    """Base exception for timeline service errors."""

    def __init__(self, message: str, code: str = "timeline_error") -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class TrackNotFoundError(TimelineServiceError):
    """Raised when track is not found."""

    def __init__(self, track_id: UUID) -> None:
        super().__init__(f"Track {track_id} not found", code="track_not_found")


class ClipNotFoundError(TimelineServiceError):
    """Raised when clip is not found."""

    def __init__(self, clip_id: UUID) -> None:
        super().__init__(f"Clip {clip_id} not found", code="clip_not_found")


class TimelineService:
    """Service for timeline editing operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ==================== Track Operations ====================

    async def get_tracks(self, project_id: UUID) -> list[Track]:
        """Get all tracks for a project, ordered by position.

        Args:
            project_id: Project UUID

        Returns:
            List of Track objects with clips loaded
        """
        result = await self.session.execute(
            select(Track)
            .where(Track.project_id == project_id)
            .options(selectinload(Track.clips))
            .order_by(Track.order)
        )
        return list(result.scalars().all())

    async def create_track(
        self,
        project_id: UUID,
        name: str,
        track_type: TrackType,
        order: int | None = None,
        color: str | None = None,
    ) -> Track:
        """Create a new track.

        Args:
            project_id: Project UUID
            name: Track display name
            track_type: Type of track
            order: Position (auto-assigned if None)
            color: Optional hex color

        Returns:
            Created Track object
        """
        # Auto-assign order if not provided
        if order is None:
            result = await self.session.execute(select(Track).where(Track.project_id == project_id))
            existing_tracks = result.scalars().all()
            order = len(existing_tracks)

        track = Track(
            project_id=project_id,
            name=name,
            track_type=track_type,
            order=order,
            color=color,
        )

        self.session.add(track)
        await self.session.commit()
        await self.session.refresh(track)

        return track

    async def update_track(
        self,
        track_id: UUID,
        name: str | None = None,
        color: str | None = None,
        is_visible: bool | None = None,
        is_locked: bool | None = None,
        is_muted: bool | None = None,
        is_solo: bool | None = None,
        volume: float | None = None,
        pan: float | None = None,
    ) -> Track:
        """Update track properties.

        Args:
            track_id: Track UUID
            name: New name
            color: New color
            is_visible: Visibility state
            is_locked: Lock state
            is_muted: Mute state
            is_solo: Solo state
            volume: Volume level
            pan: Pan position

        Returns:
            Updated Track

        Raises:
            TrackNotFoundError: If track not found
        """
        result = await self.session.execute(select(Track).where(Track.id == track_id))
        track = result.scalar_one_or_none()

        if not track:
            raise TrackNotFoundError(track_id)

        if name is not None:
            track.name = name
        if color is not None:
            track.color = color
        if is_visible is not None:
            track.is_visible = is_visible
        if is_locked is not None:
            track.is_locked = is_locked
        if is_muted is not None:
            track.is_muted = is_muted
        if is_solo is not None:
            track.is_solo = is_solo
        if volume is not None:
            track.volume = max(0.0, min(1.0, volume))
        if pan is not None:
            track.pan = max(-1.0, min(1.0, pan))

        await self.session.commit()
        await self.session.refresh(track)

        return track

    async def delete_track(self, track_id: UUID) -> bool:
        """Delete a track and all its clips.

        Args:
            track_id: Track UUID

        Returns:
            True if deleted

        Raises:
            TrackNotFoundError: If track not found
        """
        result = await self.session.execute(select(Track).where(Track.id == track_id))
        track = result.scalar_one_or_none()

        if not track:
            raise TrackNotFoundError(track_id)

        await self.session.delete(track)
        await self.session.commit()

        return True

    async def reorder_tracks(self, project_id: UUID, track_ids: list[UUID]) -> list[Track]:
        """Reorder tracks by setting new positions.

        Args:
            project_id: Project UUID
            track_ids: Track IDs in new order

        Returns:
            Updated tracks in new order
        """
        for i, track_id in enumerate(track_ids):
            await self.session.execute(
                update(Track)
                .where(Track.id == track_id, Track.project_id == project_id)
                .values(order=i)
            )

        await self.session.commit()
        return await self.get_tracks(project_id)

    # ==================== Clip Operations ====================

    async def create_clip(
        self,
        track_id: UUID,
        source_id: UUID,
        source_type: str,
        start_time: float,
        duration: float,
        name: str | None = None,
        z_index: int = 0,
    ) -> TimelineClip:
        """Create a new clip on a track.

        Args:
            track_id: Track UUID
            source_id: Source asset/shot UUID
            source_type: Type of source (shot, audio, text)
            start_time: Position on timeline (seconds)
            duration: Duration (seconds)
            name: Display name
            z_index: Stack order

        Returns:
            Created TimelineClip
        """
        clip = TimelineClip(
            track_id=track_id,
            source_id=source_id,
            source_type=source_type,
            start_time=start_time,
            duration=duration,
            name=name,
            z_index=z_index,
        )

        self.session.add(clip)
        await self.session.commit()
        await self.session.refresh(clip)

        return clip

    async def get_clip(self, clip_id: UUID) -> TimelineClip | None:
        """Get clip by ID.

        Args:
            clip_id: Clip UUID

        Returns:
            TimelineClip or None
        """
        result = await self.session.execute(select(TimelineClip).where(TimelineClip.id == clip_id))
        return result.scalar_one_or_none()

    async def update_clip(
        self,
        clip_id: UUID,
        start_time: float | None = None,
        duration: float | None = None,
        trim_start: float | None = None,
        trim_end: float | None = None,
        z_index: int | None = None,
        volume: float | None = None,
        fade_in: float | None = None,
        fade_out: float | None = None,
    ) -> TimelineClip:
        """Update clip properties.

        Args:
            clip_id: Clip UUID
            start_time: New start time
            duration: New duration
            trim_start: Trim from source start
            trim_end: Trim from source end
            z_index: New z-index
            volume: Volume level
            fade_in: Fade in duration
            fade_out: Fade out duration

        Returns:
            Updated TimelineClip

        Raises:
            ClipNotFoundError: If clip not found
        """
        clip = await self.get_clip(clip_id)
        if not clip:
            raise ClipNotFoundError(clip_id)

        if start_time is not None:
            clip.start_time = start_time
        if duration is not None:
            clip.duration = duration
        if trim_start is not None:
            clip.trim_start = trim_start
        if trim_end is not None:
            clip.trim_end = trim_end
        if z_index is not None:
            clip.z_index = z_index
        if volume is not None:
            clip.volume = max(0.0, min(1.0, volume))
        if fade_in is not None:
            clip.fade_in = fade_in
        if fade_out is not None:
            clip.fade_out = fade_out

        await self.session.commit()
        await self.session.refresh(clip)

        return clip

    async def delete_clip(self, clip_id: UUID) -> bool:
        """Delete a clip.

        Args:
            clip_id: Clip UUID

        Returns:
            True if deleted

        Raises:
            ClipNotFoundError: If clip not found
        """
        clip = await self.get_clip(clip_id)
        if not clip:
            raise ClipNotFoundError(clip_id)

        await self.session.delete(clip)
        await self.session.commit()

        return True

    async def trim_clip(
        self,
        clip_id: UUID,
        trim_start: float,
        trim_end: float,
    ) -> TimelineClip:
        """Trim clip from start and/or end.

        Args:
            clip_id: Clip UUID
            trim_start: Seconds to trim from start
            trim_end: Seconds to trim from end

        Returns:
            Updated TimelineClip
        """
        return await self.update_clip(
            clip_id,
            trim_start=trim_start,
            trim_end=trim_end,
        )

    async def split_clip(
        self, clip_id: UUID, split_time: float
    ) -> tuple[TimelineClip, TimelineClip]:
        """Split clip at specified time.

        Args:
            clip_id: Clip UUID
            split_time: Time to split at (relative to clip start)

        Returns:
            Tuple of (first_clip, second_clip)

        Raises:
            ClipNotFoundError: If clip not found
            TimelineServiceError: If split time is invalid
        """
        clip = await self.get_clip(clip_id)
        if not clip:
            raise ClipNotFoundError(clip_id)

        if split_time <= 0 or split_time >= clip.duration:
            raise TimelineServiceError(
                "Split time must be within clip duration",
                code="invalid_split_time",
            )

        # Calculate new durations
        first_duration = split_time
        second_duration = clip.duration - split_time

        # Update first clip
        clip.duration = first_duration

        # Create second clip
        second_clip = TimelineClip(
            track_id=clip.track_id,
            source_id=clip.source_id,
            source_type=clip.source_type,
            start_time=clip.start_time + first_duration,
            duration=second_duration,
            trim_start=clip.trim_start + first_duration,
            trim_end=clip.trim_end,
            z_index=clip.z_index,
            name=f"{clip.name} (2)" if clip.name else None,
            volume=clip.volume,
        )

        # Adjust first clip's trim_end
        clip.trim_end = 0  # Second half is now a separate clip

        self.session.add(second_clip)
        await self.session.commit()
        await self.session.refresh(clip)
        await self.session.refresh(second_clip)

        return clip, second_clip

    async def ripple_delete(self, clip_id: UUID, track_id: UUID) -> list[TimelineClip]:
        """Delete clip and shift following clips to fill gap.

        Args:
            clip_id: Clip to delete
            track_id: Track containing clip

        Returns:
            Updated list of clips on track
        """
        clip = await self.get_clip(clip_id)
        if not clip:
            raise ClipNotFoundError(clip_id)

        gap_duration = clip.duration
        gap_start = clip.start_time

        # Delete the clip
        await self.session.delete(clip)

        # Shift following clips
        result = await self.session.execute(
            select(TimelineClip).where(
                TimelineClip.track_id == track_id,
                TimelineClip.start_time > gap_start,
            )
        )

        for following_clip in result.scalars():
            following_clip.start_time -= gap_duration

        await self.session.commit()

        # Return updated clips
        result = await self.session.execute(
            select(TimelineClip)
            .where(TimelineClip.track_id == track_id)
            .order_by(TimelineClip.start_time)
        )
        return list(result.scalars().all())

    async def move_clip_to_track(
        self, clip_id: UUID, target_track_id: UUID, start_time: float | None = None
    ) -> TimelineClip:
        """Move clip to a different track.

        Args:
            clip_id: Clip UUID
            target_track_id: Target track UUID
            start_time: Optional new start time

        Returns:
            Updated TimelineClip
        """
        clip = await self.get_clip(clip_id)
        if not clip:
            raise ClipNotFoundError(clip_id)

        clip.track_id = target_track_id
        if start_time is not None:
            clip.start_time = start_time

        await self.session.commit()
        await self.session.refresh(clip)

        return clip
