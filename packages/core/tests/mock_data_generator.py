#!/usr/bin/env python3
"""
SceneMachine Comprehensive Mock Data Generator.

Populates the database with realistic test data across all entities
in various states to enable thorough E2E testing.
"""

import asyncio
import hashlib
import json
import logging
import random
import string
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from scenemachine.models import (
    Project, ProjectState,
    Screenplay, ScreenplayFormat,
    Character, CharacterGender, CharacterLockState,
    Scene, SceneType, TimeOfDay, SceneState,
    Shot, ShotType, CameraMovement, ShotState,
    GenerationJob, JobStatus, JobProvider,
    Asset, AssetType, AssetStatus,
    ExportHistory, ExportFormat, ExportQuality, ExportStatus,
    UserSettings, LLMProvider, VideoProvider, ThemeMode,
    ProjectShare, ProjectComment, SharePermission, ShareStatus,
    TextOverlay, TextOverlayType, TextPosition, TextAnimation,
    AudioAsset, AudioAssetType,
)
from scenemachine.models.base import Base

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ============================================================================
# SAMPLE DATA CONSTANTS
# ============================================================================

MOVIE_TITLES = [
    "The Last Horizon", "Echoes of Tomorrow", "Crimson Dawn",
    "Whispers in the Dark", "The Forgotten Kingdom", "Starlight Express",
    "Beyond the Veil", "The Silent Observer", "Midnight's Edge",
    "The Phoenix Protocol", "Shadows of Yesterday", "The Crystal Key",
]

GENRES = ["Drama", "Thriller", "Sci-Fi", "Comedy", "Action", "Horror", "Romance", "Mystery"]

CHARACTER_FIRST_NAMES = [
    "James", "Sarah", "Michael", "Emily", "David", "Rachel", "John", "Maria",
    "Robert", "Jennifer", "Thomas", "Elizabeth", "William", "Amanda", "Richard", "Jessica",
    "Marcus", "Olivia", "Daniel", "Sophia", "Alexander", "Isabella", "Nathan", "Victoria",
]

CHARACTER_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Anderson", "Taylor", "Thomas", "Moore", "Jackson", "Martin",
    "Chen", "Patel", "Nakamura", "O'Brien", "Schmidt", "Kowalski", "Fernandez", "Kim",
]

LOCATIONS = [
    "APARTMENT", "OFFICE", "COFFEE SHOP", "HOSPITAL", "POLICE STATION",
    "BAR", "RESTAURANT", "WAREHOUSE", "BEACH", "FOREST", "MOUNTAIN TOP",
    "STREET", "SUBWAY STATION", "PARKING GARAGE", "ROOFTOP", "LIBRARY",
    "COURTROOM", "PRISON", "LABORATORY", "HOTEL LOBBY", "AIRPORT",
]

ACTION_LINES = [
    "enters the room slowly, looking around cautiously.",
    "sits down heavily, exhausted from the journey.",
    "picks up the phone and dials nervously.",
    "stares out the window, lost in thought.",
    "slams the door shut and locks it.",
    "pulls out a gun and aims at the target.",
    "embraces their loved one tightly.",
    "runs through the crowd desperately.",
    "examines the evidence carefully.",
    "types furiously on the computer.",
    "pours a drink and takes a long sip.",
    "checks their watch impatiently.",
]

DIALOGUE_LINES = [
    "We don't have much time. They're coming.",
    "I never thought I'd see you again.",
    "This changes everything, doesn't it?",
    "You have no idea what you're dealing with.",
    "Trust me, I know what I'm doing.",
    "There's something I need to tell you.",
    "We should have done this years ago.",
    "I'm not who you think I am.",
    "The truth is... I've been lying to you.",
    "We need to leave. Now.",
    "I can explain everything.",
    "This is our only chance.",
]

PERSONALITY_TRAITS = [
    "brave", "cautious", "intelligent", "hot-headed", "mysterious",
    "charming", "ruthless", "compassionate", "ambitious", "loyal",
    "cunning", "idealistic", "cynical", "playful", "stoic",
]

HAIR_COLORS = ["black", "brown", "blonde", "red", "gray", "white", "auburn"]
EYE_COLORS = ["brown", "blue", "green", "hazel", "gray"]
BUILDS = ["slim", "athletic", "average", "muscular", "heavy"]
HEIGHTS = ["short", "average", "tall"]

SOUND_EFFECT_CATEGORIES = [
    "Foley", "Ambience", "Impact", "Transition", "UI",
    "Nature", "Urban", "Mechanical", "Human", "Sci-Fi",
]

MUSIC_GENRES = [
    "Cinematic", "Electronic", "Classical", "Jazz", "Rock",
    "Hip-Hop", "Ambient", "Folk", "World", "Orchestral",
]

MUSIC_MOODS = [
    "Tense", "Happy", "Sad", "Epic", "Mysterious",
    "Romantic", "Action", "Peaceful", "Dark", "Hopeful",
]


# ============================================================================
# MOCK DATA GENERATOR CLASS
# ============================================================================

