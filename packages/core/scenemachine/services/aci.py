"""ActCast Index (ACI) Rating Service.

Calculates and manages performer ACI scores.

ACI Formula:
    ACI = (Placement Rate × 0.4) + (Rehire Rate × 0.3) + (Audience Buzz × 0.2) + (MotionScore × 0.1)

All components are normalized to 0-100 scale.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scenemachine.models import (
    Booking,
    BookingStatus,
    PerformanceTake,
    Performer,
    PerformerRating,
)

logger = logging.getLogger(__name__)


# ACI Weight configuration
ACI_WEIGHTS = {
    "placement_rate": 0.4,
    "rehire_rate": 0.3,
    "audience_buzz": 0.2,
    "motion_score": 0.1,
}

# Minimum data requirements for reliable ACI
MIN_BOOKINGS_FOR_RELIABLE_ACI = 5
MIN_RATINGS_FOR_RELIABLE_ACI = 3
MIN_TAKES_FOR_MOTION_SCORE = 3

# Default score for new performers
DEFAULT_ACI_SCORE = 50.0

# Recency weighting for audience buzz (days)
BUZZ_RECENCY_WINDOW_DAYS = 30


@dataclass
class ACIBreakdown:
    """Detailed breakdown of ACI score components."""

    placement_rate: float
    placement_rate_weighted: float
    rehire_rate: float
    rehire_rate_weighted: float
    audience_buzz: float
    audience_buzz_weighted: float
    motion_score: float
    motion_score_weighted: float
    total_score: float
    is_reliable: bool
    data_quality: str  # "low", "medium", "high"
    total_bookings: int
    total_ratings: int
    total_takes: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "placement_rate": round(self.placement_rate, 2),
            "placement_rate_weighted": round(self.placement_rate_weighted, 2),
            "rehire_rate": round(self.rehire_rate, 2),
            "rehire_rate_weighted": round(self.rehire_rate_weighted, 2),
            "audience_buzz": round(self.audience_buzz, 2),
            "audience_buzz_weighted": round(self.audience_buzz_weighted, 2),
            "motion_score": round(self.motion_score, 2),
            "motion_score_weighted": round(self.motion_score_weighted, 2),
            "total_score": round(self.total_score, 2),
            "is_reliable": self.is_reliable,
            "data_quality": self.data_quality,
            "total_bookings": self.total_bookings,
            "total_ratings": self.total_ratings,
            "total_takes": self.total_takes,
        }


class ACIService:
    """
    ActCast Index (ACI) rating service.

    Calculates comprehensive performer ratings based on:
    - Placement Rate: Completed bookings / Total booking requests
    - Rehire Rate: Percentage of directors who indicated "would rehire"
    - Audience Buzz: Community engagement with public reviews (recency weighted)
    - MotionScore: Technical quality of motion capture data
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self._session = session

    async def calculate_aci(
        self,
        performer_id: UUID,
        update_performer: bool = True,
    ) -> ACIBreakdown:
        """
        Calculate the complete ACI score for a performer.

        Args:
            performer_id: The performer's UUID
            update_performer: Whether to update the performer record

        Returns:
            ACIBreakdown with all component scores
        """
        # Get the performer
        performer = await self._get_performer(performer_id)
        if not performer:
            raise ValueError(f"Performer {performer_id} not found")

        # Calculate each component
        placement_rate = await self._calculate_placement_rate(performer_id)
        rehire_rate = await self._calculate_rehire_rate(performer_id)
        audience_buzz = await self._calculate_audience_buzz(performer_id)
        motion_score = await self._calculate_motion_score(performer_id)

        # Apply weights
        placement_weighted = placement_rate * ACI_WEIGHTS["placement_rate"]
        rehire_weighted = rehire_rate * ACI_WEIGHTS["rehire_rate"]
        buzz_weighted = audience_buzz * ACI_WEIGHTS["audience_buzz"]
        motion_weighted = motion_score * ACI_WEIGHTS["motion_score"]

        # Calculate total
        total_score = placement_weighted + rehire_weighted + buzz_weighted + motion_weighted

        # Get data quality metrics
        total_bookings = performer.total_bookings
        total_ratings = len(performer.ratings) if performer.ratings else 0
        total_takes = len(performer.takes) if performer.takes else 0

        # Determine reliability
        is_reliable = (
            total_bookings >= MIN_BOOKINGS_FOR_RELIABLE_ACI
            and total_ratings >= MIN_RATINGS_FOR_RELIABLE_ACI
        )

        # Determine data quality
        if total_bookings >= 20 and total_ratings >= 10:
            data_quality = "high"
        elif total_bookings >= MIN_BOOKINGS_FOR_RELIABLE_ACI:
            data_quality = "medium"
        else:
            data_quality = "low"

        breakdown = ACIBreakdown(
            placement_rate=placement_rate,
            placement_rate_weighted=placement_weighted,
            rehire_rate=rehire_rate,
            rehire_rate_weighted=rehire_weighted,
            audience_buzz=audience_buzz,
            audience_buzz_weighted=buzz_weighted,
            motion_score=motion_score,
            motion_score_weighted=motion_weighted,
            total_score=total_score,
            is_reliable=is_reliable,
            data_quality=data_quality,
            total_bookings=total_bookings,
            total_ratings=total_ratings,
            total_takes=total_takes,
        )

        # Update performer record
        if update_performer:
            performer.aci_score = total_score
            await self._session.commit()

        logger.info(
            f"Calculated ACI for performer {performer_id}: {total_score:.1f} "
            f"(placement={placement_rate:.1f}, rehire={rehire_rate:.1f}, "
            f"buzz={audience_buzz:.1f}, motion={motion_score:.1f})"
        )

        return breakdown

    async def _get_performer(self, performer_id: UUID) -> Performer | None:
        """Get performer with relationships loaded."""
        stmt = (
            select(Performer)
            .where(Performer.id == performer_id)
            .options(
                selectinload(Performer.ratings),
                selectinload(Performer.takes),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _calculate_placement_rate(self, performer_id: UUID) -> float:
        """
        Calculate Placement Rate.

        Placement Rate = (Completed Bookings / Total Booking Requests) × 100

        Measures how often a performer successfully completes bookings.
        New performers get default score of 50.
        """
        # Count total bookings (excluding those still in matching phase)
        total_stmt = select(func.count(Booking.id)).where(
            and_(
                Booking.performer_id == performer_id,
                Booking.status.notin_([BookingStatus.REQUESTED, BookingStatus.MATCHING]),
            )
        )
        total_result = await self._session.execute(total_stmt)
        total_bookings = total_result.scalar() or 0

        if total_bookings == 0:
            return DEFAULT_ACI_SCORE

        # Count completed bookings
        completed_stmt = select(func.count(Booking.id)).where(
            and_(
                Booking.performer_id == performer_id,
                Booking.status == BookingStatus.COMPLETED,
            )
        )
        completed_result = await self._session.execute(completed_stmt)
        completed_bookings = completed_result.scalar() or 0

        return (completed_bookings / total_bookings) * 100

    async def _calculate_rehire_rate(self, performer_id: UUID) -> float:
        """
        Calculate Rehire Rate.

        Rehire Rate = (Ratings with would_rehire=True / Total Ratings) × 100

        Based on the "would_rehire" boolean from PerformerRating.
        """
        # Get total ratings
        total_stmt = select(func.count(PerformerRating.id)).where(
            PerformerRating.performer_id == performer_id
        )
        total_result = await self._session.execute(total_stmt)
        total_ratings = total_result.scalar() or 0

        if total_ratings == 0:
            return DEFAULT_ACI_SCORE

        # Count would_rehire
        rehire_stmt = select(func.count(PerformerRating.id)).where(
            and_(
                PerformerRating.performer_id == performer_id,
                PerformerRating.would_rehire == True,  # noqa: E712
            )
        )
        rehire_result = await self._session.execute(rehire_stmt)
        would_rehire_count = rehire_result.scalar() or 0

        return (would_rehire_count / total_ratings) * 100

    async def _calculate_audience_buzz(self, performer_id: UUID) -> float:
        """
        Calculate Audience Buzz.

        Weighted score from community votes on public reviews.
        Recent engagement is weighted higher (last 30 days).

        Formula:
            buzz = (recent_votes × 1.5 + older_votes × 1.0) / max_possible_votes × 100
        """
        now = datetime.now(UTC)
        recency_cutoff = now - timedelta(days=BUZZ_RECENCY_WINDOW_DAYS)

        # Get public ratings with engagement
        ratings_stmt = select(PerformerRating).where(
            and_(
                PerformerRating.performer_id == performer_id,
                PerformerRating.is_public == True,  # noqa: E712
            )
        )
        ratings_result = await self._session.execute(ratings_stmt)
        ratings = ratings_result.scalars().all()

        if not ratings:
            return DEFAULT_ACI_SCORE

        # Calculate weighted engagement
        total_weighted_engagement = 0.0
        for rating in ratings:
            engagement = rating.audience_buzz_votes + (rating.helpful_votes * 0.5)

            # Apply recency weighting
            if rating.rated_at and rating.rated_at >= recency_cutoff:
                engagement *= 1.5  # Recent ratings count 50% more

            total_weighted_engagement += engagement

        # Normalize to 0-100 scale
        # Use a logarithmic scale to prevent outliers from dominating
        if total_weighted_engagement <= 0:
            return DEFAULT_ACI_SCORE

        import math

        # Log scale: 100 votes = 50 points, 1000 votes = 75 points, 10000 votes = 100 points
        normalized = min(100, 25 * math.log10(total_weighted_engagement + 1))

        return max(DEFAULT_ACI_SCORE, normalized)

    async def _calculate_motion_score(self, performer_id: UUID) -> float:
        """
        Calculate MotionScore.

        Average quality_metrics.motion_score across all available takes.
        """
        # Get takes with quality metrics
        takes_stmt = select(PerformanceTake).where(
            and_(
                PerformanceTake.performer_id == performer_id,
                PerformanceTake.status == "available",
                PerformanceTake.quality_metrics.isnot(None),
            )
        )
        takes_result = await self._session.execute(takes_stmt)
        takes = takes_result.scalars().all()

        if len(takes) < MIN_TAKES_FOR_MOTION_SCORE:
            return DEFAULT_ACI_SCORE

        # Extract motion scores
        motion_scores = []
        for take in takes:
            if take.quality_metrics and "motion_score" in take.quality_metrics:
                motion_scores.append(take.quality_metrics["motion_score"])

        if not motion_scores:
            return DEFAULT_ACI_SCORE

        return sum(motion_scores) / len(motion_scores)

    async def recalculate_all_performers(self) -> dict[str, int]:
        """
        Recalculate ACI for all active performers.

        Returns:
            Dictionary with counts of updated performers and errors
        """
        stmt = select(Performer).where(Performer.is_active == True)  # noqa: E712
        result = await self._session.execute(stmt)
        performers = result.scalars().all()

        updated = 0
        errors = 0

        for performer in performers:
            try:
                await self.calculate_aci(performer.id, update_performer=True)
                updated += 1
            except Exception as e:
                logger.error(f"Failed to recalculate ACI for performer {performer.id}: {e}")
                errors += 1

        await self._session.commit()

        logger.info(f"Recalculated ACI for {updated} performers ({errors} errors)")
        return {"updated": updated, "errors": errors}

    async def get_leaderboard(
        self,
        limit: int = 100,
        min_bookings: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get ACI leaderboard.

        Args:
            limit: Maximum number of performers to return
            min_bookings: Minimum bookings required to appear

        Returns:
            List of performer dictionaries sorted by ACI
        """
        stmt = (
            select(Performer)
            .where(
                and_(
                    Performer.is_active == True,  # noqa: E712
                    Performer.total_bookings >= min_bookings,
                )
            )
            .order_by(Performer.aci_score.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        performers = result.scalars().all()

        return [
            {
                "rank": i + 1,
                "performer_id": str(performer.id),
                "stage_name": performer.stage_name,
                "aci_score": performer.aci_score,
                "performer_type": performer.performer_type.value,
                "total_bookings": performer.total_bookings,
                "specialties": performer.specialties or [],
            }
            for i, performer in enumerate(performers)
        ]


# Singleton instance management
_aci_service_instance: ACIService | None = None


def get_aci_service(session: AsyncSession) -> ACIService:
    """Get or create ACI service instance."""
    return ACIService(session)
