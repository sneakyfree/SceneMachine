"""Performer Payout Service.

Handles revenue calculations and payout processing for ActCore performers.
Implements the graduated revenue split structure.

Revenue Tiers:
    $0 - $999:         50% performer / 50% platform
    $1,000 - $9,999:   60% performer / 40% platform
    $10,000 - $99,999: 70% performer / 30% platform
    $100,000 - $999,999: 80% performer / 20% platform
    $1,000,000 - $9,999,999: 90% performer / 10% platform
    $10,000,000+:      99% performer / 1% platform
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models import (
    Performer,
    Booking,
    BookingStatus,
    PaymentStatus,
)

logger = logging.getLogger(__name__)


# Revenue tier configuration
# (min_earnings, max_earnings, performer_percentage)
REVENUE_TIERS = [
    (Decimal("0"), Decimal("999.99"), Decimal("50.0")),
    (Decimal("1000"), Decimal("9999.99"), Decimal("60.0")),
    (Decimal("10000"), Decimal("99999.99"), Decimal("70.0")),
    (Decimal("100000"), Decimal("999999.99"), Decimal("80.0")),
    (Decimal("1000000"), Decimal("9999999.99"), Decimal("90.0")),
    (Decimal("10000000"), Decimal("999999999999"), Decimal("99.0")),
]


@dataclass
class PayoutCalculation:
    """Result of a payout calculation."""

    booking_price_usd: Decimal
    performer_split_percent: Decimal
    platform_fee_percent: Decimal
    performer_payout_usd: Decimal
    platform_fee_usd: Decimal
    current_tier: int
    lifetime_earnings_usd: Decimal
    earnings_to_next_tier: Optional[Decimal]
    next_tier_split_percent: Optional[Decimal]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "booking_price_usd": float(self.booking_price_usd),
            "performer_split_percent": float(self.performer_split_percent),
            "platform_fee_percent": float(self.platform_fee_percent),
            "performer_payout_usd": float(self.performer_payout_usd),
            "platform_fee_usd": float(self.platform_fee_usd),
            "current_tier": self.current_tier,
            "lifetime_earnings_usd": float(self.lifetime_earnings_usd),
            "earnings_to_next_tier": (
                float(self.earnings_to_next_tier)
                if self.earnings_to_next_tier is not None
                else None
            ),
            "next_tier_split_percent": (
                float(self.next_tier_split_percent)
                if self.next_tier_split_percent is not None
                else None
            ),
        }


@dataclass
class PayoutSummary:
    """Summary of performer payouts."""

    performer_id: UUID
    stage_name: str
    current_tier: int
    performer_split_percent: Decimal
    lifetime_earnings_usd: Decimal
    pending_payout_usd: Decimal
    total_bookings: int
    completed_bookings: int
    earnings_to_next_tier: Optional[Decimal]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "performer_id": str(self.performer_id),
            "stage_name": self.stage_name,
            "current_tier": self.current_tier,
            "performer_split_percent": float(self.performer_split_percent),
            "lifetime_earnings_usd": float(self.lifetime_earnings_usd),
            "pending_payout_usd": float(self.pending_payout_usd),
            "total_bookings": self.total_bookings,
            "completed_bookings": self.completed_bookings,
            "earnings_to_next_tier": (
                float(self.earnings_to_next_tier)
                if self.earnings_to_next_tier is not None
                else None
            ),
        }


class PerformerPayoutService:
    """
    Service for calculating and processing performer payouts.

    Implements the graduated revenue structure where performers
    earn a higher percentage as their lifetime earnings increase.
    """

    def __init__(self, session: AsyncSession):
        """Initialize service with database session."""
        self._session = session

    def get_tier_for_earnings(self, lifetime_earnings: Decimal) -> Tuple[int, Decimal]:
        """
        Get the revenue tier for given lifetime earnings.

        Args:
            lifetime_earnings: Total lifetime earnings in USD

        Returns:
            Tuple of (tier_number, performer_percentage)
            Tier 1 = lowest, Tier 6 = highest (99%)
        """
        for i, (min_earnings, max_earnings, performer_pct) in enumerate(REVENUE_TIERS):
            if min_earnings <= lifetime_earnings <= max_earnings:
                return (i + 1, performer_pct)

        # Default to highest tier if above all thresholds
        return (len(REVENUE_TIERS), REVENUE_TIERS[-1][2])

    def get_next_tier_info(
        self,
        lifetime_earnings: Decimal,
    ) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """
        Get information about the next revenue tier.

        Args:
            lifetime_earnings: Current lifetime earnings

        Returns:
            Tuple of (earnings_needed, next_tier_percentage)
            Returns (None, None) if already at highest tier
        """
        current_tier, _ = self.get_tier_for_earnings(lifetime_earnings)

        # Check if already at highest tier
        if current_tier >= len(REVENUE_TIERS):
            return (None, None)

        # Get next tier threshold
        next_tier_min, _, next_tier_pct = REVENUE_TIERS[current_tier]
        earnings_needed = next_tier_min - lifetime_earnings

        return (earnings_needed, next_tier_pct)

    def calculate_payout(
        self,
        booking_price_usd: float,
        lifetime_earnings_usd: float,
    ) -> PayoutCalculation:
        """
        Calculate the payout split for a booking.

        Args:
            booking_price_usd: Total booking price in USD
            lifetime_earnings_usd: Performer's lifetime earnings for tier calculation

        Returns:
            PayoutCalculation with full breakdown
        """
        booking_price = Decimal(str(booking_price_usd))
        lifetime_earnings = Decimal(str(lifetime_earnings_usd))

        # Get current tier and split
        current_tier, performer_pct = self.get_tier_for_earnings(lifetime_earnings)
        platform_pct = Decimal("100.0") - performer_pct

        # Calculate amounts
        performer_payout = booking_price * (performer_pct / Decimal("100"))
        platform_fee = booking_price * (platform_pct / Decimal("100"))

        # Get next tier info
        earnings_to_next, next_tier_pct = self.get_next_tier_info(lifetime_earnings)

        return PayoutCalculation(
            booking_price_usd=booking_price,
            performer_split_percent=performer_pct,
            platform_fee_percent=platform_pct,
            performer_payout_usd=performer_payout,
            platform_fee_usd=platform_fee,
            current_tier=current_tier,
            lifetime_earnings_usd=lifetime_earnings,
            earnings_to_next_tier=earnings_to_next,
            next_tier_split_percent=next_tier_pct,
        )

    async def get_performer_summary(
        self,
        performer_id: UUID,
    ) -> Optional[PayoutSummary]:
        """
        Get payout summary for a performer.

        Args:
            performer_id: The performer's UUID

        Returns:
            PayoutSummary or None if performer not found
        """
        # Get performer
        stmt = select(Performer).where(Performer.id == performer_id)
        result = await self._session.execute(stmt)
        performer = result.scalar_one_or_none()

        if not performer:
            return None

        # Get pending payout amount
        pending_stmt = select(func.sum(Booking.performer_payout_usd)).where(
            and_(
                Booking.performer_id == performer_id,
                Booking.status == BookingStatus.COMPLETED,
                Booking.payment_status == PaymentStatus.ESCROWED,
            )
        )
        pending_result = await self._session.execute(pending_stmt)
        pending_payout = pending_result.scalar() or Decimal("0")

        # Get tier info
        lifetime = Decimal(str(performer.lifetime_earnings_usd))
        current_tier, performer_pct = self.get_tier_for_earnings(lifetime)
        earnings_to_next, _ = self.get_next_tier_info(lifetime)

        return PayoutSummary(
            performer_id=performer.id,
            stage_name=performer.stage_name,
            current_tier=current_tier,
            performer_split_percent=performer_pct,
            lifetime_earnings_usd=lifetime,
            pending_payout_usd=Decimal(str(pending_payout)),
            total_bookings=performer.total_bookings,
            completed_bookings=performer.completed_bookings,
            earnings_to_next_tier=earnings_to_next,
        )

    async def process_booking_payout(
        self,
        booking_id: UUID,
    ) -> Optional[PayoutCalculation]:
        """
        Process payout for a completed booking.

        Updates booking with calculated amounts and performer earnings.

        Args:
            booking_id: The booking's UUID

        Returns:
            PayoutCalculation or None if booking not found/not ready
        """
        # Get booking
        booking_stmt = select(Booking).where(Booking.id == booking_id)
        booking_result = await self._session.execute(booking_stmt)
        booking = booking_result.scalar_one_or_none()

        if not booking:
            logger.error(f"Booking {booking_id} not found")
            return None

        if booking.status != BookingStatus.APPROVED:
            logger.warning(f"Booking {booking_id} not in APPROVED status")
            return None

        # Get performer
        performer_stmt = select(Performer).where(Performer.id == booking.performer_id)
        performer_result = await self._session.execute(performer_stmt)
        performer = performer_result.scalar_one_or_none()

        if not performer:
            logger.error(f"Performer {booking.performer_id} not found")
            return None

        # Calculate payout
        calculation = self.calculate_payout(
            booking.price_usd,
            performer.lifetime_earnings_usd,
        )

        # Update booking
        booking.platform_fee_usd = float(calculation.platform_fee_usd)
        booking.performer_payout_usd = float(calculation.performer_payout_usd)
        booking.status = BookingStatus.COMPLETED
        booking.completed_at = datetime.now(timezone.utc)

        # Update performer earnings
        performer.total_earnings_usd += float(calculation.performer_payout_usd)
        performer.lifetime_earnings_usd += float(calculation.performer_payout_usd)
        performer.completed_bookings += 1

        # Update performer's revenue tier
        performer.update_revenue_tier()

        await self._session.commit()

        logger.info(
            f"Processed payout for booking {booking_id}: "
            f"${calculation.performer_payout_usd:.2f} to performer, "
            f"${calculation.platform_fee_usd:.2f} platform fee"
        )

        return calculation

    async def release_payment(
        self,
        booking_id: UUID,
        stripe_transfer_id: Optional[str] = None,
    ) -> bool:
        """
        Release escrowed payment to performer.

        Args:
            booking_id: The booking's UUID
            stripe_transfer_id: Optional Stripe transfer ID

        Returns:
            True if successful, False otherwise
        """
        # Get booking
        booking_stmt = select(Booking).where(Booking.id == booking_id)
        booking_result = await self._session.execute(booking_stmt)
        booking = booking_result.scalar_one_or_none()

        if not booking:
            logger.error(f"Booking {booking_id} not found")
            return False

        if booking.payment_status != PaymentStatus.ESCROWED:
            logger.warning(f"Booking {booking_id} payment not escrowed")
            return False

        # Update payment status
        booking.payment_status = PaymentStatus.RELEASED
        booking.released_at = datetime.now(timezone.utc)

        await self._session.commit()

        logger.info(f"Released payment for booking {booking_id}")
        return True

    async def get_tier_progress(
        self,
        performer_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get detailed tier progress information for a performer.

        Args:
            performer_id: The performer's UUID

        Returns:
            Dictionary with tier progress information
        """
        # Get performer
        stmt = select(Performer).where(Performer.id == performer_id)
        result = await self._session.execute(stmt)
        performer = result.scalar_one_or_none()

        if not performer:
            return {"error": "Performer not found"}

        lifetime = Decimal(str(performer.lifetime_earnings_usd))
        current_tier, current_pct = self.get_tier_for_earnings(lifetime)

        # Build tier information
        tiers_info = []
        for i, (min_e, max_e, pct) in enumerate(REVENUE_TIERS):
            tier_num = i + 1
            is_current = tier_num == current_tier
            is_unlocked = lifetime >= min_e

            tier_info = {
                "tier": tier_num,
                "min_earnings": float(min_e),
                "max_earnings": float(max_e) if max_e < Decimal("999999999") else None,
                "performer_split_percent": float(pct),
                "platform_fee_percent": float(Decimal("100") - pct),
                "is_current": is_current,
                "is_unlocked": is_unlocked,
            }

            # Add progress for next tier
            if tier_num == current_tier + 1:
                tier_info["earnings_needed"] = float(min_e - lifetime)

            tiers_info.append(tier_info)

        # Calculate progress within current tier
        current_tier_min = REVENUE_TIERS[current_tier - 1][0]
        current_tier_max = REVENUE_TIERS[current_tier - 1][1]
        tier_range = current_tier_max - current_tier_min
        progress_in_tier = (lifetime - current_tier_min) / tier_range if tier_range > 0 else 1.0

        return {
            "performer_id": str(performer_id),
            "stage_name": performer.stage_name,
            "lifetime_earnings_usd": float(lifetime),
            "current_tier": current_tier,
            "current_split_percent": float(current_pct),
            "progress_in_tier": float(min(progress_in_tier, 1.0)),
            "tiers": tiers_info,
        }


# Singleton instance management
def get_payout_service(session: AsyncSession) -> PerformerPayoutService:
    """Get payout service instance."""
    return PerformerPayoutService(session)


# Backwards compatibility alias
PerformerPayoutsService = PerformerPayoutService
