"""
Tests for performer seed data.

Validates that the sample performer data is correct and complete.
"""

from scenemachine.models.performer import (
    PerformerAvailability,
    PerformerType,
    PerformerVerification,
)
from scenemachine.seeds.performers import (
    SAMPLE_PERFORMERS,
    _calculate_earnings,
    _generate_motion_capabilities,
    _generate_pricing,
    _get_availability,
)


class TestSamplePerformersData:
    """Tests for the sample performers data structure."""

    def test_has_50_performers(self):
        """Should have exactly 50 sample performers."""
        assert len(SAMPLE_PERFORMERS) == 50

    def test_all_performers_have_required_fields(self):
        """All performers should have required fields."""
        required_fields = [
            "stage_name",
            "bio",
            "specialties",
            "aci_score",
            "performer_type",
            "verification_status",
            "total_bookings",
            "completed_bookings",
            "profile_image",
        ]

        for performer in SAMPLE_PERFORMERS:
            for field in required_fields:
                assert field in performer, (
                    f"Missing field '{field}' in performer: {performer.get('stage_name')}"
                )

    def test_stage_names_are_unique(self):
        """All stage names should be unique."""
        stage_names = [p["stage_name"] for p in SAMPLE_PERFORMERS]
        assert len(stage_names) == len(set(stage_names))

    def test_aci_scores_in_valid_range(self):
        """ACI scores should be between 0 and 100."""
        for performer in SAMPLE_PERFORMERS:
            assert 0 <= performer["aci_score"] <= 100, (
                f"Invalid ACI score for {performer['stage_name']}: {performer['aci_score']}"
            )

    def test_completed_bookings_not_exceed_total(self):
        """Completed bookings should not exceed total bookings."""
        for performer in SAMPLE_PERFORMERS:
            assert performer["completed_bookings"] <= performer["total_bookings"], (
                f"Completed bookings exceed total for {performer['stage_name']}"
            )

    def test_performer_types_are_valid(self):
        """All performer types should be valid."""
        for performer in SAMPLE_PERFORMERS:
            assert performer["performer_type"] in [PerformerType.HUMAN, PerformerType.SYNTHETIC]

    def test_verification_statuses_are_valid(self):
        """All verification statuses should be valid."""
        valid_statuses = [
            PerformerVerification.UNVERIFIED,
            PerformerVerification.PENDING,
            PerformerVerification.VERIFIED,
            PerformerVerification.ELITE,
        ]
        for performer in SAMPLE_PERFORMERS:
            assert performer["verification_status"] in valid_statuses

    def test_specialties_are_lists(self):
        """Specialties should be non-empty lists."""
        for performer in SAMPLE_PERFORMERS:
            assert isinstance(performer["specialties"], list)
            assert len(performer["specialties"]) > 0

    def test_bios_are_non_empty(self):
        """Bios should be non-empty strings."""
        for performer in SAMPLE_PERFORMERS:
            assert isinstance(performer["bio"], str)
            assert len(performer["bio"]) > 10  # At least a short description

    def test_has_diverse_aci_distribution(self):
        """Should have performers across different ACI tiers."""
        aci_scores = [p["aci_score"] for p in SAMPLE_PERFORMERS]

        # Check for performers in different tiers
        high_tier = [s for s in aci_scores if s >= 90]
        mid_high_tier = [s for s in aci_scores if 80 <= s < 90]
        mid_tier = [s for s in aci_scores if 70 <= s < 80]
        lower_tier = [s for s in aci_scores if s < 70]

        assert len(high_tier) >= 3, "Should have at least 3 high-tier performers"
        assert len(mid_high_tier) >= 5, "Should have at least 5 mid-high tier performers"
        assert len(mid_tier) >= 5, "Should have at least 5 mid tier performers"
        assert len(lower_tier) >= 5, "Should have at least 5 lower tier performers"

    def test_has_synthetic_performers(self):
        """Should have some synthetic performers."""
        synthetic = [p for p in SAMPLE_PERFORMERS if p["performer_type"] == PerformerType.SYNTHETIC]
        assert len(synthetic) >= 3, "Should have at least 3 synthetic performers"

    def test_has_elite_performers(self):
        """Should have some elite verified performers."""
        elite = [
            p for p in SAMPLE_PERFORMERS if p["verification_status"] == PerformerVerification.ELITE
        ]
        assert len(elite) >= 3, "Should have at least 3 elite performers"

    def test_profile_images_have_valid_urls(self):
        """Profile images should have valid URL format."""
        for performer in SAMPLE_PERFORMERS:
            url = performer["profile_image"]
            assert url.startswith("https://"), f"Invalid URL for {performer['stage_name']}: {url}"


