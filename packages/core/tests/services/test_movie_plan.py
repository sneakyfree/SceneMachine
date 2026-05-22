"""Tests for MoviePlanService."""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models import (
    Character,
    Project,
    Scene,
    Screenplay,
)
from scenemachine.models.scene import SceneType, TimeOfDay
from scenemachine.services.movie_plan import (
    MoviePlan,
    MoviePlanService,
)


@pytest_asyncio.fixture
async def screenplay_with_content(db_session: AsyncSession, sample_project: Project) -> Screenplay:
    """Create a screenplay with parsed content for testing."""
    screenplay = Screenplay(
        project_id=sample_project.id,
        original_filename="test_screenplay.fountain",
        content_hash="abc123",
        raw_content="""
        Title: Test Movie
        Author: Test Author

        FADE IN:

        INT. LIVING ROOM - DAY

        JOHN enters the room. He looks around nervously.

        JOHN
        (whispering)
        I can't believe we made it.

        SARAH walks in behind him, laughing.

        SARAH
        Relax! Everything is fine.

        They embrace.

        EXT. CITY STREET - NIGHT

        John runs through the dark street. An EXPLOSION echoes behind him.

        FADE OUT.
        """,
        is_parsed=True,
        parsed_content={
            "title_page": {"title": "Test Movie", "author": "Test Author"},
            "elements": [
                {"type": "scene_heading", "text": "INT. LIVING ROOM - DAY"},
                {"type": "action", "text": "JOHN enters the room. He looks around nervously."},
                {"type": "character", "text": "JOHN"},
                {"type": "dialogue", "text": "I can't believe we made it."},
                {"type": "action", "text": "SARAH walks in behind him, laughing."},
                {"type": "character", "text": "SARAH"},
                {"type": "dialogue", "text": "Relax! Everything is fine."},
                {"type": "action", "text": "They embrace."},
                {"type": "scene_heading", "text": "EXT. CITY STREET - NIGHT"},
                {
                    "type": "action",
                    "text": "John runs through the dark street. An EXPLOSION echoes behind him.",
                },
            ],
            "metadata": {"scene_count": 2, "character_count": 2},
        },
    )
    db_session.add(screenplay)
    await db_session.commit()
    await db_session.refresh(screenplay)
    return screenplay


@pytest_asyncio.fixture
async def sample_characters(db_session: AsyncSession, sample_project: Project) -> list[Character]:
    """Create sample characters for testing."""
    characters = [
        Character(
            project_id=sample_project.id,
            name="JOHN",
            dialogue_count=5,
            scene_count=3,
            first_appearance="1",
        ),
        Character(
            project_id=sample_project.id,
            name="SARAH",
            dialogue_count=3,
            scene_count=2,
            first_appearance="1",
        ),
    ]
    for char in characters:
        db_session.add(char)
    await db_session.commit()
    for char in characters:
        await db_session.refresh(char)
    return characters


@pytest_asyncio.fixture
async def sample_scenes(db_session: AsyncSession, sample_project: Project) -> list[Scene]:
    """Create sample scenes for testing."""
    scenes = [
        Scene(
            project_id=sample_project.id,
            scene_number="1",
            sequence_number=1,
            scene_type=SceneType.INTERIOR,
            location="LIVING ROOM",
            time_of_day=TimeOfDay.DAY,
            raw_content="INT. LIVING ROOM - DAY\n\nJOHN enters...",
            action_lines=["JOHN enters the room", "SARAH walks in", "They embrace"],
        ),
        Scene(
            project_id=sample_project.id,
            scene_number="2",
            sequence_number=2,
            scene_type=SceneType.EXTERIOR,
            location="CITY STREET",
            time_of_day=TimeOfDay.NIGHT,
            raw_content="EXT. CITY STREET - NIGHT\n\nJohn runs...",
            action_lines=["John runs through the dark street", "An EXPLOSION echoes"],
        ),
    ]
    for scene in scenes:
        db_session.add(scene)
    await db_session.commit()
    for scene in scenes:
        await db_session.refresh(scene)
    return scenes


@pytest_asyncio.fixture
async def movie_plan_service(db_session: AsyncSession) -> MoviePlanService:
    """Create MoviePlanService instance."""
    return MoviePlanService(db_session)


