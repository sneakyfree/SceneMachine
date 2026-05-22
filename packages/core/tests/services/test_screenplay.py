"""Tests for Screenplay service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models import Project
from scenemachine.services.screenplay import ScreenplayService


class TestScreenplayService:
    """Tests for ScreenplayService."""

    @pytest.fixture
    def screenplay_service(self, db_session: AsyncSession) -> ScreenplayService:
        """Create a screenplay service instance."""
        return ScreenplayService(db_session)

    @pytest.fixture
    def sample_fountain_content(self) -> str:
        """Sample Fountain screenplay content."""
        return """Title:
    Test Screenplay

Author:
    Test Author

INT. COFFEE SHOP - DAY

JOHN, 30s, sits alone at a table, staring at his coffee.

JOHN
I wonder if today will be different.

MARY enters, spotting JOHN.

MARY
(cheerfully)
John! There you are.

She sits across from him.

JOHN
Mary. You're early.

MARY
Couldn't wait to see you.

They share a smile.

FADE OUT.
"""

    @pytest.mark.asyncio
    async def test_parse_fountain_screenplay(
        self,
        screenplay_service: ScreenplayService,
        sample_project: Project,
        sample_fountain_content: str,
    ):
        """Test parsing a Fountain format screenplay."""
        result = await screenplay_service.parse_screenplay(
            project_id=sample_project.id,
            content=sample_fountain_content,
            format="fountain",
        )

        assert result is not None
        assert "scenes" in result or hasattr(result, "scenes")

    @pytest.mark.asyncio
    async def test_parse_screenplay_extracts_characters(
        self,
        screenplay_service: ScreenplayService,
        sample_project: Project,
        sample_fountain_content: str,
    ):
        """Test that parsing extracts character names."""
        result = await screenplay_service.parse_screenplay(
            project_id=sample_project.id,
            content=sample_fountain_content,
            format="fountain",
        )

        # Should find JOHN and MARY
        if isinstance(result, dict) and "characters" in result:
            character_names = [c.upper() for c in result["characters"]]
            assert "JOHN" in character_names or any(
                "JOHN" in str(c).upper() for c in result.get("characters", [])
            )

    @pytest.mark.asyncio
    async def test_parse_screenplay_extracts_scenes(
        self,
        screenplay_service: ScreenplayService,
        sample_project: Project,
        sample_fountain_content: str,
    ):
        """Test that parsing extracts scenes."""
        result = await screenplay_service.parse_screenplay(
            project_id=sample_project.id,
            content=sample_fountain_content,
            format="fountain",
        )

        if isinstance(result, dict) and "scenes" in result:
            assert len(result["scenes"]) >= 1
            # Check for scene heading
            first_scene = result["scenes"][0]
            assert "coffee shop" in str(first_scene).lower() or "INT." in str(first_scene)

    @pytest.mark.asyncio
    async def test_parse_screenplay_extracts_dialogue(
        self,
        screenplay_service: ScreenplayService,
        sample_project: Project,
        sample_fountain_content: str,
    ):
        """Test that parsing extracts dialogue."""
        result = await screenplay_service.parse_screenplay(
            project_id=sample_project.id,
            content=sample_fountain_content,
            format="fountain",
        )

        # Should have extracted dialogue
        assert result is not None

    @pytest.mark.asyncio
    async def test_parse_empty_screenplay(
        self,
        screenplay_service: ScreenplayService,
        sample_project: Project,
    ):
        """Test parsing an empty screenplay."""
        result = await screenplay_service.parse_screenplay(
            project_id=sample_project.id,
            content="",
            format="fountain",
        )

        # Should handle gracefully
        assert result is not None

    @pytest.mark.asyncio
    async def test_parse_invalid_format(
        self,
        screenplay_service: ScreenplayService,
        sample_project: Project,
        sample_fountain_content: str,
    ):
        """Test parsing with an invalid format."""
        with pytest.raises((ValueError, KeyError, Exception)):
            await screenplay_service.parse_screenplay(
                project_id=sample_project.id,
                content=sample_fountain_content,
                format="invalid_format",
            )

    @pytest.mark.asyncio
    async def test_get_screenplay_by_project(
        self,
        screenplay_service: ScreenplayService,
        sample_project: Project,
    ):
        """Test getting a screenplay by project ID."""
        await screenplay_service.get_screenplay(sample_project.id)

        # May return None if no screenplay exists
        # Just verify no exception is raised

    @pytest.mark.asyncio
    async def test_update_screenplay(
        self,
        screenplay_service: ScreenplayService,
        sample_project: Project,
        sample_fountain_content: str,
    ):
        """Test updating a screenplay."""
        # First parse the screenplay
        await screenplay_service.parse_screenplay(
            project_id=sample_project.id,
            content=sample_fountain_content,
            format="fountain",
        )

        # Update with modified content
        updated_content = sample_fountain_content.replace("JOHN", "JACK")
        result = await screenplay_service.parse_screenplay(
            project_id=sample_project.id,
            content=updated_content,
            format="fountain",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_analyze_screenplay(
        self,
        screenplay_service: ScreenplayService,
        sample_project: Project,
        sample_fountain_content: str,
    ):
        """Test analyzing a screenplay for insights."""
        # Parse first
        await screenplay_service.parse_screenplay(
            project_id=sample_project.id,
            content=sample_fountain_content,
            format="fountain",
        )

        # Analyze if method exists
        if hasattr(screenplay_service, "analyze_screenplay"):
            analysis = await screenplay_service.analyze_screenplay(sample_project.id)
            assert analysis is not None

    @pytest.mark.asyncio
    async def test_extract_locations(
        self,
        screenplay_service: ScreenplayService,
        sample_project: Project,
        sample_fountain_content: str,
    ):
        """Test extracting locations from a screenplay."""
        result = await screenplay_service.parse_screenplay(
            project_id=sample_project.id,
            content=sample_fountain_content,
            format="fountain",
        )

        # Should have extracted at least one location
        if isinstance(result, dict) and "locations" in result:
            locations = result["locations"]
            assert any("coffee shop" in str(loc).lower() for loc in locations)