class TestPricingGeneration:
    """Tests for pricing generation function."""

    def test_generates_all_pricing_tiers(self):
        """Should generate all pricing tiers."""
        pricing = _generate_pricing(80.0, PerformerType.HUMAN)

        assert "blink" in pricing
        assert "deep" in pricing
        assert "epic_per_minute" in pricing
        assert "auction_minimum" in pricing

    def test_higher_aci_means_higher_prices(self):
        """Higher ACI should result in higher prices."""
        low_aci_pricing = _generate_pricing(60.0, PerformerType.HUMAN)
        high_aci_pricing = _generate_pricing(95.0, PerformerType.HUMAN)

        assert high_aci_pricing["blink"] > low_aci_pricing["blink"]
        assert high_aci_pricing["deep"] > low_aci_pricing["deep"]

    def test_synthetic_performers_are_cheaper(self):
        """Synthetic performers should have lower prices."""
        human_pricing = _generate_pricing(80.0, PerformerType.HUMAN)
        synthetic_pricing = _generate_pricing(80.0, PerformerType.SYNTHETIC)

        assert synthetic_pricing["blink"] < human_pricing["blink"]
        assert synthetic_pricing["deep"] < human_pricing["deep"]


class TestMotionCapabilities:
    """Tests for motion capabilities generation."""

    def test_generates_required_capabilities(self):
        """Should generate all required capability fields."""
        caps = _generate_motion_capabilities(PerformerType.HUMAN, 80.0)

        assert "supports_liveportrait" in caps
        assert "supported_resolutions" in caps
        assert "face_tracking_quality" in caps
        assert "hand_tracking" in caps

    def test_synthetic_has_more_resolutions(self):
        """Synthetic performers should support more resolutions."""
        human_caps = _generate_motion_capabilities(PerformerType.HUMAN, 75.0)
        synthetic_caps = _generate_motion_capabilities(PerformerType.SYNTHETIC, 75.0)

        assert "4k" in synthetic_caps["supported_resolutions"]
        # Human at 75 ACI shouldn't have 4k
        assert "4k" not in human_caps["supported_resolutions"]

    def test_higher_aci_better_quality(self):
        """Higher ACI should result in better quality tracking."""
        low_caps = _generate_motion_capabilities(PerformerType.HUMAN, 60.0)
        high_caps = _generate_motion_capabilities(PerformerType.HUMAN, 90.0)

        assert high_caps["face_tracking_quality"] == "high"
        assert low_caps["face_tracking_quality"] == "standard"


class TestEarningsCalculation:
    """Tests for earnings calculation function."""

    def test_calculates_total_and_lifetime(self):
        """Should return both total and lifetime earnings."""
        total, lifetime = _calculate_earnings(100, 80.0)

        assert total > 0
        assert lifetime > 0
        assert lifetime > total  # Lifetime should include historical

    def test_more_bookings_means_more_earnings(self):
        """More bookings should result in more earnings."""
        low_total, _ = _calculate_earnings(50, 80.0)
        high_total, _ = _calculate_earnings(500, 80.0)

        assert high_total > low_total

    def test_higher_aci_means_more_per_booking(self):
        """Higher ACI should mean more earnings per booking."""
        low_aci_total, _ = _calculate_earnings(100, 60.0)
        high_aci_total, _ = _calculate_earnings(100, 95.0)

        assert high_aci_total > low_aci_total


class TestAvailabilityStatus:
    """Tests for availability status determination."""

    def test_returns_valid_status(self):
        """Should return a valid PerformerAvailability."""
        status = _get_availability(100)
        assert status in [
            PerformerAvailability.AVAILABLE,
            PerformerAvailability.BUSY,
            PerformerAvailability.OFFLINE,
            PerformerAvailability.ON_LEAVE,
        ]

    def test_active_performers_mostly_available(self):
        """Performers with many bookings should usually be available."""
        # Run multiple times due to randomness
        statuses = [_get_availability(500) for _ in range(100)]
        available_count = sum(1 for s in statuses if s == PerformerAvailability.AVAILABLE)

        # Should be available at least 50% of the time
        assert available_count >= 50

    def test_inactive_performers_often_offline(self):
        """Performers with few bookings should often be offline."""
        statuses = [_get_availability(5) for _ in range(100)]
        offline_count = sum(1 for s in statuses if s == PerformerAvailability.OFFLINE)

        # Should be offline at least 30% of the time
        assert offline_count >= 30
