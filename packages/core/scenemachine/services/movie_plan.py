"""Movie plan generation service.

Generates comprehensive movie plans from parsed screenplays using AI analysis.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.config import get_settings
from scenemachine.models import Character, Project, Scene, Screenplay
from scenemachine.models.project import ProjectState

logger = logging.getLogger(__name__)


@dataclass
class CharacterAnalysis:
    """AI analysis of a character."""

    name: str
    description: str
    arc: str
    relationships: list[dict[str, str]]
    visual_suggestions: dict[str, Any]
    key_scenes: list[str]
    dialogue_style: str
    estimated_age_range: str
    gender_presentation: str


@dataclass
class SceneAnalysis:
    """AI analysis of a scene."""

    scene_number: str
    location: str
    time_of_day: str
    mood: str
    pacing: str
    visual_style: str
    key_actions: list[str]
    characters_present: list[str]
    dialogue_summary: str
    estimated_duration_seconds: int
    suggested_shot_count: int
    lighting_notes: str
    sound_design_notes: str


@dataclass
class MoviePlan:
    """Complete movie plan for a screenplay."""

    # Metadata
    screenplay_id: str
    generated_at: str
    ai_model: str

    # Overall Analysis
    title: str
    logline: str
    genre: str
    tone: str
    themes: list[str]
    estimated_runtime_minutes: int

    # Visual Style
    visual_style: dict[str, Any] = field(default_factory=dict)
    color_palette: list[str] = field(default_factory=list)
    cinematography_notes: str = ""

    # Characters
    characters: list[dict[str, Any]] = field(default_factory=list)
    protagonist: str | None = None
    antagonist: str | None = None

    # Scenes
    scenes: list[dict[str, Any]] = field(default_factory=list)
    act_structure: dict[str, list[str]] = field(default_factory=dict)

    # Production Notes
    location_requirements: list[dict[str, Any]] = field(default_factory=list)
    prop_requirements: list[str] = field(default_factory=list)
    special_effects_notes: list[str] = field(default_factory=list)

    # Generation Statistics
    generation_notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class MoviePlanService:
    """Service for generating and managing movie plans.

    Uses AI to analyze parsed screenplays and generate comprehensive
    production-ready movie plans.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize movie plan service.

        Args:
            session: Database session
        """
        self.session = session
        self.settings = get_settings()

    async def generate_movie_plan(
        self,
        screenplay_id: UUID,
        regenerate: bool = False,
    ) -> MoviePlan:
        """Generate a movie plan from a parsed screenplay.

        Args:
            screenplay_id: Screenplay UUID
            regenerate: If True, regenerate even if plan exists

        Returns:
            Generated MoviePlan

        Raises:
            ValueError: If screenplay not found or not parsed
        """
        # Get screenplay
        screenplay = await self._get_screenplay(screenplay_id)
        if not screenplay:
            raise ValueError(f"Screenplay {screenplay_id} not found")

        if not screenplay.is_parsed or not screenplay.parsed_content:
            raise ValueError("Screenplay must be parsed before generating movie plan")

        # Check if plan already exists
        if screenplay.movie_plan and not regenerate:
            return self._dict_to_movie_plan(screenplay.movie_plan)

        logger.info(f"Generating movie plan for screenplay {screenplay_id}")

        # Get characters and scenes from database
        characters = await self._get_characters(screenplay.project_id)
        scenes = await self._get_scenes(screenplay.project_id)

        # Generate the plan
        movie_plan = await self._generate_plan(screenplay, characters, scenes)

        # Store the plan
        screenplay.movie_plan = self._movie_plan_to_dict(movie_plan)
        await self.session.commit()

        # Update project state
        project = await self._get_project(screenplay.project_id)
        if project and project.state == ProjectState.SCREENPLAY_PARSED:
            project.state = ProjectState.PLAN_GENERATED
            await self.session.commit()

        logger.info(f"Movie plan generated for screenplay {screenplay_id}")
        return movie_plan

    async def _generate_plan(
        self,
        screenplay: Screenplay,
        characters: list[Character],
        scenes: list[Scene],
    ) -> MoviePlan:
        """Generate movie plan using AI analysis.

        This method orchestrates the AI analysis of the screenplay.
        In production, this would call an LLM API (e.g., Claude).
        """
        parsed = screenplay.parsed_content or {}
        title_page = parsed.get("title_page", {})
        elements = parsed.get("elements", [])
        metadata = parsed.get("metadata", {})

        # Extract title
        title = title_page.get("title", screenplay.original_filename.rsplit(".", 1)[0])

        # Analyze genre and tone from content
        genre, tone = self._analyze_genre_tone(elements)

        # Analyze themes
        themes = self._extract_themes(elements)

        # Generate logline
        logline = self._generate_logline(title, characters, scenes)

        # Estimate runtime (approx 1 min per page, ~1 page per scene on average)
        estimated_runtime = max(len(scenes) * 2, metadata.get("scene_count", 0) * 2)

        # Analyze visual style
        visual_style = self._analyze_visual_style(scenes, genre, tone)

        # Generate color palette
        color_palette = self._generate_color_palette(genre, tone)

        # Analyze characters
        character_analyses = [
            self._analyze_character(char, scenes, elements) for char in characters
        ]

        # Identify protagonist and antagonist
        protagonist = self._identify_protagonist(characters, scenes)
        antagonist = self._identify_antagonist(characters, scenes, protagonist)

        # Analyze scenes
        scene_analyses = [
            self._analyze_scene(scene, characters, elements) for scene in scenes
        ]

        # Determine act structure
        act_structure = self._determine_act_structure(scenes)

        # Extract location requirements
        location_requirements = self._extract_locations(scenes)

        # Extract prop requirements
        prop_requirements = self._extract_props(elements)

        # Identify special effects needs
        sfx_notes = self._identify_special_effects(elements)

        return MoviePlan(
            screenplay_id=str(screenplay.id),
            generated_at=datetime.utcnow().isoformat(),
            ai_model="rule-based-v1",  # Will be updated when AI is integrated
            title=title,
            logline=logline,
            genre=genre,
            tone=tone,
            themes=themes,
            estimated_runtime_minutes=estimated_runtime,
            visual_style=visual_style,
            color_palette=color_palette,
            cinematography_notes=self._generate_cinematography_notes(genre, tone),
            characters=character_analyses,
            protagonist=protagonist,
            antagonist=antagonist,
            scenes=scene_analyses,
            act_structure=act_structure,
            location_requirements=location_requirements,
            prop_requirements=prop_requirements,
            special_effects_notes=sfx_notes,
            generation_notes=["Generated using rule-based analysis"],
            warnings=self._generate_warnings(screenplay, characters, scenes),
        )

    def _analyze_genre_tone(self, elements: list[dict]) -> tuple[str, str]:
        """Analyze genre and tone from screenplay elements."""
        # Keywords for genre detection
        genre_keywords = {
            "horror": ["blood", "scream", "dark", "terror", "monster", "nightmare"],
            "comedy": ["laugh", "joke", "funny", "hilarious", "grin", "chuckle"],
            "drama": ["tears", "emotional", "struggle", "conflict", "heartbreak"],
            "action": ["explosion", "fight", "chase", "gun", "crash", "punch"],
            "thriller": ["suspense", "tension", "danger", "mysterious", "secret"],
            "romance": ["love", "kiss", "heart", "romantic", "passion", "embrace"],
            "sci-fi": ["space", "alien", "future", "robot", "technology", "spacecraft"],
        }

        # Count keyword occurrences
        text = " ".join(e.get("text", "").lower() for e in elements)
        genre_scores: dict[str, int] = {}

        for genre, keywords in genre_keywords.items():
            score = sum(text.count(kw) for kw in keywords)
            if score > 0:
                genre_scores[genre] = score

        # Default genre
        genre = max(genre_scores, key=genre_scores.get) if genre_scores else "drama"

        # Tone based on genre
        tone_map = {
            "horror": "dark and suspenseful",
            "comedy": "light and humorous",
            "drama": "emotional and grounded",
            "action": "fast-paced and intense",
            "thriller": "tense and mysterious",
            "romance": "warm and intimate",
            "sci-fi": "imaginative and speculative",
        }

        tone = tone_map.get(genre, "balanced and engaging")

        return genre, tone

    def _extract_themes(self, elements: list[dict]) -> list[str]:
        """Extract thematic elements from the screenplay."""
        theme_keywords = {
            "redemption": ["forgive", "second chance", "redemption", "atone"],
            "love": ["love", "heart", "together", "romance"],
            "family": ["family", "father", "mother", "child", "home"],
            "identity": ["who am i", "discover", "true self", "belong"],
            "power": ["power", "control", "authority", "rule"],
            "survival": ["survive", "death", "alive", "escape"],
            "justice": ["justice", "right", "fair", "deserve"],
            "betrayal": ["betray", "trust", "deceive", "lie"],
        }

        text = " ".join(e.get("text", "").lower() for e in elements)
        themes = []

        for theme, keywords in theme_keywords.items():
            if any(kw in text for kw in keywords):
                themes.append(theme)

        return themes[:5] if themes else ["personal journey"]

    def _generate_logline(
        self, title: str, characters: list[Character], scenes: list[Scene]
    ) -> str:
        """Generate a logline for the screenplay."""
        # Find protagonist (character with most dialogue)
        protagonist = max(characters, key=lambda c: c.dialogue_count) if characters else None

        # Count scene types
        ext_count = sum(1 for s in scenes if "EXT" in str(s.scene_type.value).upper())
        int_count = len(scenes) - ext_count

        if protagonist:
            return (
                f"A {protagonist.name.lower()} must navigate "
                f"{'challenging external environments' if ext_count > int_count else 'intimate interior spaces'} "
                f"across {len(scenes)} pivotal scenes to face their ultimate challenge."
            )

        return f"An epic journey across {len(scenes)} scenes unfolds in this compelling story."

    def _analyze_visual_style(
        self, scenes: list[Scene], genre: str, tone: str
    ) -> dict[str, Any]:
        """Analyze and suggest visual style."""
        return {
            "overall_look": self._get_visual_look(genre),
            "lighting_style": self._get_lighting_style(genre, tone),
            "camera_movement": self._get_camera_style(genre),
            "aspect_ratio": "2.39:1" if genre in ["action", "sci-fi"] else "1.85:1",
            "frame_rate": 24,
        }

    def _get_visual_look(self, genre: str) -> str:
        """Get visual look recommendation based on genre."""
        looks = {
            "horror": "high contrast, desaturated with deep shadows",
            "comedy": "bright, saturated, and evenly lit",
            "drama": "naturalistic with motivated lighting",
            "action": "dynamic, high contrast, and bold",
            "thriller": "moody with strategic shadows and highlights",
            "romance": "soft, warm, with golden hour aesthetics",
            "sci-fi": "sleek, blue-tinted with practical lighting accents",
        }
        return looks.get(genre, "balanced and naturalistic")

    def _get_lighting_style(self, genre: str, tone: str) -> str:
        """Get lighting style recommendation."""
        if "dark" in tone.lower():
            return "low-key lighting with strong shadows"
        elif "light" in tone.lower() or "warm" in tone.lower():
            return "high-key lighting with soft fill"
        return "motivated naturalistic lighting"

    def _get_camera_style(self, genre: str) -> str:
        """Get camera movement style recommendation."""
        styles = {
            "horror": "slow creeping movements, sudden reveals",
            "comedy": "stable, wide shots for physical comedy",
            "drama": "intimate handheld, deliberate dollies",
            "action": "dynamic tracking, quick cuts",
            "thriller": "tense slow pushes, rack focuses",
            "romance": "smooth gliding movements, shallow DOF",
            "sci-fi": "grand scale movements, elaborate cranes",
        }
        return styles.get(genre, "varied based on scene requirements")

    def _generate_color_palette(self, genre: str, tone: str) -> list[str]:
        """Generate suggested color palette."""
        palettes = {
            "horror": ["#1a1a2e", "#16213e", "#0f3460", "#e94560"],
            "comedy": ["#fff3e0", "#ffe0b2", "#ffcc80", "#ffa726"],
            "drama": ["#3e2723", "#4e342e", "#5d4037", "#6d4c41"],
            "action": ["#263238", "#37474f", "#455a64", "#ff5722"],
            "thriller": ["#212121", "#424242", "#616161", "#00bcd4"],
            "romance": ["#fce4ec", "#f8bbd9", "#f48fb1", "#e91e63"],
            "sci-fi": ["#0d47a1", "#1565c0", "#1976d2", "#00e5ff"],
        }
        return palettes.get(genre, ["#424242", "#616161", "#757575", "#9e9e9e"])

    def _generate_cinematography_notes(self, genre: str, tone: str) -> str:
        """Generate cinematography notes."""
        return (
            f"For this {genre} with a {tone} tone, recommend using "
            f"{self._get_camera_style(genre)}. Pay attention to "
            f"establishing shots for new locations and maintain visual continuity "
            f"throughout the production."
        )

    def _analyze_character(
        self, character: Character, scenes: list[Scene], elements: list[dict]
    ) -> dict[str, Any]:
        """Analyze a character for the movie plan."""
        # Find scenes character appears in
        character_scenes = [
            s.scene_number for s in scenes
            if character.name in (s.raw_content or "")
        ]

        return {
            "name": character.name,
            "dialogue_count": character.dialogue_count,
            "scene_count": character.scene_count,
            "key_scenes": character_scenes[:5],
            "visual_suggestions": {
                "costume_notes": f"Consistent wardrobe for {character.name}",
                "distinguishing_features": "To be defined in Character Lab",
            },
            "estimated_screen_time_percent": round(
                (character.scene_count / max(len(scenes), 1)) * 100, 1
            ),
        }

    def _identify_protagonist(
        self, characters: list[Character], scenes: list[Scene]
    ) -> str | None:
        """Identify the likely protagonist."""
        if not characters:
            return None

        # Score characters by dialogue and scene presence
        scores = {}
        for char in characters:
            scores[char.name] = char.dialogue_count * 2 + char.scene_count * 3

        return max(scores, key=scores.get) if scores else None

    def _identify_antagonist(
        self,
        characters: list[Character],
        scenes: list[Scene],
        protagonist: str | None,
    ) -> str | None:
        """Identify a potential antagonist."""
        if not characters or not protagonist:
            return None

        # Second most prominent character could be antagonist
        sorted_chars = sorted(
            characters,
            key=lambda c: c.dialogue_count + c.scene_count,
            reverse=True,
        )

        for char in sorted_chars:
            if char.name != protagonist:
                return char.name

        return None

    def _analyze_scene(
        self, scene: Scene, characters: list[Character], elements: list[dict]
    ) -> dict[str, Any]:
        """Analyze a scene for the movie plan."""
        # Estimate duration based on action lines
        action_count = len(scene.action_lines) if scene.action_lines else 0
        estimated_duration = max(30, action_count * 10)  # Minimum 30 seconds

        return {
            "scene_number": scene.scene_number,
            "sequence_number": scene.sequence_number,
            "location": scene.location,
            "time_of_day": scene.time_of_day.value,
            "scene_type": scene.scene_type.value,
            "estimated_duration_seconds": estimated_duration,
            "suggested_shot_count": max(3, action_count),
            "mood": "To be analyzed",
            "lighting_notes": f"Natural {scene.time_of_day.value.lower()} lighting",
        }

    def _determine_act_structure(
        self, scenes: list[Scene]
    ) -> dict[str, list[str]]:
        """Determine three-act structure."""
        total = len(scenes)
        if total == 0:
            return {"act_1": [], "act_2": [], "act_3": []}

        # Traditional three-act structure: 25% / 50% / 25%
        act_1_end = total // 4
        act_3_start = total - (total // 4)

        return {
            "act_1": [s.scene_number for s in scenes[:act_1_end]],
            "act_2": [s.scene_number for s in scenes[act_1_end:act_3_start]],
            "act_3": [s.scene_number for s in scenes[act_3_start:]],
        }

    def _extract_locations(self, scenes: list[Scene]) -> list[dict[str, Any]]:
        """Extract unique location requirements."""
        locations: dict[str, dict[str, Any]] = {}

        for scene in scenes:
            loc = scene.location
            if loc not in locations:
                locations[loc] = {
                    "name": loc,
                    "scene_type": scene.scene_type.value,
                    "scene_count": 0,
                    "times_of_day": set(),
                }

            locations[loc]["scene_count"] += 1
            locations[loc]["times_of_day"].add(scene.time_of_day.value)

        # Convert sets to lists for JSON serialization
        return [
            {**loc, "times_of_day": list(loc["times_of_day"])}
            for loc in locations.values()
        ]

    def _extract_props(self, elements: list[dict]) -> list[str]:
        """Extract potential prop requirements from action lines."""
        # Common prop indicators
        prop_words = [
            "gun", "phone", "letter", "book", "knife", "car", "bag",
            "drink", "glass", "bottle", "key", "door", "window",
        ]

        props = set()
        for elem in elements:
            if elem.get("type") == "action":
                text = elem.get("text", "").lower()
                for prop in prop_words:
                    if prop in text:
                        props.add(prop)

        return sorted(props)

    def _identify_special_effects(self, elements: list[dict]) -> list[str]:
        """Identify potential special effects needs."""
        sfx_keywords = {
            "explosion": "Pyrotechnic or VFX explosion",
            "fire": "Fire effects",
            "rain": "Weather effects - rain",
            "snow": "Weather effects - snow",
            "blood": "Practical blood effects",
            "crash": "Vehicle crash effects",
            "transform": "Transformation VFX",
            "disappear": "Vanishing VFX",
            "fly": "Wire work or flight VFX",
        }

        notes = set()
        for elem in elements:
            text = elem.get("text", "").lower()
            for keyword, note in sfx_keywords.items():
                if keyword in text:
                    notes.add(note)

        return sorted(notes)

    def _generate_warnings(
        self,
        screenplay: Screenplay,
        characters: list[Character],
        scenes: list[Scene],
    ) -> list[str]:
        """Generate warnings about potential production challenges."""
        warnings = []

        # Too many locations
        locations = {s.location for s in scenes}
        if len(locations) > 20:
            warnings.append(f"High location count ({len(locations)}) may impact budget")

        # Too many characters
        if len(characters) > 30:
            warnings.append(f"Large cast ({len(characters)}) requires careful management")

        # Night scenes
        night_count = sum(1 for s in scenes if "NIGHT" in s.time_of_day.value.upper())
        if night_count > len(scenes) * 0.5:
            warnings.append("Many night scenes - consider lighting budget")

        return warnings

    async def approve_movie_plan(self, screenplay_id: UUID) -> bool:
        """Mark the movie plan as approved.

        Args:
            screenplay_id: Screenplay UUID

        Returns:
            True if approved successfully
        """
        screenplay = await self._get_screenplay(screenplay_id)
        if not screenplay:
            raise ValueError(f"Screenplay {screenplay_id} not found")

        if not screenplay.movie_plan:
            raise ValueError("No movie plan to approve")

        screenplay.movie_plan_approved = True
        await self.session.commit()

        # Update project state
        project = await self._get_project(screenplay.project_id)
        if project and project.state == ProjectState.PLAN_GENERATED:
            project.state = ProjectState.PLAN_APPROVED
            await self.session.commit()

        return True

    async def get_movie_plan(self, screenplay_id: UUID) -> MoviePlan | None:
        """Get the movie plan for a screenplay.

        Args:
            screenplay_id: Screenplay UUID

        Returns:
            MoviePlan if exists, None otherwise
        """
        screenplay = await self._get_screenplay(screenplay_id)
        if not screenplay or not screenplay.movie_plan:
            return None

        return self._dict_to_movie_plan(screenplay.movie_plan)

    def _movie_plan_to_dict(self, plan: MoviePlan) -> dict[str, Any]:
        """Convert MoviePlan to dictionary for storage."""
        return {
            "screenplay_id": plan.screenplay_id,
            "generated_at": plan.generated_at,
            "ai_model": plan.ai_model,
            "title": plan.title,
            "logline": plan.logline,
            "genre": plan.genre,
            "tone": plan.tone,
            "themes": plan.themes,
            "estimated_runtime_minutes": plan.estimated_runtime_minutes,
            "visual_style": plan.visual_style,
            "color_palette": plan.color_palette,
            "cinematography_notes": plan.cinematography_notes,
            "characters": plan.characters,
            "protagonist": plan.protagonist,
            "antagonist": plan.antagonist,
            "scenes": plan.scenes,
            "act_structure": plan.act_structure,
            "location_requirements": plan.location_requirements,
            "prop_requirements": plan.prop_requirements,
            "special_effects_notes": plan.special_effects_notes,
            "generation_notes": plan.generation_notes,
            "warnings": plan.warnings,
        }

    def _dict_to_movie_plan(self, data: dict[str, Any]) -> MoviePlan:
        """Convert dictionary to MoviePlan."""
        return MoviePlan(
            screenplay_id=data.get("screenplay_id", ""),
            generated_at=data.get("generated_at", ""),
            ai_model=data.get("ai_model", "unknown"),
            title=data.get("title", "Untitled"),
            logline=data.get("logline", ""),
            genre=data.get("genre", "drama"),
            tone=data.get("tone", ""),
            themes=data.get("themes", []),
            estimated_runtime_minutes=data.get("estimated_runtime_minutes", 0),
            visual_style=data.get("visual_style", {}),
            color_palette=data.get("color_palette", []),
            cinematography_notes=data.get("cinematography_notes", ""),
            characters=data.get("characters", []),
            protagonist=data.get("protagonist"),
            antagonist=data.get("antagonist"),
            scenes=data.get("scenes", []),
            act_structure=data.get("act_structure", {}),
            location_requirements=data.get("location_requirements", []),
            prop_requirements=data.get("prop_requirements", []),
            special_effects_notes=data.get("special_effects_notes", []),
            generation_notes=data.get("generation_notes", []),
            warnings=data.get("warnings", []),
        )

    async def _get_screenplay(self, screenplay_id: UUID) -> Screenplay | None:
        """Get screenplay by ID."""
        stmt = select(Screenplay).where(Screenplay.id == screenplay_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_project(self, project_id: UUID) -> Project | None:
        """Get project by ID."""
        stmt = select(Project).where(Project.id == project_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_characters(self, project_id: UUID) -> list[Character]:
        """Get all characters for a project."""
        stmt = select(Character).where(Character.project_id == project_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _get_scenes(self, project_id: UUID) -> list[Scene]:
        """Get all scenes for a project, ordered by sequence."""
        stmt = (
            select(Scene)
            .where(Scene.project_id == project_id)
            .order_by(Scene.sequence_number)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


async def get_movie_plan_service(session: AsyncSession) -> MoviePlanService:
    """Factory function for MoviePlanService."""
    return MoviePlanService(session)