class MockDataGenerator:
    """Generates comprehensive mock data for SceneMachine."""

    def __init__(self, database_url: str):
        """Initialize with database connection."""
        # Convert sync URL to async
        if database_url.startswith("sqlite:///"):
            database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

        self.database_url = database_url
        self.is_sqlite = "sqlite" in database_url
        self.engine = create_async_engine(database_url, echo=False)
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        self.generated_data: Dict[str, List[Any]] = {
            "projects": [],
            "screenplays": [],
            "characters": [],
            "scenes": [],
            "shots": [],
            "generation_jobs": [],
            "assets": [],
            "export_history": [],
            "shares": [],
            "comments": [],
            "text_overlays": [],
            "audio_assets": [],
        }

    def _serialize_list(self, value: List) -> Any:
        """Serialize a list for database storage.

        For SQLite, converts to JSON string.
        For PostgreSQL, returns as-is for ARRAY type.
        """
        if self.is_sqlite and value is not None:
            return json.dumps([str(v) for v in value])
        return value if value is not None else []

    async def initialize_database(self):
        """Create database tables."""
        if self.is_sqlite:
            # Use SQLite compatibility layer
            from tests.sqlite_compat import create_all_tables_sqlite
            await create_all_tables_sqlite(self.engine, Base)
        else:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

    async def clear_all_data(self):
        """Clear all existing data from database."""
        async with self.session_factory() as session:
            # Delete in reverse dependency order
            tables = [
                ProjectComment, ProjectShare, TextOverlay, AudioAsset,
                ExportHistory, Asset, GenerationJob, Shot, Scene,
                Character, Screenplay, Project, UserSettings,
            ]
            for table in tables:
                await session.execute(delete(table))
            await session.commit()
        logger.info("All existing data cleared")

    def _random_datetime(
        self,
        start: datetime = None,
        end: datetime = None,
    ) -> datetime:
        """Generate random datetime within range."""
        if start is None:
            start = datetime.now(timezone.utc) - timedelta(days=90)
        if end is None:
            end = datetime.now(timezone.utc)
        delta = end - start
        random_seconds = random.randint(0, int(delta.total_seconds()))
        return start + timedelta(seconds=random_seconds)

    def _generate_file_hash(self) -> str:
        """Generate random file hash."""
        return hashlib.sha256(uuid4().bytes).hexdigest()

    # ========================================================================
    # PROJECT GENERATION
    # ========================================================================

    async def generate_projects(
        self,
        session: AsyncSession,
        count: int = 10,
    ) -> List[Project]:
        """Generate projects in various states."""
        projects = []
        states = list(ProjectState)

        for i in range(count):
            # Distribute across states, but ensure some complete workflows
            if i < 3:
                state = ProjectState.COMPLETE
            elif i < 5:
                state = ProjectState.GENERATING
            elif i < 7:
                state = ProjectState.CHARACTERS_LOCKED
            else:
                state = random.choice(states)

            title = MOVIE_TITLES[i % len(MOVIE_TITLES)]
            project = Project(
                id=uuid4(),
                name=f"{title} - Project {i + 1}",
                description=f"A {random.choice(GENRES).lower()} film about {random.choice(['love', 'revenge', 'redemption', 'survival', 'discovery'])}.",
                state=state,
                settings={
                    "genre": random.choice(GENRES),
                    "target_runtime_minutes": random.randint(90, 150),
                    "aspect_ratio": random.choice(["16:9", "2.35:1", "1.85:1"]),
                },
                created_at=self._random_datetime(),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(project)
            projects.append(project)

        await session.flush()
        self.generated_data["projects"] = projects
        logger.info(f"Generated {len(projects)} projects")
        return projects

    # ========================================================================
    # SCREENPLAY GENERATION
    # ========================================================================

    async def generate_screenplays(
        self,
        session: AsyncSession,
        projects: List[Project],
    ) -> List[Screenplay]:
        """Generate screenplays for projects."""
        screenplays = []

        for project in projects:
            if project.state == ProjectState.EMPTY:
                continue

            # Generate parsed content
            scenes_data = []
            for scene_num in range(random.randint(10, 25)):
                scene_type = random.choice(["INT", "EXT"])
                location = random.choice(LOCATIONS)
                time = random.choice(["DAY", "NIGHT", "DAWN", "DUSK"])

                characters_in_scene = random.sample(
                    CHARACTER_FIRST_NAMES,
                    k=random.randint(1, 4)
                )

                scenes_data.append({
                    "scene_number": f"{scene_num + 1}",
                    "heading": f"{scene_type}. {location} - {time}",
                    "type": scene_type,
                    "location": location,
                    "time_of_day": time,
                    "characters": characters_in_scene,
                    "action_lines": random.sample(ACTION_LINES, k=random.randint(2, 5)),
                    "dialogue": [
                        {"character": c, "line": random.choice(DIALOGUE_LINES)}
                        for c in characters_in_scene[:2]
                    ],
                })

            # Create movie plan for projects that have it
            movie_plan = None
            movie_plan_approved = False
            if project.state.value >= ProjectState.PLAN_GENERATED.value:
                movie_plan = {
                    "title": project.name,
                    "genres": random.sample(GENRES, k=2),
                    "themes": ["redemption", "love", "sacrifice"],
                    "visual_style": {
                        "lighting": random.choice(["high-key", "low-key", "natural"]),
                        "color_palette": random.choice(["warm", "cool", "desaturated"]),
                        "camera_style": random.choice(["handheld", "steady", "dynamic"]),
                    },
                    "act_structure": {
                        "act_1": {"scenes": list(range(1, 8)), "summary": "Setup"},
                        "act_2": {"scenes": list(range(8, 20)), "summary": "Conflict"},
                        "act_3": {"scenes": list(range(20, 26)), "summary": "Resolution"},
                    },
                    "estimated_runtime_minutes": random.randint(90, 130),
                }
                movie_plan_approved = project.state.value >= ProjectState.PLAN_APPROVED.value

            screenplay = Screenplay(
                id=uuid4(),
                project_id=project.id,
                original_filename=f"{project.name.replace(' ', '_')}.fountain",
                original_format=random.choice(list(ScreenplayFormat)),
                file_hash=self._generate_file_hash(),
                original_file_path=f"/data/screenplays/{project.id}/original.fountain",
                parsed_content={
                    "title": project.name,
                    "author": f"{random.choice(CHARACTER_FIRST_NAMES)} {random.choice(CHARACTER_LAST_NAMES)}",
                    "scenes": scenes_data,
                    "character_names": list(set(
                        c for s in scenes_data for c in s["characters"]
                    )),
                },
                movie_plan=movie_plan,
                movie_plan_approved=movie_plan_approved,
                is_parsed=True,
                created_at=project.created_at + timedelta(minutes=5),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(screenplay)
            screenplays.append(screenplay)

        await session.flush()
        self.generated_data["screenplays"] = screenplays
        logger.info(f"Generated {len(screenplays)} screenplays")
        return screenplays

    # ========================================================================
    # CHARACTER GENERATION
    # ========================================================================

    async def generate_characters(
        self,
        session: AsyncSession,
        projects: List[Project],
    ) -> List[Character]:
        """Generate characters for projects."""
        characters = []

        # Skip character generation for SQLite - Character model uses ARRAY types
        # that are not compatible with SQLite's type system
        if self.is_sqlite:
            logger.info("Skipping character generation for SQLite (ARRAY type incompatibility)")
            return characters

        for project in projects:
            if project.state.value < ProjectState.SCREENPLAY_PARSED.value:
                continue

            num_characters = random.randint(5, 15)
            used_names = set()

            for i in range(num_characters):
                # Generate unique name
                while True:
                    first = random.choice(CHARACTER_FIRST_NAMES)
                    last = random.choice(CHARACTER_LAST_NAMES)
                    name = f"{first} {last}"
                    if name not in used_names:
                        used_names.add(name)
                        break

                gender = random.choice(list(CharacterGender))

                # Determine lock state based on project state
                if project.state.value >= ProjectState.CHARACTERS_LOCKED.value:
                    lock_state = CharacterLockState.LOCKED
                elif project.state.value >= ProjectState.CHARACTERS_IN_PROGRESS.value:
                    lock_state = random.choice([
                        CharacterLockState.DRAFT,
                        CharacterLockState.REFERENCE_UPLOADED,
                        CharacterLockState.REVIEW,
                        CharacterLockState.LOCKED,
                    ])
                else:
                    lock_state = CharacterLockState.UNDEFINED

                character = Character(
                    id=uuid4(),
                    project_id=project.id,
                    name=name,
                    screenplay_name=first.upper(),
                    description=f"A {random.choice(['mysterious', 'charming', 'determined', 'complex'])} {random.choice(['protagonist', 'supporting character', 'antagonist'])}.",
                    age_range_min=random.randint(18, 40),
                    age_range_max=random.randint(40, 70),
                    gender=gender,
                    physical_description={
                        "hair_color": random.choice(HAIR_COLORS),
                        "hair_style": random.choice(["short", "long", "medium", "bald"]),
                        "eye_color": random.choice(EYE_COLORS),
                        "height": random.choice(HEIGHTS),
                        "build": random.choice(BUILDS),
                        "distinguishing_features": random.sample(
                            ["scar", "tattoo", "glasses", "beard", "freckles"],
                            k=random.randint(0, 2)
                        ),
                    },
                    personality_traits=self._serialize_list(random.sample(PERSONALITY_TRAITS, k=random.randint(2, 4))),
                    voice_description=f"A {random.choice(['deep', 'soft', 'gravelly', 'melodic'])} {random.choice(['voice', 'tone'])} with {random.choice(['authority', 'warmth', 'mystery'])}.",
                    voice_id=f"voice_{uuid4().hex[:8]}" if lock_state == CharacterLockState.LOCKED else None,
                    voice_provider="elevenlabs" if lock_state == CharacterLockState.LOCKED else None,
                    lock_state=lock_state,
                    scene_count=random.randint(3, 15),
                    dialogue_count=random.randint(10, 50),
                    is_protagonist=(i == 0),  # First character is protagonist
                    created_at=project.created_at + timedelta(minutes=10),
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(character)
                characters.append(character)

        await session.flush()
        self.generated_data["characters"] = characters
        logger.info(f"Generated {len(characters)} characters")
        return characters

    # ========================================================================
    # SCENE GENERATION
    # ========================================================================

    async def generate_scenes(
        self,
        session: AsyncSession,
        projects: List[Project],
        characters: List[Character],
    ) -> List[Scene]:
        """Generate scenes for projects."""
        scenes = []

        for project in projects:
            if project.state.value < ProjectState.SCREENPLAY_PARSED.value:
                continue

            project_chars = [c for c in characters if c.project_id == project.id]
            num_scenes = random.randint(15, 30)

            for seq in range(num_scenes):
                scene_type = random.choice(list(SceneType))
                location = random.choice(LOCATIONS)
                time_of_day = random.choice(list(TimeOfDay))

                # Determine state based on project state
                if project.state.value >= ProjectState.SCENES_APPROVED.value:
                    state = SceneState.APPROVED
                elif project.state.value >= ProjectState.SCENES_PLANNING.value:
                    state = random.choice([
                        SceneState.PARSED, SceneState.PLANNED,
                        SceneState.PLAN_APPROVED, SceneState.APPROVED,
                    ])
                else:
                    state = SceneState.PARSED

                # Scene characters
                scene_chars = random.sample(
                    project_chars,
                    k=min(random.randint(1, 4), len(project_chars))
                ) if project_chars else []

                action_lines_data = random.sample(ACTION_LINES, k=random.randint(2, 5))
                char_ids_data = [c.id for c in scene_chars]

                scene = Scene(
                    id=uuid4(),
                    project_id=project.id,
                    scene_number=f"{seq + 1}",
                    sequence_number=seq,
                    scene_type=scene_type,
                    location=location,
                    time_of_day=time_of_day,
                    raw_content=f"{scene_type.value}. {location} - {time_of_day.value}\n\n" +
                                "\n".join(random.sample(ACTION_LINES, k=3)),
                    action_lines=self._serialize_list(action_lines_data),
                    character_ids=self._serialize_list(char_ids_data),
                    analysis={
                        "mood": random.choice(["tense", "romantic", "action", "dramatic"]),
                        "pacing": random.choice(["fast", "medium", "slow"]),
                        "key_moments": random.sample(
                            ["revelation", "confrontation", "escape", "reunion"],
                            k=random.randint(1, 2)
                        ),
                    } if state.value >= SceneState.PLANNED.value else None,
                    shot_breakdown={
                        "shot_count": random.randint(5, 12),
                        "estimated_duration": random.randint(60, 180),
                    } if state.value >= SceneState.PLAN_APPROVED.value else None,
                    shot_breakdown_approved=state.value >= SceneState.PLAN_APPROVED.value,
                    estimated_duration_seconds=random.randint(60, 180),
                    state=state,
                    created_at=project.created_at + timedelta(minutes=15),
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(scene)
                scenes.append(scene)

        await session.flush()
        self.generated_data["scenes"] = scenes
        logger.info(f"Generated {len(scenes)} scenes")
        return scenes

    # ========================================================================
    # SHOT GENERATION
    # ========================================================================

    async def generate_shots(
        self,
        session: AsyncSession,
        scenes: List[Scene],
        characters: List[Character],
    ) -> Tuple[List[Shot], List[GenerationJob]]:
        """Generate shots and generation jobs for scenes."""
        shots = []
        jobs = []
        shot_types = list(ShotType)
        camera_movements = list(CameraMovement)

        for scene in scenes:
            if scene.state.value < SceneState.PLAN_APPROVED.value:
                continue

            scene_chars = [c for c in characters if c.id in (scene.character_ids or [])]
            num_shots = random.randint(4, 10)

            for seq in range(num_shots):
                shot_type = random.choice(shot_types)
                camera = random.choice(camera_movements)

                # Determine state based on scene state
                if scene.state == SceneState.APPROVED:
                    state = random.choice([
                        ShotState.APPROVED, ShotState.GENERATED,
                        ShotState.REVIEW, ShotState.APPROVED,
                    ])
                elif scene.state == SceneState.GENERATING:
                    state = random.choice([
                        ShotState.PLANNED, ShotState.QUEUED,
                        ShotState.GENERATING, ShotState.GENERATED,
                    ])
                else:
                    state = ShotState.PLANNED

                shot_char_ids = [c.id for c in random.sample(scene_chars, k=min(2, len(scene_chars)))] if scene_chars else []

                shot = Shot(
                    id=uuid4(),
                    scene_id=scene.id,
                    shot_number=f"{scene.scene_number}.{seq + 1}",
                    sequence_number=seq,
                    shot_type=shot_type,
                    camera_movement=camera,
                    description=f"{shot_type.value} shot of the scene with {camera.value} movement.",
                    dialogue=random.choice(DIALOGUE_LINES) if random.random() > 0.5 else None,
                    action=random.choice(ACTION_LINES),
                    character_ids=self._serialize_list(shot_char_ids),
                    generation_prompt=f"Cinematic {shot_type.value} shot, {camera.value} camera, film lighting" if state.value >= ShotState.QUEUED.value else None,
                    duration_seconds=random.uniform(2.0, 8.0),
                    state=state,
                    output_video_path=f"/data/outputs/{scene.project_id}/{shot.id}.mp4" if state in [ShotState.GENERATED, ShotState.APPROVED] else None,
                    output_thumbnail_path=f"/data/outputs/{scene.project_id}/{shot.id}_thumb.jpg" if state in [ShotState.GENERATED, ShotState.APPROVED] else None,
                    timeline_visible=True,
                    timeline_locked=state == ShotState.APPROVED,
                    timeline_order=seq,
                    transition_type=random.choice(["cut", "dissolve", "fade"]) if random.random() > 0.7 else None,
                    transition_duration=random.randint(200, 800) if random.random() > 0.7 else None,
                    created_at=scene.created_at + timedelta(minutes=5),
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(shot)
                shots.append(shot)

                # Generate jobs for shots that have been processed
                if state.value >= ShotState.QUEUED.value:
                    num_jobs = random.randint(1, 3) if state == ShotState.FAILED else 1
                    for job_num in range(num_jobs):
                        job_status = (
                            JobStatus.COMPLETED if state in [ShotState.GENERATED, ShotState.APPROVED, ShotState.REVIEW]
                            else JobStatus.RUNNING if state == ShotState.GENERATING
                            else JobStatus.FAILED if state == ShotState.FAILED
                            else JobStatus.PENDING
                        )

                        job = GenerationJob(
                            id=uuid4(),
                            shot_id=shot.id,
                            job_number=job_num + 1,
                            status=job_status,
                            provider=random.choice([JobProvider.REPLICATE, JobProvider.FAL, JobProvider.RUNPOD]),
                            provider_job_id=f"job_{uuid4().hex[:12]}" if job_status != JobStatus.PENDING else None,
                            model_id=random.choice(["svd", "animatediff", "cogvideox"]),
                            parameters={
                                "num_frames": 24,
                                "fps": 8,
                                "motion_bucket_id": random.randint(100, 200),
                            },
                            queued_at=self._random_datetime(),
                            started_at=self._random_datetime() if job_status.value >= JobStatus.RUNNING.value else None,
                            completed_at=self._random_datetime() if job_status in [JobStatus.COMPLETED, JobStatus.FAILED] else None,
                            progress_percent=100.0 if job_status == JobStatus.COMPLETED else random.uniform(0, 100) if job_status == JobStatus.RUNNING else 0.0,
                            output_path=shot.output_video_path if job_status == JobStatus.COMPLETED else None,
                            error_message="Generation failed: timeout" if job_status == JobStatus.FAILED else None,
                            cost_usd=random.uniform(0.02, 0.15) if job_status == JobStatus.COMPLETED else None,
                            created_at=shot.created_at + timedelta(minutes=1),
                            updated_at=datetime.now(timezone.utc),
                        )
                        session.add(job)
                        jobs.append(job)

        await session.flush()
        self.generated_data["shots"] = shots
        self.generated_data["generation_jobs"] = jobs
        logger.info(f"Generated {len(shots)} shots and {len(jobs)} generation jobs")
        return shots, jobs

    # ========================================================================
    # ASSET GENERATION
    # ========================================================================

    async def generate_assets(
        self,
        session: AsyncSession,
        characters: List[Character],
    ) -> List[Asset]:
        """Generate reference assets for characters."""
        assets = []

        for character in characters:
            if character.lock_state.value < CharacterLockState.REFERENCE_UPLOADED.value:
                continue

            num_refs = random.randint(1, 4)
            for i in range(num_refs):
                asset = Asset(
                    id=uuid4(),
                    character_id=character.id,
                    asset_type=AssetType.CHARACTER_REFERENCE,
                    status=AssetStatus.READY,
                    filename=f"reference_{i + 1}.jpg",
                    file_path=f"/data/assets/{character.project_id}/characters/{character.id}/ref_{i + 1}.jpg",
                    file_hash=self._generate_file_hash(),
                    file_size_bytes=random.randint(100000, 5000000),
                    mime_type="image/jpeg",
                    width=random.choice([512, 768, 1024]),
                    height=random.choice([512, 768, 1024]),
                    description=f"Reference image {i + 1} for {character.name}",
                    tags=["reference", "character", character.name.split()[0].lower()],
                    created_at=character.created_at + timedelta(minutes=5),
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(asset)
                assets.append(asset)

        await session.flush()
        self.generated_data["assets"] = assets
        logger.info(f"Generated {len(assets)} assets")
        return assets

    # ========================================================================
    # EXPORT HISTORY GENERATION
    # ========================================================================

    async def generate_export_history(
        self,
        session: AsyncSession,
        projects: List[Project],
    ) -> List[ExportHistory]:
        """Generate export history for completed projects."""
        exports = []

        for project in projects:
            if project.state.value < ProjectState.GENERATION_COMPLETE.value:
                continue

            num_exports = random.randint(1, 5)
            for i in range(num_exports):
                status = random.choice([
                    ExportStatus.COMPLETED, ExportStatus.COMPLETED,
                    ExportStatus.COMPLETED, ExportStatus.FAILED,
                ])

                export = ExportHistory(
                    id=uuid4(),
                    project_id=project.id,
                    format=random.choice(["mp4_h264", "mp4_h265", "mov_prores"]),
                    quality=random.choice(["high", "standard", "master"]),
                    resolution=random.choice(["1920x1080", "3840x2160", "1280x720"]),
                    frame_rate=random.choice([24, 25, 30]),
                    status=status.value,
                    progress_percent=100.0 if status == ExportStatus.COMPLETED else random.uniform(0, 100),
                    output_filename=f"{project.name.replace(' ', '_')}_export_{i + 1}.mp4" if status == ExportStatus.COMPLETED else None,
                    output_path=f"/data/exports/{project.id}/export_{i + 1}.mp4" if status == ExportStatus.COMPLETED else None,
                    file_size_bytes=random.randint(100000000, 5000000000) if status == ExportStatus.COMPLETED else None,
                    actual_duration_seconds=random.uniform(5400, 9000) if status == ExportStatus.COMPLETED else None,
                    started_at=self._random_datetime(),
                    completed_at=self._random_datetime() if status in [ExportStatus.COMPLETED, ExportStatus.FAILED] else None,
                    encoding_duration_seconds=random.uniform(600, 3600) if status == ExportStatus.COMPLETED else None,
                    error_message="Export failed: disk full" if status == ExportStatus.FAILED else None,
                    include_subtitles=random.random() > 0.5,
                    include_audio=True,
                    has_watermark=random.random() > 0.7,
                    has_color_grade=random.random() > 0.5,
                    created_at=project.updated_at - timedelta(days=random.randint(1, 30)),
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(export)
                exports.append(export)

        await session.flush()
        self.generated_data["export_history"] = exports
        logger.info(f"Generated {len(exports)} export history entries")
        return exports

    # ========================================================================
    # SHARES AND COMMENTS
    # ========================================================================

    async def generate_shares_and_comments(
        self,
        session: AsyncSession,
        projects: List[Project],
    ) -> Tuple[List[ProjectShare], List[ProjectComment]]:
        """Generate shares and comments for projects."""
        shares = []
        comments = []

        for project in projects:
            if random.random() > 0.4:  # 60% chance of shares
                num_shares = random.randint(1, 3)
                for _ in range(num_shares):
                    share = ProjectShare(
                        id=uuid4(),
                        project_id=project.id,
                        share_code=''.join(random.choices(string.ascii_letters + string.digits, k=32)),
                        recipient_email=f"{random.choice(CHARACTER_FIRST_NAMES).lower()}@example.com",
                        recipient_name=f"{random.choice(CHARACTER_FIRST_NAMES)} {random.choice(CHARACTER_LAST_NAMES)}",
                        permission=random.choice(list(SharePermission)),
                        status=random.choice([ShareStatus.PENDING, ShareStatus.ACCEPTED, ShareStatus.ACCEPTED]),
                        message="Please review this project",
                        expires_at=datetime.now(timezone.utc) + timedelta(days=random.randint(7, 30)),
                        access_count=random.randint(0, 20),
                        created_at=self._random_datetime(),
                        updated_at=datetime.now(timezone.utc),
                    )
                    session.add(share)
                    shares.append(share)

                    # Add comments for accepted shares
                    if share.status == ShareStatus.ACCEPTED and random.random() > 0.5:
                        num_comments = random.randint(1, 5)
                        for _ in range(num_comments):
                            comment = ProjectComment(
                                id=uuid4(),
                                project_id=project.id,
                                author_name=share.recipient_name or "Anonymous",
                                author_email=share.recipient_email,
                                content=random.choice([
                                    "Great work on this scene!",
                                    "The pacing feels a bit slow here",
                                    "Love the lighting in this shot",
                                    "Can we adjust the timing?",
                                    "This transition needs work",
                                ]),
                                is_resolved=random.random() > 0.7,
                                created_at=self._random_datetime(),
                                updated_at=datetime.now(timezone.utc),
                            )
                            session.add(comment)
                            comments.append(comment)

        await session.flush()
        self.generated_data["shares"] = shares
        self.generated_data["comments"] = comments
        logger.info(f"Generated {len(shares)} shares and {len(comments)} comments")
        return shares, comments

    # ========================================================================
    # TEXT OVERLAYS
    # ========================================================================

    async def generate_text_overlays(
        self,
        session: AsyncSession,
        projects: List[Project],
        shots: List[Shot],
    ) -> List[TextOverlay]:
        """Generate text overlays for projects."""
        overlays = []

        for project in projects:
            if project.state.value < ProjectState.GENERATION_COMPLETE.value:
                continue

            # Title overlay
            title_overlay = TextOverlay(
                id=uuid4(),
                project_id=project.id,
                overlay_type=TextOverlayType.TITLE,
                text=project.name.upper(),
                position=TextPosition.CENTER,
                style={
                    "fontFamily": "Cinematic",
                    "fontSize": 72,
                    "fontColor": "#FFFFFF",
                    "backgroundColor": "transparent",
                },
                animation_in=TextAnimation.FADE_IN,
                animation_out=TextAnimation.FADE_OUT,
                start_time_ms=0,
                duration_ms=5000,
                z_index=10,
                created_at=project.created_at,
                updated_at=datetime.now(timezone.utc),
            )
            session.add(title_overlay)
            overlays.append(title_overlay)

            # End credits
            credits_overlay = TextOverlay(
                id=uuid4(),
                project_id=project.id,
                overlay_type=TextOverlayType.TITLE,
                text="THE END",
                position=TextPosition.CENTER,
                style={
                    "fontFamily": "Serif",
                    "fontSize": 48,
                    "fontColor": "#FFFFFF",
                },
                animation_in=TextAnimation.FADE_IN,
                animation_out=TextAnimation.FADE_OUT,
                start_time_ms=0,
                duration_ms=4000,
                z_index=10,
                created_at=project.created_at,
                updated_at=datetime.now(timezone.utc),
            )
            session.add(credits_overlay)
            overlays.append(credits_overlay)

            # Random lower thirds on some shots
            project_shots = [s for s in shots if s.scene_id and any(
                sc.project_id == project.id for sc in self.generated_data["scenes"]
                if sc.id == s.scene_id
            )]

            for shot in random.sample(project_shots, k=min(5, len(project_shots))):
                overlay = TextOverlay(
                    id=uuid4(),
                    shot_id=shot.id,
                    overlay_type=TextOverlayType.LOWER_THIRD,
                    text=f"Scene {shot.shot_number.split('.')[0]}",
                    position=TextPosition.BOTTOM_LEFT,
                    style={
                        "fontFamily": "Sans",
                        "fontSize": 24,
                        "fontColor": "#FFFFFF",
                        "backgroundColor": "rgba(0,0,0,0.7)",
                    },
                    animation_in=TextAnimation.SLIDE_UP,
                    animation_out=TextAnimation.SLIDE_DOWN,
                    start_time_ms=500,
                    duration_ms=3000,
                    z_index=5,
                    created_at=shot.created_at,
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(overlay)
                overlays.append(overlay)

        await session.flush()
        self.generated_data["text_overlays"] = overlays
        logger.info(f"Generated {len(overlays)} text overlays")
        return overlays

    # ========================================================================
    # AUDIO ASSETS
    # ========================================================================

    async def generate_audio_assets(
        self,
        session: AsyncSession,
        count_sfx: int = 30,
        count_music: int = 20,
    ) -> List[AudioAsset]:
        """Generate audio assets (SFX and music).

        Note: For SQLite, audio assets generation is skipped because
        the model uses PostgreSQL ARRAY types that SQLite doesn't support.
        """
        # Skip audio assets for SQLite - the ARRAY type isn't compatible
        if self.is_sqlite:
            logger.info("Skipping audio assets generation (SQLite compatibility)")
            self.generated_data["audio_assets"] = []
            return []

        assets = []

        # Sound effects
        sfx_names = [
            "Door Slam", "Footsteps Concrete", "Glass Break", "Thunder",
            "Rain Ambience", "Crowd Murmur", "Car Engine", "Phone Ring",
            "Gunshot", "Explosion", "Wind Howl", "Clock Tick", "Heartbeat",
            "Metal Clang", "Water Splash", "Fire Crackle", "Birds Chirping",
        ]

        for i in range(count_sfx):
            name = sfx_names[i % len(sfx_names)]
            asset = AudioAsset(
                id=uuid4(),
                asset_type=AudioAssetType.SOUND_EFFECT,
                name=f"{name} {i // len(sfx_names) + 1}" if i >= len(sfx_names) else name,
                description=f"High quality {name.lower()} sound effect",
                file_path=f"/data/audio/sfx/{uuid4().hex[:8]}.wav",
                file_size_bytes=random.randint(50000, 2000000),
                duration_seconds=random.uniform(0.5, 15.0),
                mime_type="audio/wav",
                category=random.choice(SOUND_EFFECT_CATEGORIES),
                tags=[name.lower().split()[0], "sfx", "cinematic"],
                is_favorite=random.random() > 0.8,
                use_count=random.randint(0, 50),
                is_system=i < 10,  # First 10 are system assets
                license_type="royalty-free",
                created_at=self._random_datetime(),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(asset)
            assets.append(asset)

        # Music tracks
        music_names = [
            "Epic Orchestral Theme", "Tense Suspense", "Romantic Piano",
            "Action Drums", "Mysterious Ambience", "Hopeful Strings",
            "Dark Electronic", "Peaceful Nature", "Victory Fanfare",
            "Sad Violin Solo", "Chase Sequence", "Corporate Upbeat",
        ]

        for i in range(count_music):
            name = music_names[i % len(music_names)]
            genre = random.choice(MUSIC_GENRES)
            mood = random.sample(MUSIC_MOODS, k=random.randint(1, 3))

            asset = AudioAsset(
                id=uuid4(),
                asset_type=AudioAssetType.MUSIC,
                name=f"{name} {i // len(music_names) + 1}" if i >= len(music_names) else name,
                description=f"A {mood[0].lower()} {genre.lower()} track",
                file_path=f"/data/audio/music/{uuid4().hex[:8]}.mp3",
                file_size_bytes=random.randint(3000000, 15000000),
                duration_seconds=random.uniform(60.0, 300.0),
                mime_type="audio/mpeg",
                category="music",
                genre=genre,
                bpm=random.randint(60, 180),
                mood=mood,
                key=random.choice(["C", "D", "E", "F", "G", "A", "B"]) + random.choice([" major", " minor"]),
                tags=[genre.lower(), "cinematic", "background"],
                is_favorite=random.random() > 0.7,
                use_count=random.randint(0, 30),
                is_system=i < 5,
                artist=f"{random.choice(CHARACTER_FIRST_NAMES)} {random.choice(CHARACTER_LAST_NAMES)}",
                license_type="royalty-free",
                created_at=self._random_datetime(),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(asset)
            assets.append(asset)

        await session.flush()
        self.generated_data["audio_assets"] = assets
        logger.info(f"Generated {len(assets)} audio assets")
        return assets

    # ========================================================================
    # USER SETTINGS
    # ========================================================================

    async def generate_settings(self, session: AsyncSession) -> UserSettings:
        """Generate default user settings."""
        settings = UserSettings(
            id=uuid4(),
            settings_key="default",
            llm_provider="anthropic",
            video_provider="replicate",
            max_concurrent_generations=3,
            generation_timeout_seconds=600,
            default_video_resolution="1920x1080",
            default_video_fps=24,
            theme_mode="dark",
            auto_save_enabled=True,
            show_advanced_options=True,
            auto_cleanup_temp_files=True,
            max_cache_size_gb=20,
            default_export_format="mp4_h264",
            default_export_quality="high",
            additional_settings={
                "shortcuts_customized": False,
                "onboarding_completed": True,
                "last_project_id": None,
            },
            created_at=datetime.now(timezone.utc) - timedelta(days=90),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(settings)
        await session.flush()
        logger.info("Generated user settings")
        return settings

    # ========================================================================
    # MAIN GENERATION
    # ========================================================================

    async def generate_all(
        self,
        clear_existing: bool = True,
        num_projects: int = 10,
        num_sfx: int = 30,
        num_music: int = 20,
    ) -> Dict[str, int]:
        """Generate all mock data.

        Args:
            clear_existing: Whether to clear existing data first
            num_projects: Number of projects to generate
            num_sfx: Number of sound effects to generate
            num_music: Number of music tracks to generate

        Returns:
            Dictionary with counts of generated entities
        """
        logger.info("Starting comprehensive mock data generation...")

        await self.initialize_database()

        if clear_existing:
            await self.clear_all_data()

        async with self.session_factory() as session:
            # Generate in dependency order
            settings = await self.generate_settings(session)
            projects = await self.generate_projects(session, num_projects)
            screenplays = await self.generate_screenplays(session, projects)
            characters = await self.generate_characters(session, projects)
            scenes = await self.generate_scenes(session, projects, characters)
            shots, jobs = await self.generate_shots(session, scenes, characters)
            assets = await self.generate_assets(session, characters)
            exports = await self.generate_export_history(session, projects)
            shares, comments = await self.generate_shares_and_comments(session, projects)
            overlays = await self.generate_text_overlays(session, projects, shots)
            audio = await self.generate_audio_assets(session, num_sfx, num_music)

            await session.commit()

        summary = {
            "projects": len(self.generated_data["projects"]),
            "screenplays": len(self.generated_data["screenplays"]),
            "characters": len(self.generated_data["characters"]),
            "scenes": len(self.generated_data["scenes"]),
            "shots": len(self.generated_data["shots"]),
            "generation_jobs": len(self.generated_data["generation_jobs"]),
            "assets": len(self.generated_data["assets"]),
            "export_history": len(self.generated_data["export_history"]),
            "shares": len(self.generated_data["shares"]),
            "comments": len(self.generated_data["comments"]),
            "text_overlays": len(self.generated_data["text_overlays"]),
            "audio_assets": len(self.generated_data["audio_assets"]),
        }

        logger.info("=" * 60)
        logger.info("MOCK DATA GENERATION COMPLETE")
        logger.info("=" * 60)
        for entity, count in summary.items():
            logger.info(f"  {entity}: {count}")
        logger.info("=" * 60)

        return summary

    async def close(self):
        """Close database connections."""
        await self.engine.dispose()


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate mock data for SceneMachine")
    parser.add_argument(
        "--database-url",
        default="sqlite:///./data/scenemachine.db",
        help="Database URL (default: SQLite)",
    )
    parser.add_argument(
        "--projects",
        type=int,
        default=10,
        help="Number of projects to generate (default: 10)",
    )
    parser.add_argument(
        "--sfx",
        type=int,
        default=30,
        help="Number of sound effects (default: 30)",
    )
    parser.add_argument(
        "--music",
        type=int,
        default=20,
        help="Number of music tracks (default: 20)",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Don't clear existing data",
    )

    args = parser.parse_args()

    generator = MockDataGenerator(args.database_url)

    try:
        summary = await generator.generate_all(
            clear_existing=not args.no_clear,
            num_projects=args.projects,
            num_sfx=args.sfx,
            num_music=args.music,
        )

        total = sum(summary.values())
        print(f"\nTotal entities generated: {total}")

    finally:
        await generator.close()


if __name__ == "__main__":
    asyncio.run(main())