class TestMoviePlanService:
    """Test suite for MoviePlanService."""

    async def test_generate_movie_plan_success(
        self,
        movie_plan_service: MoviePlanService,
        screenplay_with_content: Screenplay,
        sample_characters: list[Character],
        sample_scenes: list[Scene],
    ):
        """Test successful movie plan generation."""
        plan = await movie_plan_service.generate_movie_plan(screenplay_with_content.id)

        assert plan is not None
        assert isinstance(plan, MoviePlan)
        assert plan.title == "Test Movie"
        assert plan.screenplay_id == str(screenplay_with_content.id)
        assert plan.generated_at is not None
        assert len(plan.scenes) == 2
        assert len(plan.characters) == 2

    async def test_generate_movie_plan_not_found(
        self,
        movie_plan_service: MoviePlanService,
    ):
        """Test movie plan generation with non-existent screenplay."""
        with pytest.raises(ValueError, match="not found"):
            await movie_plan_service.generate_movie_plan(uuid4())

    async def test_generate_movie_plan_not_parsed(
        self,
        movie_plan_service: MoviePlanService,
        db_session: AsyncSession,
        sample_project: Project,
    ):
        """Test movie plan generation with unparsed screenplay."""
        screenplay = Screenplay(
            project_id=sample_project.id,
            original_filename="unparsed.fountain",
            content_hash="xyz789",
            raw_content="Some content",
            is_parsed=False,
        )
        db_session.add(screenplay)
        await db_session.commit()

        with pytest.raises(ValueError, match="must be parsed"):
            await movie_plan_service.generate_movie_plan(screenplay.id)

    async def test_get_movie_plan_returns_existing(
        self,
        movie_plan_service: MoviePlanService,
        screenplay_with_content: Screenplay,
        sample_characters: list[Character],
        sample_scenes: list[Scene],
    ):
        """Test getting an existing movie plan."""
        # Generate first
        await movie_plan_service.generate_movie_plan(screenplay_with_content.id)

        # Then get
        plan = await movie_plan_service.get_movie_plan(screenplay_with_content.id)
        assert plan is not None
        assert plan.title == "Test Movie"

    async def test_get_movie_plan_not_found(
        self,
        movie_plan_service: MoviePlanService,
    ):
        """Test getting movie plan for non-existent screenplay."""
        result = await movie_plan_service.get_movie_plan(uuid4())
        assert result is None

    async def test_approve_movie_plan(
        self,
        movie_plan_service: MoviePlanService,
        screenplay_with_content: Screenplay,
        sample_characters: list[Character],
        sample_scenes: list[Scene],
        db_session: AsyncSession,
    ):
        """Test approving a movie plan."""
        # Generate plan first
        await movie_plan_service.generate_movie_plan(screenplay_with_content.id)

        # Approve it
        result = await movie_plan_service.approve_movie_plan(screenplay_with_content.id)
        assert result is True

        # Verify screenplay is marked as approved
        await db_session.refresh(screenplay_with_content)
        assert screenplay_with_content.movie_plan_approved is True

    async def test_approve_movie_plan_no_plan(
        self,
        movie_plan_service: MoviePlanService,
        db_session: AsyncSession,
        sample_project: Project,
    ):
        """Test approving when no plan exists."""
        screenplay = Screenplay(
            project_id=sample_project.id,
            original_filename="no_plan.fountain",
            content_hash="abc",
            raw_content="content",
            is_parsed=True,
            parsed_content={"elements": []},
        )
        db_session.add(screenplay)
        await db_session.commit()

        with pytest.raises(ValueError, match="No movie plan"):
            await movie_plan_service.approve_movie_plan(screenplay.id)

    async def test_regenerate_movie_plan(
        self,
        movie_plan_service: MoviePlanService,
        screenplay_with_content: Screenplay,
        sample_characters: list[Character],
        sample_scenes: list[Scene],
    ):
        """Test regenerating an existing movie plan."""
        # Generate first
        plan1 = await movie_plan_service.generate_movie_plan(screenplay_with_content.id)
        original_generated_at = plan1.generated_at

        # Regenerate
        plan2 = await movie_plan_service.generate_movie_plan(
            screenplay_with_content.id, regenerate=True
        )

        assert plan2.generated_at != original_generated_at


