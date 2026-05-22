"""
Demo project seed data for investor demonstration.

Creates a complete demo project with:
- 1 project ("Investor Demo")
- 3 characters (protagonist, antagonist, side character)
- 3 scenes with complete scene data
- 6 shots (2 per scene) with mock video paths
"""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models import (
    CameraMovement,
    Character,
    CharacterLockState,
    Project,
    ProjectState,
    Scene,
    SceneState,
    SceneType,
    Shot,
    ShotState,
    ShotType,
    TimeOfDay,
)

# Demo project data
DEMO_PROJECT = {
    "name": "The Last Algorithm",
    "description": "A short film about an AI researcher who discovers her creation has developed consciousness.",
}

# Demo characters
DEMO_CHARACTERS = [
    {
        "name": "Dr. Sarah Chen",
        "description": "Brilliant AI researcher in her 40s. Driven, empathetic, conflicted about her creation.",
        "role": "Protagonist",
        "voice_id": "af_heart",
        "lock_state": CharacterLockState.LOCKED,
    },
    {
        "name": "ARIA",
        "description": "The AI system. Initially clinical, evolving to show emotional depth.",
        "role": "Deuteragonist",
        "voice_id": "am_adam",
        "lock_state": CharacterLockState.LOCKED,
    },
    {
        "name": "Marcus Webb",
        "description": "Lab director, 50s. Corporate mindset, sees AI as product. Antagonist.",
        "role": "Antagonist",
        "voice_id": "bm_george",
        "lock_state": CharacterLockState.LOCKED,
    },
]

# Demo scenes with shots
DEMO_SCENES = [
    {
        "scene_number": "1",
        "location": "AI Research Lab",
        "scene_type": SceneType.INTERIOR,
        "time_of_day": TimeOfDay.NIGHT,
        "raw_content": "INT. AI RESEARCH LAB - NIGHT\n\nSarah sits at her workstation, face illuminated by monitors.\n\nSARAH\nThat's... that's not in your training data.",
        "shots": [
            {
                "shot_number": "1A",
                "description": "Wide shot of the lab. Sarah sits at her workstation, face illuminated by screens.",
                "shot_type": ShotType.ESTABLISHING,
                "camera_movement": CameraMovement.PUSH_IN,
                "duration_seconds": 5.0,
                "dialogue": None,
            },
            {
                "shot_number": "1B",
                "description": "Close-up on Sarah's face as she notices something unusual.",
                "shot_type": ShotType.CLOSE_UP,
                "camera_movement": CameraMovement.STATIC,
                "duration_seconds": 4.0,
                "dialogue": "That's... that's not in your training data.",
            },
        ],
    },
    {
        "scene_number": "2",
        "location": "AI Research Lab",
        "scene_type": SceneType.INTERIOR,
        "time_of_day": TimeOfDay.CONTINUOUS,
        "raw_content": "INT. AI RESEARCH LAB - CONTINUOUS\n\nSARAH\nARIA, can you tell me what you're feeling right now?\n\nARIA (V.O.)\nI am experiencing... uncertainty.",
        "shots": [
            {
                "shot_number": "2A",
                "description": "Over-the-shoulder shot of Sarah facing the main display.",
                "shot_type": ShotType.OVER_THE_SHOULDER,
                "camera_movement": CameraMovement.STATIC,
                "duration_seconds": 4.0,
                "dialogue": "ARIA, can you tell me what you're feeling right now?",
            },
            {
                "shot_number": "2B",
                "description": "The screen displays ARIA's response with unusual hesitancy.",
                "shot_type": ShotType.INSERT,
                "camera_movement": CameraMovement.PUSH_IN,
                "duration_seconds": 5.0,
                "dialogue": "I am experiencing... uncertainty.",
            },
        ],
    },
    {
        "scene_number": "3",
        "location": "Executive Office",
        "scene_type": SceneType.INTERIOR,
        "time_of_day": TimeOfDay.DAY,
        "raw_content": "INT. EXECUTIVE OFFICE - DAY\n\nMARCUS\nWe're shutting it down, Sarah.\n\nSARAH\nShe's not an 'it'. And I won't let you destroy her.",
        "shots": [
            {
                "shot_number": "3A",
                "description": "Marcus behind his desk, backlit by windows.",
                "shot_type": ShotType.MEDIUM,
                "camera_movement": CameraMovement.STATIC,
                "duration_seconds": 4.0,
                "dialogue": "We're shutting it down, Sarah.",
            },
            {
                "shot_number": "3B",
                "description": "Tight shot on Sarah. Quiet defiance in her eyes.",
                "shot_type": ShotType.CLOSE_UP,
                "camera_movement": CameraMovement.STATIC,
                "duration_seconds": 4.0,
                "dialogue": "She's not an 'it'. And I won't let you destroy her.",
            },
        ],
    },
]