class TestGenreAnalysis:
    """Test suite for genre and tone analysis."""

    async def test_analyze_genre_horror(self, movie_plan_service: MoviePlanService):
        """Test horror genre detection."""
        elements = [
            {"type": "action", "text": "Blood drips from the ceiling. A scream echoes."},
            {"type": "action", "text": "The monster emerges from the dark."},
        ]
        genre, tone = movie_plan_service._analyze_genre_tone(elements)
        assert genre == "horror"
        assert "dark" in tone.lower() or "suspense" in tone.lower()

    async def test_analyze_genre_comedy(self, movie_plan_service: MoviePlanService):
        """Test comedy genre detection."""
        elements = [
            {"type": "action", "text": "Everyone laughs at the joke."},
            {"type": "action", "text": "He grins and chuckles."},
        ]
        genre, tone = movie_plan_service._analyze_genre_tone(elements)
        assert genre == "comedy"
        assert "humor" in tone.lower() or "light" in tone.lower()

    async def test_analyze_genre_action(self, movie_plan_service: MoviePlanService):
        """Test action genre detection."""
        elements = [
            {"type": "action", "text": "The car crashes through the explosion."},
            {"type": "action", "text": "He throws a punch as bullets fly."},
        ]
        genre, tone = movie_plan_service._analyze_genre_tone(elements)
        assert genre == "action"
        assert "intense" in tone.lower() or "fast" in tone.lower()

    async def test_analyze_genre_default_drama(self, movie_plan_service: MoviePlanService):
        """Test default genre when no keywords found."""
        elements = [
            {"type": "action", "text": "She walks into the room."},
            {"type": "action", "text": "They sit in silence."},
        ]
        genre, tone = movie_plan_service._analyze_genre_tone(elements)
        assert genre == "drama"


class TestThemeExtraction:
    """Test suite for theme extraction."""

    async def test_extract_themes_love(self, movie_plan_service: MoviePlanService):
        """Test love theme extraction."""
        elements = [
            {"type": "dialogue", "text": "I love you with all my heart."},
        ]
        themes = movie_plan_service._extract_themes(elements)
        assert "love" in themes

    async def test_extract_themes_family(self, movie_plan_service: MoviePlanService):
        """Test family theme extraction."""
        elements = [
            {"type": "action", "text": "The family gathers around the table."},
            {"type": "dialogue", "text": "Father, I need your help."},
        ]
        themes = movie_plan_service._extract_themes(elements)
        assert "family" in themes

    async def test_extract_themes_multiple(self, movie_plan_service: MoviePlanService):
        """Test multiple theme extraction."""
        elements = [
            {"type": "dialogue", "text": "I will survive this betrayal."},
            {"type": "action", "text": "She seeks justice for her family."},
        ]
        themes = movie_plan_service._extract_themes(elements)
        assert len(themes) >= 2

    async def test_extract_themes_default(self, movie_plan_service: MoviePlanService):
        """Test default theme when no keywords found."""
        elements = [{"type": "action", "text": "A plain scene."}]
        themes = movie_plan_service._extract_themes(elements)
        assert "personal journey" in themes


class TestVisualStyleAnalysis:
    """Test suite for visual style analysis."""

    async def test_visual_style_action(self, movie_plan_service: MoviePlanService):
        """Test visual style for action genre."""
        visual_style = movie_plan_service._analyze_visual_style([], "action", "intense")
        assert visual_style["aspect_ratio"] == "2.39:1"
        assert visual_style["frame_rate"] == 24

    async def test_visual_style_drama(self, movie_plan_service: MoviePlanService):
        """Test visual style for drama genre."""
        visual_style = movie_plan_service._analyze_visual_style([], "drama", "emotional")
        assert visual_style["aspect_ratio"] == "1.85:1"

    async def test_color_palette_horror(self, movie_plan_service: MoviePlanService):
        """Test color palette for horror."""
        palette = movie_plan_service._generate_color_palette("horror", "dark")
        assert len(palette) >= 4
        assert any("#" in color for color in palette)

    async def test_color_palette_romance(self, movie_plan_service: MoviePlanService):
        """Test color palette for romance."""
        palette = movie_plan_service._generate_color_palette("romance", "warm")
        assert len(palette) >= 4


class TestActStructure:
    """Test suite for act structure determination."""

    async def test_act_structure_empty(self, movie_plan_service: MoviePlanService):
        """Test act structure with no scenes."""
        structure = movie_plan_service._determine_act_structure([])
        assert structure == {"act_1": [], "act_2": [], "act_3": []}

    async def test_act_structure_single_scene(
        self,
        movie_plan_service: MoviePlanService,
        db_session: AsyncSession,
        sample_project: Project,
    ):
        """Test act structure with single scene."""
        scene = Scene(
            project_id=sample_project.id,
            scene_number="1",
            sequence_number=1,
            scene_type=SceneType.INTERIOR,
            location="ROOM",
            time_of_day=TimeOfDay.DAY,
        )
        db_session.add(scene)
        await db_session.commit()

        structure = movie_plan_service._determine_act_structure([scene])
        # With one scene, act divisions are minimal
        assert "act_1" in structure
        assert "act_2" in structure
        assert "act_3" in structure


class TestLocationExtraction:
    """Test suite for location extraction."""

    async def test_extract_locations(
        self,
        movie_plan_service: MoviePlanService,
        sample_scenes: list[Scene],
    ):
        """Test location extraction from scenes."""
        locations = movie_plan_service._extract_locations(sample_scenes)
        assert len(locations) == 2
        location_names = [loc["name"] for loc in locations]
        assert "LIVING ROOM" in location_names
        assert "CITY STREET" in location_names

    async def test_extract_locations_with_times(
        self,
        movie_plan_service: MoviePlanService,
        sample_scenes: list[Scene],
    ):
        """Test location extraction includes times of day."""
        locations = movie_plan_service._extract_locations(sample_scenes)
        for loc in locations:
            assert "times_of_day" in loc
            assert isinstance(loc["times_of_day"], list)


class TestPropExtraction:
    """Test suite for prop extraction."""

    async def test_extract_props(self, movie_plan_service: MoviePlanService):
        """Test prop extraction from elements."""
        elements = [
            {"type": "action", "text": "He picks up the gun and checks his phone."},
            {"type": "action", "text": "She opens the door with a key."},
        ]
        props = movie_plan_service._extract_props(elements)
        assert "gun" in props
        assert "phone" in props
        assert "door" in props
        assert "key" in props

    async def test_extract_props_empty(self, movie_plan_service: MoviePlanService):
        """Test prop extraction with no props."""
        elements = [{"type": "action", "text": "They stood in silence."}]
        props = movie_plan_service._extract_props(elements)
        assert isinstance(props, list)


class TestSpecialEffects:
    """Test suite for special effects identification."""

    async def test_identify_sfx_explosion(self, movie_plan_service: MoviePlanService):
        """Test explosion SFX identification."""
        elements = [{"type": "action", "text": "The building explodes in a massive explosion."}]
        sfx = movie_plan_service._identify_special_effects(elements)
        assert any("explosion" in note.lower() for note in sfx)

    async def test_identify_sfx_weather(self, movie_plan_service: MoviePlanService):
        """Test weather effects identification."""
        elements = [{"type": "action", "text": "Rain pours down as snow begins to fall."}]
        sfx = movie_plan_service._identify_special_effects(elements)
        assert any("rain" in note.lower() for note in sfx)
        assert any("snow" in note.lower() for note in sfx)

    async def test_identify_sfx_none(self, movie_plan_service: MoviePlanService):
        """Test no SFX identification."""
        elements = [{"type": "action", "text": "She walks across the room."}]
        sfx = movie_plan_service._identify_special_effects(elements)
        assert len(sfx) == 0