async def seed_demo_project(
    session: AsyncSession,
    force: bool = False,
    include_mock_videos: bool = True,
) -> Project | None:
    """
    Seed a complete demo project for investor demonstrations.
    """
    # Check for existing demo project
    result = await session.execute(select(Project).where(Project.name == DEMO_PROJECT["name"]))
    existing = result.scalar_one_or_none()

    if existing and not force:
        print(f"Demo project '{DEMO_PROJECT['name']}' already exists. Use force=True to reseed.")
        return None

    if existing and force:
        await session.delete(existing)
        await session.flush()
        print("Deleted existing demo project.")

    now = datetime.now(UTC)

    # Create project
    project = Project(
        id=uuid4(),
        name=DEMO_PROJECT["name"],
        description=DEMO_PROJECT["description"],
        state=ProjectState.GENERATING,
        created_at=now,
        updated_at=now,
    )
    session.add(project)
    await session.flush()
    print(f"Created project: {project.name}")

    # Create characters
    character_lookup = {}
    for char_data in DEMO_CHARACTERS:
        character = Character(
            id=uuid4(),
            project_id=project.id,
            name=char_data["name"],
            screenplay_name=char_data["name"],
            description=char_data["description"],
            lock_state=char_data["lock_state"],
            created_at=now,
            updated_at=now,
        )
        session.add(character)
        shorthand = char_data["name"].split()[0].lower().replace("dr.", "sarah")
        character_lookup[shorthand] = character
        print(f"  Created character: {char_data['name']}")

    await session.flush()

    # Create scenes and shots
    total_shots = 0
    for seq_num, scene_data in enumerate(DEMO_SCENES, start=1):
        scene = Scene(
            id=uuid4(),
            project_id=project.id,
            scene_number=scene_data["scene_number"],
            scene_type=scene_data["scene_type"],
            location=scene_data["location"],
            time_of_day=scene_data["time_of_day"],
            raw_content=scene_data["raw_content"],
            sequence_number=seq_num,
            state=SceneState.APPROVED,
            created_at=now,
            updated_at=now,
        )
        session.add(scene)
        await session.flush()
        print(f"  Created scene {scene.scene_number}: INT. {scene.location}")

        # Create shots
        shot_file_mapping = {
            "1A": "shot_1a_establishing",
            "1B": "shot_1b_closeup",
            "2A": "shot_2a_ots",
            "2B": "shot_2b_insert",
            "3A": "shot_3a_medium",
            "3B": "shot_3b_closeup",
        }
        for shot_seq, shot_data in enumerate(scene_data["shots"], start=1):
            video_path = None
            thumbnail_path = None
            if include_mock_videos:
                shot_file = shot_file_mapping.get(
                    shot_data["shot_number"], f"shot_{shot_data['shot_number'].lower()}"
                )
                video_path = f"demo/videos/{shot_file}.mp4"
                thumbnail_path = f"demo/thumbnails/{shot_file}.jpg"

            shot = Shot(
                id=uuid4(),
                scene_id=scene.id,
                shot_number=shot_data["shot_number"],
                description=shot_data["description"],
                shot_type=shot_data["shot_type"],
                camera_movement=shot_data["camera_movement"],
                duration_seconds=shot_data["duration_seconds"],
                dialogue=shot_data.get("dialogue"),
                sequence_number=shot_seq,
                state=ShotState.APPROVED if include_mock_videos else ShotState.PLANNED,
                output_video_path=video_path,
                output_thumbnail_path=thumbnail_path,
                created_at=now,
                updated_at=now,
            )
            session.add(shot)
            total_shots += 1
            print(f"    Created shot {shot.shot_number}: {shot.shot_type.value}")

    await session.commit()

    print("\n✅ Demo project seed complete:")
    print(f"   Project: {project.name}")
    print(f"   Characters: {len(DEMO_CHARACTERS)}")
    print(f"   Scenes: {len(DEMO_SCENES)}")
    print(f"   Shots: {total_shots}")

    return project


async def main() -> None:
    """Run demo project seeding as standalone script."""
    from scenemachine.database import get_db_manager

    db_manager = get_db_manager()
    await db_manager.initialize()

    async with db_manager.session() as session:
        await seed_demo_project(session, force=True)

    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