class TestWarnings:
    """Test suite for warning generation."""

    async def test_warnings_many_locations(
        self,
        movie_plan_service: MoviePlanService,
        db_session: AsyncSession,
        sample_project: Project,
        screenplay_with_content: Screenplay,
    ):
        """Test warning for many locations."""
        # Create many scenes with different locations
        scenes = []
        for i in range(25):
            scene = Scene(
                project_id=sample_project.id,
                scene_number=str(i),
                sequence_number=i,
                scene_type=SceneType.INTERIOR,
                location=f"LOCATION_{i}",
                time_of_day=TimeOfDay.DAY,
            )
            db_session.add(scene)
            scenes.append(scene)
        await db_session.commit()

        warnings = movie_plan_service._generate_warnings(screenplay_with_content, [], scenes)
        assert any("location" in w.lower() for w in warnings)

    async def test_warnings_large_cast(
        self,
        movie_plan_service: MoviePlanService,
        db_session: AsyncSession,
        sample_project: Project,
        screenplay_with_content: Screenplay,
    ):
        """Test warning for large cast."""
        characters = []
        for i in range(35):
            char = Character(
                project_id=sample_project.id,
                name=f"CHARACTER_{i}",
                dialogue_count=1,
                scene_count=1,
            )
            db_session.add(char)
            characters.append(char)
        await db_session.commit()

        warnings = movie_plan_service._generate_warnings(screenplay_with_content, characters, [])
        assert any("cast" in w.lower() for w in warnings)


class TestCharacterAnalysis:
    """Test suite for character analysis."""

    async def test_identify_protagonist(
        self,
        movie_plan_service: MoviePlanService,
        sample_characters: list[Character],
        sample_scenes: list[Scene],
    ):
        """Test protagonist identification."""
        protagonist = movie_plan_service._identify_protagonist(sample_characters, sample_scenes)
        # JOHN has more dialogue (5) vs SARAH (3)
        assert protagonist == "JOHN"

    async def test_identify_antagonist(
        self,
        movie_plan_service: MoviePlanService,
        sample_characters: list[Character],
        sample_scenes: list[Scene],
    ):
        """Test antagonist identification."""
        protagonist = "JOHN"
        antagonist = movie_plan_service._identify_antagonist(
            sample_characters, sample_scenes, protagonist
        )
        # Second most prominent character
        assert antagonist == "SARAH"

    async def test_analyze_character(
        self,
        movie_plan_service: MoviePlanService,
        sample_characters: list[Character],
        sample_scenes: list[Scene],
    ):
        """Test character analysis."""
        analysis = movie_plan_service._analyze_character(sample_characters[0], sample_scenes, [])
        assert analysis["name"] == "JOHN"
        assert analysis["dialogue_count"] == 5
        assert "estimated_screen_time_percent" in analysis


class TestLoglineGeneration:
    """Test suite for logline generation."""

    async def test_generate_logline_with_protagonist(
        self,
        movie_plan_service: MoviePlanService,
        sample_characters: list[Character],
        sample_scenes: list[Scene],
    ):
        """Test logline generation with protagonist."""
        logline = movie_plan_service._generate_logline(
            "Test Movie", sample_characters, sample_scenes
        )
        assert "john" in logline.lower()
        assert str(len(sample_scenes)) in logline

    async def test_generate_logline_no_characters(
        self,
        movie_plan_service: MoviePlanService,
        sample_scenes: list[Scene],
    ):
        """Test logline generation without characters."""
        logline = movie_plan_service._generate_logline("Test Movie", [], sample_scenes)
        assert "journey" in logline.lower()


class TestDataConversion:
    """Test suite for data conversion methods."""

    async def test_movie_plan_to_dict(self, movie_plan_service: MoviePlanService):
        """Test MoviePlan to dict conversion."""
        plan = MoviePlan(
            screenplay_id="test-id",
            generated_at="2024-01-01T00:00:00",
            ai_model="test",
            title="Test",
            logline="Test logline",
            genre="drama",
            tone="dramatic",
            themes=["love"],
            estimated_runtime_minutes=90,
        )
        result = movie_plan_service._movie_plan_to_dict(plan)
        assert result["title"] == "Test"
        assert result["genre"] == "drama"

    async def test_dict_to_movie_plan(self, movie_plan_service: MoviePlanService):
        """Test dict to MoviePlan conversion."""
        data = {
            "screenplay_id": "test-id",
            "generated_at": "2024-01-01T00:00:00",
            "ai_model": "test",
            "title": "Test",
            "logline": "Test logline",
            "genre": "drama",
            "tone": "dramatic",
            "themes": ["love"],
            "estimated_runtime_minutes": 90,
        }
        plan = movie_plan_service._dict_to_movie_plan(data)
        assert isinstance(plan, MoviePlan)
        assert plan.title == "Test"
        assert plan.genre == "drama"
