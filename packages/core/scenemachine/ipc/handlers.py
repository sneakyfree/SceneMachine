"""IPC method handlers for Electron communication."""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from scenemachine.config import get_settings
from scenemachine.database import get_db_manager
from scenemachine.ipc.server import IPCServer
from scenemachine.models import Project, ProjectState
from scenemachine.services import get_storage_service

logger = logging.getLogger(__name__)


def register_handlers(server: IPCServer) -> None:
    """Register all IPC method handlers.

    Args:
        server: IPC server instance to register handlers on
    """
    # Ensure the global ProviderRegistry is populated before any handler
    # runs. Without this, generation.getProviderModels('local') silently
    # falls back to the hard-coded 'mock' stub because the registry is
    # empty until something else calls setup_providers(). This was the
    # root cause of the desktop UI showing "Mock Provider" as the only
    # local model option instead of the validated Wan22 / LTX-2 stacks.
    try:
        from scenemachine.generators.registry import setup_providers
        setup_providers()
        logger.info("Provider registry populated for IPC server")
    except Exception as e:
        # Don't refuse to start handlers if provider setup fails — non-
        # generation handlers (projects/screenplays/scenes) still work.
        logger.error("setup_providers() failed during IPC handler init: %s", e)

    @server.handler("ping")
    async def handle_ping() -> Dict[str, str]:
        """Health check ping."""
        return {"status": "pong"}

    @server.handler("version")
    async def handle_version() -> Dict[str, str]:
        """Get application version."""
        settings = get_settings()
        return {
            "version": settings.version,
            "environment": settings.environment,
        }

    # Project handlers
    @server.handler("projects.list")
    async def handle_list_projects(
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List all projects."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            stmt = (
                select(Project)
                .options(selectinload(Project.screenplay))
                .offset(skip)
                .limit(limit)
                .order_by(Project.updated_at.desc())
            )
            result = await session.execute(stmt)
            projects = result.scalars().all()

            return [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "description": p.description,
                    "state": p.state.value,
                    "screenplayTitle": p.screenplay.title if p.screenplay else None,
                    "characterCount": p.character_count,
                    "sceneCount": p.scene_count,
                    "createdAt": p.created_at.isoformat(),
                    "updatedAt": p.updated_at.isoformat(),
                }
                for p in projects
            ]

    @server.handler("projects.get")
    async def handle_get_project(id: str) -> Dict[str, Any]:
        """Get project details."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        project_id = UUID(id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = (
                select(Project)
                .options(
                    selectinload(Project.screenplay),
                    selectinload(Project.characters),
                    selectinload(Project.scenes),
                )
                .where(Project.id == project_id)
            )
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project {id} not found")

            return {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "state": project.state.value,
                "settings": project.settings,
                "canAdvance": project.can_advance,
                "screenplay": (
                    {
                        "id": str(project.screenplay.id),
                        "title": project.screenplay.title,
                        "originalFilename": project.screenplay.original_filename,
                        "isParsed": project.screenplay.is_parsed,
                        "moviePlanApproved": project.screenplay.movie_plan_approved,
                    }
                    if project.screenplay
                    else None
                ),
                "characters": [
                    {
                        "id": str(c.id),
                        "name": c.name,
                        "screenplayName": c.screenplay_name,
                        "isLocked": c.is_locked,
                        "isProtagonist": c.is_protagonist,
                    }
                    for c in project.characters
                ],
                "scenes": [
                    {
                        "id": str(s.id),
                        "sceneNumber": s.scene_number,
                        "heading": s.heading,
                        "shotBreakdownApproved": s.shot_breakdown_approved,
                    }
                    for s in project.scenes
                ],
                "characterCount": project.character_count,
                "sceneCount": project.scene_count,
                "createdAt": project.created_at.isoformat(),
                "updatedAt": project.updated_at.isoformat(),
            }

    @server.handler("projects.create")
    async def handle_create_project(
        name: str,
        description: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new project."""
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            project = Project(
                name=name,
                description=description,
                settings=settings or {},
            )

            session.add(project)
            await session.commit()
            await session.refresh(project)

            return {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "state": project.state.value,
                "settings": project.settings,
                "createdAt": project.created_at.isoformat(),
                "updatedAt": project.updated_at.isoformat(),
            }

    @server.handler("projects.update")
    async def handle_update_project(
        id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update project details."""
        from sqlalchemy import select

        project_id = UUID(id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = select(Project).where(Project.id == project_id)
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project {id} not found")

            if name is not None:
                project.name = name
            if description is not None:
                project.description = description
            if settings is not None:
                project.settings = {**project.settings, **settings}

            await session.commit()
            await session.refresh(project)

            return {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "state": project.state.value,
                "settings": project.settings,
                "updatedAt": project.updated_at.isoformat(),
            }

    @server.handler("projects.delete")
    async def handle_delete_project(id: str) -> Dict[str, bool]:
        """Delete a project."""
        from sqlalchemy import select

        project_id = UUID(id)
        db_manager = get_db_manager()
        storage = get_storage_service()

        async with db_manager.session() as session:
            stmt = select(Project).where(Project.id == project_id)
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project {id} not found")

            await session.delete(project)
            await session.commit()

        # Delete project files
        await storage.delete_project(project_id)

        return {"success": True}

    @server.handler("projects.duplicate")
    async def handle_duplicate_project(
        id: str,
        new_name: Optional[str] = None,
        include_generated_videos: bool = False,
    ) -> Dict[str, Any]:
        """Duplicate a project with all its data."""
        from scenemachine.services.project_duplicator import duplicate_project

        project_id = UUID(id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            new_project = await duplicate_project(
                session=session,
                project_id=project_id,
                new_name=new_name,
                include_generated_videos=include_generated_videos,
            )
            await session.commit()

            return {
                "id": str(new_project.id),
                "name": new_project.name,
                "description": new_project.description,
                "state": new_project.state.value,
                "created_at": new_project.created_at.isoformat(),
                "updated_at": new_project.updated_at.isoformat(),
            }

    # Screenplay handlers
    @server.handler("screenplays.upload")
    async def handle_upload_screenplay(
        project_id: str,
        file_path: str,
        filename: str,
    ) -> Dict[str, Any]:
        """Upload a screenplay file from disk.

        Args:
            project_id: Project UUID string
            file_path: Path to the screenplay file on disk
            filename: Original filename
        """
        from pathlib import Path

        from scenemachine.services.screenplay import ScreenplayService

        pid = UUID(project_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = ScreenplayService(session)

            # Open file from disk
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise ValueError(f"File not found: {file_path}")

            with open(file_path_obj, "rb") as f:
                screenplay = await service.upload_screenplay(
                    project_id=pid,
                    file=f,
                    filename=filename,
                )

            return {
                "id": str(screenplay.id),
                "projectId": str(screenplay.project_id),
                "originalFilename": screenplay.original_filename,
                "originalFormat": screenplay.original_format.value,
                "isParsed": screenplay.is_parsed,
                "createdAt": screenplay.created_at.isoformat(),
            }

    @server.handler("screenplays.parse")
    async def handle_parse_screenplay(screenplay_id: str) -> Dict[str, Any]:
        """Parse an uploaded screenplay.

        Args:
            screenplay_id: Screenplay UUID string
        """
        from scenemachine.services.screenplay import ScreenplayService

        sid = UUID(screenplay_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = ScreenplayService(session)
            screenplay = await service.parse_screenplay(sid)

            return {
                "id": str(screenplay.id),
                "isParsed": screenplay.is_parsed,
                "parseErrors": screenplay.parse_errors,
                "metadata": screenplay.parsed_content.get("metadata", {})
                if screenplay.parsed_content
                else {},
            }

    @server.handler("screenplays.get")
    async def handle_get_screenplay(screenplay_id: str) -> Dict[str, Any]:
        """Get screenplay details.

        Args:
            screenplay_id: Screenplay UUID string
        """
        from sqlalchemy import select

        from scenemachine.models import Character, Scene, Screenplay

        sid = UUID(screenplay_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = select(Screenplay).where(Screenplay.id == sid)
            result = await session.execute(stmt)
            screenplay = result.scalar_one_or_none()

            if not screenplay:
                raise ValueError(f"Screenplay {screenplay_id} not found")

            # Get characters
            chars_stmt = select(Character).where(
                Character.project_id == screenplay.project_id
            )
            chars_result = await session.execute(chars_stmt)
            characters = chars_result.scalars().all()

            # Get scenes
            scenes_stmt = (
                select(Scene)
                .where(Scene.project_id == screenplay.project_id)
                .order_by(Scene.sequence_number)
            )
            scenes_result = await session.execute(scenes_stmt)
            scenes = scenes_result.scalars().all()

            return {
                "id": str(screenplay.id),
                "projectId": str(screenplay.project_id),
                "originalFilename": screenplay.original_filename,
                "originalFormat": screenplay.original_format.value,
                "isParsed": screenplay.is_parsed,
                "parseErrors": screenplay.parse_errors,
                "parsedContent": screenplay.parsed_content,
                "characters": [
                    {
                        "id": str(c.id),
                        "name": c.name,
                        "dialogueCount": c.dialogue_count,
                        "sceneCount": c.scene_count,
                    }
                    for c in characters
                ],
                "scenes": [
                    {
                        "id": str(s.id),
                        "sceneNumber": s.scene_number,
                        "sequenceNumber": s.sequence_number,
                        "sceneType": s.scene_type.value,
                        "location": s.location,
                        "timeOfDay": s.time_of_day.value,
                    }
                    for s in scenes
                ],
                "createdAt": screenplay.created_at.isoformat(),
                "updatedAt": screenplay.updated_at.isoformat(),
            }

    @server.handler("screenplays.getByProject")
    async def handle_get_project_screenplay(project_id: str) -> Optional[Dict[str, Any]]:
        """Get screenplay for a project.

        Args:
            project_id: Project UUID string
        """
        from sqlalchemy import select

        from scenemachine.models import Screenplay

        pid = UUID(project_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = select(Screenplay).where(Screenplay.project_id == pid)
            result = await session.execute(stmt)
            screenplay = result.scalar_one_or_none()

            if not screenplay:
                return None

            return {
                "id": str(screenplay.id),
                "projectId": str(screenplay.project_id),
                "originalFilename": screenplay.original_filename,
                "originalFormat": screenplay.original_format.value,
                "isParsed": screenplay.is_parsed,
                "createdAt": screenplay.created_at.isoformat(),
            }

    @server.handler("screenplays.delete")
    async def handle_delete_screenplay(screenplay_id: str) -> Dict[str, bool]:
        """Delete a screenplay.

        Args:
            screenplay_id: Screenplay UUID string
        """
        from scenemachine.services.screenplay import ScreenplayService

        sid = UUID(screenplay_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = ScreenplayService(session)
            deleted = await service.delete_screenplay(sid)

            if not deleted:
                raise ValueError(f"Screenplay {screenplay_id} not found")

            return {"success": True}

    # Movie Plan handlers
    @server.handler("moviePlan.generate")
    async def handle_generate_movie_plan(
        screenplay_id: str,
        regenerate: bool = False,
    ) -> Dict[str, Any]:
        """Generate a movie plan for a screenplay.

        Args:
            screenplay_id: Screenplay UUID string
            regenerate: Whether to regenerate if plan exists
        """
        from scenemachine.services.movie_plan import MoviePlanService

        sid = UUID(screenplay_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = MoviePlanService(session)
            plan = await service.generate_movie_plan(sid, regenerate=regenerate)

            return {
                "screenplayId": plan.screenplay_id,
                "generatedAt": plan.generated_at,
                "aiModel": plan.ai_model,
                "title": plan.title,
                "logline": plan.logline,
                "genre": plan.genre,
                "tone": plan.tone,
                "themes": plan.themes,
                "estimatedRuntimeMinutes": plan.estimated_runtime_minutes,
                "visualStyle": plan.visual_style,
                "colorPalette": plan.color_palette,
                "cinematographyNotes": plan.cinematography_notes,
                "characters": plan.characters,
                "protagonist": plan.protagonist,
                "antagonist": plan.antagonist,
                "scenes": plan.scenes,
                "actStructure": plan.act_structure,
                "locationRequirements": plan.location_requirements,
                "propRequirements": plan.prop_requirements,
                "specialEffectsNotes": plan.special_effects_notes,
                "generationNotes": plan.generation_notes,
                "warnings": plan.warnings,
            }

    @server.handler("moviePlan.get")
    async def handle_get_movie_plan(screenplay_id: str) -> Optional[Dict[str, Any]]:
        """Get the movie plan for a screenplay.

        Args:
            screenplay_id: Screenplay UUID string
        """
        from scenemachine.services.movie_plan import MoviePlanService

        sid = UUID(screenplay_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = MoviePlanService(session)
            plan = await service.get_movie_plan(sid)

            if not plan:
                return None

            return {
                "screenplayId": plan.screenplay_id,
                "generatedAt": plan.generated_at,
                "aiModel": plan.ai_model,
                "title": plan.title,
                "logline": plan.logline,
                "genre": plan.genre,
                "tone": plan.tone,
                "themes": plan.themes,
                "estimatedRuntimeMinutes": plan.estimated_runtime_minutes,
                "visualStyle": plan.visual_style,
                "colorPalette": plan.color_palette,
                "cinematographyNotes": plan.cinematography_notes,
                "characters": plan.characters,
                "protagonist": plan.protagonist,
                "antagonist": plan.antagonist,
                "scenes": plan.scenes,
                "actStructure": plan.act_structure,
                "locationRequirements": plan.location_requirements,
                "propRequirements": plan.prop_requirements,
                "specialEffectsNotes": plan.special_effects_notes,
                "generationNotes": plan.generation_notes,
                "warnings": plan.warnings,
            }

    @server.handler("moviePlan.approve")
    async def handle_approve_movie_plan(screenplay_id: str) -> Dict[str, Any]:
        """Approve the movie plan.

        Args:
            screenplay_id: Screenplay UUID string
        """
        from scenemachine.services.movie_plan import MoviePlanService

        sid = UUID(screenplay_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = MoviePlanService(session)
            await service.approve_movie_plan(sid)

            return {
                "success": True,
                "message": "Movie plan approved. You can now proceed to Character Lab.",
            }

    # Character handlers
    @server.handler("characters.list")
    async def handle_list_characters(project_id: str) -> List[Dict[str, Any]]:
        """List all characters for a project.

        Args:
            project_id: Project UUID string
        """
        from scenemachine.services.character import CharacterService

        pid = UUID(project_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = CharacterService(session)
            characters = await service.get_project_characters(pid, include_references=True)

            return [
                {
                    "id": str(c.id),
                    "projectId": str(c.project_id),
                    "name": c.name,
                    "screenplayName": c.screenplay_name,
                    "description": c.description,
                    "ageRangeMin": c.age_range_min,
                    "ageRangeMax": c.age_range_max,
                    "ageRangeDisplay": c.age_range_display,
                    "gender": c.gender.value,
                    "physicalDescription": c.physical_description,
                    "personalityTraits": c.personality_traits,
                    "lockState": c.lock_state.value,
                    "isLocked": c.is_locked,
                    "sceneCount": c.scene_count,
                    "dialogueCount": c.dialogue_count,
                    "isProtagonist": c.is_protagonist,
                    "referenceCount": len(c.reference_assets) if c.reference_assets else 0,
                    "voiceId": c.voice_id,
                    "voiceProvider": c.voice_provider,
                    "voiceName": c.voice_name,
                    "createdAt": c.created_at.isoformat(),
                    "updatedAt": c.updated_at.isoformat(),
                }
                for c in characters
            ]

    @server.handler("characters.get")
    async def handle_get_character(character_id: str) -> Dict[str, Any]:
        """Get a character by ID.

        Args:
            character_id: Character UUID string
        """
        from scenemachine.services.character import CharacterService

        cid = UUID(character_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = CharacterService(session)
            character = await service.get_character(cid, include_references=True)

            if not character:
                raise ValueError(f"Character {character_id} not found")

            references = []
            if character.reference_assets:
                for asset in character.reference_assets:
                    is_primary = (
                        asset.metadata.get("is_primary", False)
                        if asset.metadata
                        else False
                    )
                    references.append({
                        "id": str(asset.id),
                        "assetType": asset.asset_type.value,
                        "originalFilename": asset.original_filename,
                        "filePath": asset.file_path,
                        "isPrimary": is_primary,
                        "createdAt": asset.created_at.isoformat(),
                    })

            return {
                "id": str(character.id),
                "projectId": str(character.project_id),
                "name": character.name,
                "screenplayName": character.screenplay_name,
                "description": character.description,
                "ageRangeMin": character.age_range_min,
                "ageRangeMax": character.age_range_max,
                "ageRangeDisplay": character.age_range_display,
                "gender": character.gender.value,
                "physicalDescription": character.physical_description,
                "personalityTraits": character.personality_traits,
                "voiceDescription": character.voice_description,
                "lockState": character.lock_state.value,
                "isLocked": character.is_locked,
                "lockedLikeness": character.locked_likeness,
                "sceneCount": character.scene_count,
                "dialogueCount": character.dialogue_count,
                "isProtagonist": character.is_protagonist,
                "referenceAssets": references,
                "createdAt": character.created_at.isoformat(),
                "updatedAt": character.updated_at.isoformat(),
            }

    @server.handler("characters.update")
    async def handle_update_character(
        character_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        age_range_min: Optional[int] = None,
        age_range_max: Optional[int] = None,
        gender: Optional[str] = None,
        physical_description: Optional[Dict[str, Any]] = None,
        personality_traits: Optional[List[str]] = None,
        voice_description: Optional[str] = None,
        is_protagonist: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update a character.

        Args:
            character_id: Character UUID string
            name: Display name
            description: Description
            age_range_min: Min age
            age_range_max: Max age
            gender: Gender value
            physical_description: Physical description dict
            personality_traits: List of traits
            voice_description: Voice description
            is_protagonist: Is protagonist flag
        """
        from scenemachine.models.character import CharacterGender
        from scenemachine.services.character import CharacterService

        cid = UUID(character_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = CharacterService(session)

            gender_enum = None
            if gender:
                gender_enum = CharacterGender(gender)

            character = await service.update_character(
                character_id=cid,
                name=name,
                description=description,
                age_range_min=age_range_min,
                age_range_max=age_range_max,
                gender=gender_enum,
                physical_description=physical_description,
                personality_traits=personality_traits,
                voice_description=voice_description,
                is_protagonist=is_protagonist,
            )

            return {
                "id": str(character.id),
                "name": character.name,
                "lockState": character.lock_state.value,
                "updatedAt": character.updated_at.isoformat(),
            }

    @server.handler("characters.generateDescription")
    async def handle_generate_description(character_id: str) -> Dict[str, Any]:
        """Generate character description from screenplay.

        Args:
            character_id: Character UUID string
        """
        from scenemachine.services.character import CharacterService

        cid = UUID(character_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = CharacterService(session)
            result = await service.generate_character_description(cid)

            return {
                "description": result.get("description", ""),
                "estimatedAge": result.get("estimated_age"),
                "gender": result.get("gender"),
                "personalityTraits": result.get("personality_traits", []),
                "physicalDescription": result.get("physical_description", {}),
            }

    @server.handler("characters.uploadReference")
    async def handle_upload_reference(
        character_id: str,
        file_path: str,
        filename: str,
        is_primary: bool = False,
    ) -> Dict[str, Any]:
        """Upload a reference image from disk.

        Args:
            character_id: Character UUID string
            file_path: Path to image file
            filename: Original filename
            is_primary: Whether this is the primary reference
        """
        from pathlib import Path

        from scenemachine.services.character import CharacterService

        cid = UUID(character_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = CharacterService(session)

            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise ValueError(f"File not found: {file_path}")

            with open(file_path_obj, "rb") as f:
                asset = await service.upload_reference_image(
                    character_id=cid,
                    file=f,
                    filename=filename,
                    is_primary=is_primary,
                )

            return {
                "id": str(asset.id),
                "assetType": asset.asset_type.value,
                "originalFilename": asset.original_filename,
                "filePath": asset.file_path,
                "isPrimary": is_primary,
                "createdAt": asset.created_at.isoformat(),
            }

    @server.handler("characters.deleteReference")
    async def handle_delete_reference(
        character_id: str,
        asset_id: str,
    ) -> Dict[str, bool]:
        """Delete a reference image.

        Args:
            character_id: Character UUID string
            asset_id: Asset UUID string
        """
        from scenemachine.services.character import CharacterService

        cid = UUID(character_id)
        aid = UUID(asset_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = CharacterService(session)
            deleted = await service.delete_reference_image(cid, aid)

            if not deleted:
                raise ValueError("Reference image not found")

            return {"success": True}

    @server.handler("characters.lock")
    async def handle_lock_character(
        character_id: str,
        primary_reference_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Lock a character's likeness.

        Args:
            character_id: Character UUID string
            primary_reference_id: Optional primary reference asset ID
        """
        from scenemachine.services.character import CharacterService

        cid = UUID(character_id)
        primary_ref = UUID(primary_reference_id) if primary_reference_id else None
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = CharacterService(session)
            character = await service.lock_character(cid, primary_ref)

            return {
                "id": str(character.id),
                "name": character.name,
                "lockState": character.lock_state.value,
                "isLocked": character.is_locked,
                "lockedLikeness": character.locked_likeness,
            }

    @server.handler("characters.unlock")
    async def handle_unlock_character(character_id: str) -> Dict[str, Any]:
        """Unlock a character for editing.

        Args:
            character_id: Character UUID string
        """
        from scenemachine.services.character import CharacterService

        cid = UUID(character_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = CharacterService(session)
            character = await service.unlock_character(cid)

            return {
                "id": str(character.id),
                "name": character.name,
                "lockState": character.lock_state.value,
                "isLocked": character.is_locked,
            }

    @server.handler("characters.updateVoice")
    async def handle_update_voice(
        character_id: str,
        voice_id: str,
        voice_provider: str,
        voice_name: str,
    ) -> Dict[str, Any]:
        """Update character voice assignment.

        Args:
            character_id: Character UUID string
            voice_id: Voice ID from TTS provider
            voice_provider: TTS provider name
            voice_name: Display name of the voice
        """
        from scenemachine.services.character import CharacterService

        cid = UUID(character_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = CharacterService(session)
            character = await service.update_voice(
                cid,
                voice_id=voice_id,
                voice_provider=voice_provider,
                voice_name=voice_name,
            )

            return {
                "id": str(character.id),
                "name": character.name,
                "voiceId": character.voice_id,
                "voiceProvider": character.voice_provider,
                "voiceName": character.voice_name,
            }

    @server.handler("characters.getPrompt")
    async def handle_get_prompt(
        character_id: str,
        scene_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get AI generation prompts for a character.

        Args:
            character_id: Character UUID string
            scene_context: Optional scene context
        """
        from scenemachine.services.character import CharacterService

        cid = UUID(character_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = CharacterService(session)
            character = await service.get_character(cid)

            if not character:
                raise ValueError(f"Character {character_id} not found")

            prompt = service.generate_character_prompt(character, scene_context)

            return {
                "positivePrompt": prompt.positive_prompt,
                "negativePrompt": prompt.negative_prompt,
                "stylePrompt": prompt.style_prompt,
                "consistencyTokens": prompt.consistency_tokens,
            }

    # Scene handlers
    @server.handler("scenes.list")
    async def handle_list_scenes(
        project_id: str,
        include_shots: bool = False,
    ) -> List[Dict[str, Any]]:
        """List all scenes for a project.

        Args:
            project_id: Project UUID string
            include_shots: Whether to include shots
        """
        from scenemachine.services.scene_planning import ScenePlanningService

        pid = UUID(project_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = ScenePlanningService(session)
            scenes = await service.get_project_scenes(pid, include_shots=include_shots)

            result = []
            for scene in scenes:
                scene_data = {
                    "id": str(scene.id),
                    "projectId": str(scene.project_id),
                    "sceneNumber": scene.scene_number,
                    "sequenceNumber": scene.sequence_number,
                    "heading": scene.heading,
                    "sceneType": scene.scene_type.value,
                    "location": scene.location,
                    "timeOfDay": scene.time_of_day.value,
                    "state": scene.state.value,
                    "characterIds": [str(cid) for cid in (scene.character_ids or [])],
                    "analysis": scene.analysis,
                    "shotBreakdown": scene.shot_breakdown,
                    "shotBreakdownApproved": scene.shot_breakdown_approved,
                    "estimatedDurationSeconds": scene.estimated_duration_seconds,
                    "shotCount": len(scene.shots) if hasattr(scene, "shots") and scene.shots else 0,
                }

                if include_shots and hasattr(scene, "shots") and scene.shots:
                    scene_data["shots"] = [
                        {
                            "id": str(s.id),
                            "shotNumber": s.shot_number,
                            "sequenceNumber": s.sequence_number,
                            "shotType": s.shot_type.value,
                            "cameraMovement": s.camera_movement.value,
                            "description": s.description,
                            "dialogue": s.dialogue,
                            "action": s.action,
                            "characterIds": [str(cid) for cid in (s.character_ids or [])],
                            "durationSeconds": s.duration_seconds,
                            "compositionNotes": s.composition_notes,
                            "lightingNotes": s.lighting_notes,
                            "state": s.state.value,
                        }
                        for s in sorted(scene.shots, key=lambda x: x.sequence_number)
                    ]

                result.append(scene_data)

            return result

    @server.handler("scenes.get")
    async def handle_get_scene(
        scene_id: str,
        include_shots: bool = True,
    ) -> Dict[str, Any]:
        """Get a scene by ID.

        Args:
            scene_id: Scene UUID string
            include_shots: Whether to include shots
        """
        from scenemachine.services.scene_planning import ScenePlanningService

        sid = UUID(scene_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = ScenePlanningService(session)
            scene = await service.get_scene(sid, include_shots=include_shots)

            if not scene:
                raise ValueError(f"Scene {scene_id} not found")

            scene_data = {
                "id": str(scene.id),
                "projectId": str(scene.project_id),
                "screenplayId": str(scene.screenplay_id) if scene.screenplay_id else None,
                "sceneNumber": scene.scene_number,
                "sequenceNumber": scene.sequence_number,
                "heading": scene.heading,
                "sceneType": scene.scene_type.value,
                "location": scene.location,
                "timeOfDay": scene.time_of_day.value,
                "state": scene.state.value,
                "characterIds": [str(cid) for cid in (scene.character_ids or [])],
                "rawContent": scene.raw_content,
                "actionLines": scene.action_lines,
                "analysis": scene.analysis,
                "shotBreakdown": scene.shot_breakdown,
                "shotBreakdownApproved": scene.shot_breakdown_approved,
                "estimatedDurationSeconds": scene.estimated_duration_seconds,
            }

            if include_shots and scene.shots:
                scene_data["shots"] = [
                    {
                        "id": str(s.id),
                        "shotNumber": s.shot_number,
                        "sequenceNumber": s.sequence_number,
                        "shotType": s.shot_type.value,
                        "cameraMovement": s.camera_movement.value,
                        "description": s.description,
                        "dialogue": s.dialogue,
                        "action": s.action,
                        "characterIds": [str(cid) for cid in (s.character_ids or [])],
                        "durationSeconds": s.duration_seconds,
                        "compositionNotes": s.composition_notes,
                        "lightingNotes": s.lighting_notes,
                        "state": s.state.value,
                        "prompt": s.prompt,
                    }
                    for s in sorted(scene.shots, key=lambda x: x.sequence_number)
                ]

            return scene_data

    @server.handler("scenes.analyze")
    async def handle_analyze_scene(scene_id: str) -> Dict[str, Any]:
        """Analyze a scene for shot planning.

        Args:
            scene_id: Scene UUID string
        """
        from scenemachine.services.scene_planning import ScenePlanningService

        sid = UUID(scene_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = ScenePlanningService(session)
            analysis = await service.analyze_scene(sid)

            return {
                "summary": analysis.summary,
                "mood": analysis.mood,
                "emotionalArc": analysis.emotional_arc,
                "keyMoments": analysis.key_moments,
                "visualStyleSuggestions": analysis.visual_style_suggestions,
                "pacing": analysis.pacing,
                "importance": analysis.importance,
                "suggestedShotCount": analysis.suggested_shot_count,
                "dialogueHeavy": analysis.dialogue_heavy,
                "actionHeavy": analysis.action_heavy,
            }

    @server.handler("scenes.generateBreakdown")
    async def handle_generate_breakdown(
        scene_id: str,
        regenerate: bool = False,
    ) -> Dict[str, Any]:
        """Generate shot breakdown for a scene.

        Args:
            scene_id: Scene UUID string
            regenerate: Whether to regenerate if exists
        """
        from scenemachine.services.scene_planning import ScenePlanningService

        sid = UUID(scene_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = ScenePlanningService(session)
            breakdown = await service.generate_shot_breakdown(sid, regenerate=regenerate)

            # Re-fetch scene to get shot IDs
            scene = await service.get_scene(sid, include_shots=True)

            return {
                "sceneId": breakdown.scene_id,
                "approach": breakdown.approach,
                "coverageStyle": breakdown.coverage_style,
                "notes": breakdown.notes,
                "estimatedDuration": breakdown.estimated_duration,
                "shots": [
                    {
                        "id": str(s.id),
                        "shotNumber": s.shot_number,
                        "sequenceNumber": s.sequence_number,
                        "shotType": s.shot_type.value,
                        "cameraMovement": s.camera_movement.value,
                        "description": s.description,
                        "dialogue": s.dialogue,
                        "action": s.action,
                        "characterIds": [str(cid) for cid in (s.character_ids or [])],
                        "durationSeconds": s.duration_seconds,
                        "compositionNotes": s.composition_notes,
                        "lightingNotes": s.lighting_notes,
                        "state": s.state.value,
                    }
                    for s in sorted(scene.shots, key=lambda x: x.sequence_number)
                ] if scene and scene.shots else [],
            }

    @server.handler("scenes.approve")
    async def handle_approve_breakdown(scene_id: str) -> Dict[str, Any]:
        """Approve the shot breakdown for a scene.

        Args:
            scene_id: Scene UUID string
        """
        from scenemachine.services.scene_planning import ScenePlanningService

        sid = UUID(scene_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = ScenePlanningService(session)
            scene = await service.approve_shot_breakdown(sid)

            return {
                "id": str(scene.id),
                "state": scene.state.value,
                "shotBreakdownApproved": scene.shot_breakdown_approved,
                "message": "Shot breakdown approved. Ready for generation.",
            }

    # Shot handlers
    @server.handler("shots.get")
    async def handle_get_shot(shot_id: str) -> Dict[str, Any]:
        """Get a shot by ID.

        Args:
            shot_id: Shot UUID string
        """
        from scenemachine.services.scene_planning import ScenePlanningService

        sid = UUID(shot_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = ScenePlanningService(session)
            shot = await service.get_shot(sid)

            if not shot:
                raise ValueError(f"Shot {shot_id} not found")

            return {
                "id": str(shot.id),
                "sceneId": str(shot.scene_id),
                "shotNumber": shot.shot_number,
                "sequenceNumber": shot.sequence_number,
                "shotType": shot.shot_type.value,
                "cameraMovement": shot.camera_movement.value,
                "description": shot.description,
                "dialogue": shot.dialogue,
                "action": shot.action,
                "characterIds": [str(cid) for cid in (shot.character_ids or [])],
                "durationSeconds": shot.duration_seconds,
                "compositionNotes": shot.composition_notes,
                "lightingNotes": shot.lighting_notes,
                "state": shot.state.value,
                "prompt": shot.prompt,
            }

    @server.handler("shots.update")
    async def handle_update_shot(
        shot_id: str,
        shot_type: Optional[str] = None,
        camera_movement: Optional[str] = None,
        description: Optional[str] = None,
        dialogue: Optional[str] = None,
        action: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        composition_notes: Optional[str] = None,
        lighting_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a shot.

        Args:
            shot_id: Shot UUID string
            shot_type: New shot type
            camera_movement: New camera movement
            description: New description
            dialogue: New dialogue
            action: New action
            duration_seconds: New duration
            composition_notes: New composition notes
            lighting_notes: New lighting notes
        """
        from scenemachine.models.shot import CameraMovement, ShotType
        from scenemachine.services.scene_planning import ScenePlanningService

        sid = UUID(shot_id)
        db_manager = get_db_manager()

        st = ShotType(shot_type) if shot_type else None
        cm = CameraMovement(camera_movement) if camera_movement else None

        async with db_manager.session() as session:
            service = ScenePlanningService(session)
            shot = await service.update_shot(
                shot_id=sid,
                shot_type=st,
                camera_movement=cm,
                description=description,
                dialogue=dialogue,
                action=action,
                duration_seconds=duration_seconds,
                composition_notes=composition_notes,
                lighting_notes=lighting_notes,
            )

            return {
                "id": str(shot.id),
                "shotType": shot.shot_type.value,
                "cameraMovement": shot.camera_movement.value,
                "description": shot.description,
                "durationSeconds": shot.duration_seconds,
            }

    @server.handler("shots.add")
    async def handle_add_shot(
        scene_id: str,
        shot_type: str,
        description: str,
        camera_movement: str = "static",
        duration_seconds: float = 3.0,
        after_shot_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a new shot to a scene.

        Args:
            scene_id: Scene UUID string
            shot_type: Shot type
            description: Shot description
            camera_movement: Camera movement
            duration_seconds: Duration
            after_shot_id: Insert after this shot
        """
        from scenemachine.models.shot import CameraMovement, ShotType
        from scenemachine.services.scene_planning import ScenePlanningService

        sid = UUID(scene_id)
        after_id = UUID(after_shot_id) if after_shot_id else None
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = ScenePlanningService(session)
            shot = await service.add_shot(
                scene_id=sid,
                shot_type=ShotType(shot_type),
                description=description,
                camera_movement=CameraMovement(camera_movement),
                duration_seconds=duration_seconds,
                after_shot_id=after_id,
            )

            return {
                "id": str(shot.id),
                "sceneId": str(shot.scene_id),
                "shotNumber": shot.shot_number,
                "sequenceNumber": shot.sequence_number,
                "shotType": shot.shot_type.value,
                "cameraMovement": shot.camera_movement.value,
                "description": shot.description,
                "durationSeconds": shot.duration_seconds,
                "state": shot.state.value,
            }

    @server.handler("shots.delete")
    async def handle_delete_shot(shot_id: str) -> Dict[str, bool]:
        """Delete a shot.

        Args:
            shot_id: Shot UUID string
        """
        from scenemachine.services.scene_planning import ScenePlanningService

        sid = UUID(shot_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = ScenePlanningService(session)
            deleted = await service.delete_shot(sid)

            if not deleted:
                raise ValueError(f"Shot {shot_id} not found")

            return {"success": True}

    @server.handler("scenes.getShotTypes")
    async def handle_get_shot_types() -> List[Dict[str, str]]:
        """Get available shot types."""
        from scenemachine.models.shot import ShotType

        descriptions = {
            ShotType.ESTABLISHING: "Wide shot that establishes location/setting",
            ShotType.WIDE: "Full view of the scene with all characters",
            ShotType.MEDIUM_WIDE: "Characters visible from knees up",
            ShotType.MEDIUM: "Characters visible from waist up",
            ShotType.MEDIUM_CLOSE_UP: "Characters visible from chest up",
            ShotType.CLOSE_UP: "Face or important detail fills frame",
            ShotType.EXTREME_CLOSE_UP: "Very tight on specific detail",
            ShotType.TWO_SHOT: "Two characters in frame together",
            ShotType.OVER_THE_SHOULDER: "Shot from behind one character",
            ShotType.POV: "Point of view from character's perspective",
            ShotType.INSERT: "Close shot of specific object or detail",
            ShotType.CUTAWAY: "Shot that cuts away from main action",
        }

        return [
            {
                "value": st.value,
                "label": st.value.replace("_", " ").title(),
                "description": descriptions.get(st, ""),
            }
            for st in ShotType
        ]

    @server.handler("scenes.getCameraMovements")
    async def handle_get_camera_movements() -> List[Dict[str, str]]:
        """Get available camera movements."""
        from scenemachine.models.shot import CameraMovement

        descriptions = {
            CameraMovement.STATIC: "Camera remains stationary",
            CameraMovement.PAN: "Camera pivots horizontally on fixed point",
            CameraMovement.TILT: "Camera pivots vertically on fixed point",
            CameraMovement.DOLLY: "Camera moves toward or away from subject",
            CameraMovement.TRUCK: "Camera moves left or right parallel to subject",
            CameraMovement.CRANE: "Camera moves up or down vertically",
            CameraMovement.HANDHELD: "Camera held by operator for organic movement",
            CameraMovement.STEADICAM: "Stabilized moving camera for smooth tracking",
            CameraMovement.ZOOM: "Lens zooms in or out (not camera movement)",
            CameraMovement.TRACKING: "Camera follows alongside moving subject",
            CameraMovement.ARC: "Camera moves in curved path around subject",
            CameraMovement.PUSH_IN: "Slow dolly toward subject",
            CameraMovement.PULL_OUT: "Slow dolly away from subject",
        }

        return [
            {
                "value": cm.value,
                "label": cm.value.replace("_", " ").title(),
                "description": descriptions.get(cm, ""),
            }
            for cm in CameraMovement
        ]

    # Generation handlers
    @server.handler("generation.getProviders")
    async def handle_get_providers() -> List[Dict[str, Any]]:
        """Get available generation providers."""
        from scenemachine.models.generation_job import JobProvider
        from scenemachine.services.generation import GenerationService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = GenerationService(session)
            available = await service.get_available_providers()

            return [
                {
                    "provider": p.value,
                    "name": p.value.title(),
                    "available": p in available,
                }
                for p in JobProvider
            ]

    @server.handler("generation.getQueueStatus")
    async def handle_get_queue_status(
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get generation queue status."""
        from scenemachine.services.generation import GenerationService

        pid = UUID(project_id) if project_id else None
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = GenerationService(session)
            status = await service.get_queue_status(pid)
            return status

    @server.handler("generation.queueShot")
    async def handle_queue_shot(
        shot_id: str,
        provider: str = "local",
        priority: int = 0,
    ) -> Dict[str, Any]:
        """Queue a shot for generation."""
        from scenemachine.models.generation_job import JobProvider
        from scenemachine.services.generation import GenerationService

        sid = UUID(shot_id)
        prov = JobProvider(provider)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = GenerationService(session)
            job = await service.queue_shot(sid, prov, priority)

            return {
                "id": str(job.id),
                "shotId": str(job.shot_id),
                "jobNumber": job.job_number,
                "status": job.status.value,
                "provider": job.provider.value,
                "queuedAt": job.queued_at.isoformat() if job.queued_at else None,
            }

    @server.handler("generation.queueScene")
    async def handle_queue_scene(
        scene_id: str,
        provider: str = "local",
    ) -> List[Dict[str, Any]]:
        """Queue all planned shots in a scene."""
        from scenemachine.models.generation_job import JobProvider
        from scenemachine.services.generation import GenerationService

        sid = UUID(scene_id)
        prov = JobProvider(provider)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = GenerationService(session)
            jobs = await service.queue_scene(sid, prov)

            return [
                {
                    "id": str(job.id),
                    "shotId": str(job.shot_id),
                    "jobNumber": job.job_number,
                    "status": job.status.value,
                }
                for job in jobs
            ]

    @server.handler("generation.queueProject")
    async def handle_queue_project(
        project_id: str,
        provider: str = "local",
    ) -> Dict[str, Any]:
        """Queue all planned shots in a project."""
        from scenemachine.models.generation_job import JobProvider
        from scenemachine.services.generation import GenerationService

        pid = UUID(project_id)
        prov = JobProvider(provider)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = GenerationService(session)
            jobs = await service.queue_project(pid, prov)

            return {
                "queuedCount": len(jobs),
                "jobs": [
                    {
                        "id": str(job.id),
                        "shotId": str(job.shot_id),
                        "status": job.status.value,
                    }
                    for job in jobs
                ],
            }

    @server.handler("generation.getJob")
    async def handle_get_job(job_id: str) -> Dict[str, Any]:
        """Get a generation job by ID."""
        from scenemachine.services.generation import GenerationService

        jid = UUID(job_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = GenerationService(session)
            job = await service.get_job(jid)

            if not job:
                raise ValueError(f"Job {job_id} not found")

            return {
                "id": str(job.id),
                "shotId": str(job.shot_id),
                "jobNumber": job.job_number,
                "status": job.status.value,
                "provider": job.provider.value,
                "modelId": job.model_id,
                "progressPercent": job.progress_percent,
                "progressMessage": job.progress_message,
                "errorMessage": job.error_message,
                "outputPath": job.output_path,
                "thumbnailPath": job.thumbnail_path,
                "costUsd": job.cost_usd,
                "queuedAt": job.queued_at.isoformat() if job.queued_at else None,
                "startedAt": job.started_at.isoformat() if job.started_at else None,
                "completedAt": job.completed_at.isoformat() if job.completed_at else None,
            }

    @server.handler("generation.processJob")
    async def handle_process_job(job_id: str) -> Dict[str, Any]:
        """Process a pending generation job."""
        from scenemachine.services.generation import GenerationService

        jid = UUID(job_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = GenerationService(session)
            result = await service.process_job(jid)
            job = await service.get_job(jid)

            return {
                "success": result.success,
                "jobId": str(job.id) if job else None,
                "status": job.status.value if job else None,
                "outputPath": result.output_path,
                "errorMessage": result.error_message,
            }

    @server.handler("generation.cancelJob")
    async def handle_cancel_job(job_id: str) -> Dict[str, bool]:
        """Cancel a pending or running job."""
        from scenemachine.services.generation import GenerationService

        jid = UUID(job_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = GenerationService(session)
            cancelled = await service.cancel_job(jid)

            return {"success": cancelled}

    @server.handler("generation.retryJob")
    async def handle_retry_job(job_id: str) -> Dict[str, Any]:
        """Retry a failed job."""
        from scenemachine.services.generation import GenerationService

        jid = UUID(job_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = GenerationService(session)
            job = await service.retry_job(jid)

            if not job:
                raise ValueError("Job cannot be retried")

            return {
                "id": str(job.id),
                "shotId": str(job.shot_id),
                "jobNumber": job.job_number,
                "status": job.status.value,
            }

    @server.handler("generation.approveShot")
    async def handle_approve_shot(shot_id: str) -> Dict[str, Any]:
        """Approve a generated shot."""
        from scenemachine.services.generation import GenerationService

        sid = UUID(shot_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = GenerationService(session)
            shot = await service.approve_shot(sid)

            return {
                "id": str(shot.id),
                "state": shot.state.value,
                "approved": True,
            }

    @server.handler("generation.rejectShot")
    async def handle_reject_shot(
        shot_id: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reject a generated shot for regeneration."""
        from scenemachine.services.generation import GenerationService

        sid = UUID(shot_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = GenerationService(session)
            shot = await service.reject_shot(sid, notes)

            return {
                "id": str(shot.id),
                "state": shot.state.value,
                "rejected": True,
            }

    @server.handler("generation.getPendingJobs")
    async def handle_get_pending_jobs(limit: int = 20) -> List[Dict[str, Any]]:
        """Get pending jobs in queue."""
        from scenemachine.services.generation import GenerationService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = GenerationService(session)
            jobs = await service.get_pending_jobs(limit)

            return [
                {
                    "id": str(job.id),
                    "shotId": str(job.shot_id),
                    "jobNumber": job.job_number,
                    "status": job.status.value,
                    "provider": job.provider.value,
                    "queuedAt": job.queued_at.isoformat() if job.queued_at else None,
                }
                for job in jobs
            ]

    @server.handler("generation.getShotJobs")
    async def handle_get_shot_jobs(shot_id: str) -> List[Dict[str, Any]]:
        """Get all generation jobs for a shot."""
        from sqlalchemy import select

        from scenemachine.models.generation_job import GenerationJob

        sid = UUID(shot_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = (
                select(GenerationJob)
                .where(GenerationJob.shot_id == sid)
                .order_by(GenerationJob.created_at.desc())
            )

            result = await session.execute(stmt)
            jobs = result.scalars().all()

            return [
                {
                    "id": str(job.id),
                    "jobNumber": job.job_number,
                    "status": job.status.value,
                    "provider": job.provider.value,
                    "progressPercent": job.progress_percent,
                    "progressMessage": job.progress_message,
                    "errorMessage": job.error_message,
                    "outputPath": job.output_path,
                    "costUsd": job.cost_usd,
                    "completedAt": job.completed_at.isoformat() if job.completed_at else None,
                }
                for job in jobs
            ]

    @server.handler("generation.getProvidersHealth")
    async def handle_get_providers_health() -> List[Dict[str, Any]]:
        """Get detailed health status for all providers."""
        from scenemachine.config import get_settings
        from scenemachine.services.generation import (
            ReplicateProvider,
            FalProvider,
        )

        settings = get_settings()
        providers = []

        # Replicate
        replicate_configured = bool(settings.replicate_api_token)
        replicate_available = False
        replicate_error = None

        if replicate_configured:
            try:
                provider = ReplicateProvider(
                    api_token=settings.replicate_api_token,
                    model_id=settings.replicate_video_model,
                )
                replicate_available = await provider.check_availability()
            except Exception as e:
                replicate_error = str(e)

        providers.append({
            "provider": "replicate",
            "name": "Replicate",
            "available": replicate_available,
            "configured": replicate_configured,
            "models": ReplicateProvider.list_models(),
            "defaultModel": settings.replicate_video_model or "minimax",
            "error": replicate_error,
        })

        # Fal.ai
        fal_configured = bool(settings.fal_api_key)
        fal_available = False
        fal_error = None

        if fal_configured:
            try:
                provider = FalProvider(
                    api_key=settings.fal_api_key,
                    model_id=settings.fal_video_model,
                )
                fal_available = await provider.check_availability()
            except Exception as e:
                fal_error = str(e)

        providers.append({
            "provider": "fal",
            "name": "Fal.ai",
            "available": fal_available,
            "configured": fal_configured,
            "models": FalProvider.list_models(),
            "defaultModel": settings.fal_video_model or "ltx",
            "error": fal_error,
        })

        # Local
        providers.append({
            "provider": "local",
            "name": "Local (Development)",
            "available": True,
            "configured": True,
            "models": [{
                "id": "mock",
                "name": "Mock Generator",
                "cost_per_second": 0.0,
                "supports_text_to_video": True,
                "supports_image_to_video": True,
                "max_duration": 10.0,
            }],
            "defaultModel": "mock",
            "error": None,
        })

        return providers

    @server.handler("generation.getProviderModels")
    async def handle_get_provider_models(provider_id: str) -> List[Dict[str, Any]]:
        """Get available models for a specific provider.

        Looks the provider up in the central ProviderRegistry first so
        any registered provider (ComfyUI, ActCore, RunPod, etc.) surfaces
        its model list to the desktop renderer's model dropdowns. Falls
        back to the legacy hard-coded paths only if the registry can't
        instantiate the provider (e.g. it needs an API key not yet set).

        Without the registry lookup, the desktop UI was unable to show
        ComfyUI's model list — the dropdown stayed empty even though the
        provider was healthy on /generation.getProvidersHealth.
        """
        from scenemachine.generators.base import get_provider_registry
        from scenemachine.models.generation_job import JobProvider

        # The renderer sends the lowercase JobProvider enum value
        # (e.g. "custom", "replicate"). Convert it to the enum.
        try:
            job_provider = JobProvider(provider_id.lower())
        except ValueError:
            job_provider = None

        if job_provider is not None:
            registry = get_provider_registry()
            if registry.is_registered(job_provider):
                try:
                    provider = registry.get_provider(job_provider)
                    if provider is not None:
                        return provider.list_models()
                except Exception as e:
                    logger.warning(
                        f"Provider {provider_id} registered but list_models failed "
                        f"({e}); falling back to legacy listing."
                    )

        # Legacy fallback for cases where the registry can't instantiate
        # the provider (e.g. provider needs config that isn't present).
        from scenemachine.services.generation import (
            ReplicateProvider,
            FalProvider,
        )

        if provider_id == "replicate":
            return ReplicateProvider.list_models()
        if provider_id == "fal":
            return FalProvider.list_models()
        if provider_id == "local":
            return [{
                "id": "mock",
                "name": "Mock Generator",
                "cost_per_second": 0.0,
                "supports_text_to_video": True,
                "supports_image_to_video": True,
                "max_duration": 10.0,
            }]
        raise ValueError(f"Unknown provider: {provider_id}")

    @server.handler("generation.estimateCost")
    async def handle_estimate_cost(
        provider: str,
        model_id: Optional[str] = None,
        duration_seconds: float = 3.0,
        shot_count: int = 1,
    ) -> Dict[str, Any]:
        """Estimate generation cost."""
        from scenemachine.services.generation import (
            ReplicateProvider,
            FalProvider,
        )

        if provider == "replicate":
            p = ReplicateProvider()
            model = p.get_model(model_id)
            cost_per_shot = p.estimate_cost(model_id, duration_seconds)
        elif provider == "fal":
            p = FalProvider()
            model = p.get_model(model_id)
            cost_per_shot = p.estimate_cost(model_id, duration_seconds)
        elif provider == "local":
            return {
                "provider": "local",
                "modelId": "mock",
                "modelName": "Mock Generator",
                "durationSeconds": duration_seconds,
                "shotCount": shot_count,
                "costPerShot": 0.0,
                "totalCost": 0.0,
                "currency": "USD",
            }
        else:
            raise ValueError(f"Unknown provider: {provider}")

        return {
            "provider": provider,
            "modelId": model_id or p.model_id,
            "modelName": model.name,
            "durationSeconds": duration_seconds,
            "shotCount": shot_count,
            "costPerShot": cost_per_shot,
            "totalCost": cost_per_shot * shot_count,
            "currency": "USD",
        }

    @server.handler("generation.getWorkerStatus")
    async def handle_get_worker_status() -> Dict[str, Any]:
        """Get queue worker status."""
        from scenemachine.services.queue_worker import get_queue_worker

        worker = get_queue_worker()
        return worker.stats.to_dict()

    @server.handler("generation.pauseWorker")
    async def handle_pause_worker() -> Dict[str, bool]:
        """Pause the queue worker."""
        from scenemachine.services.queue_worker import get_queue_worker

        worker = get_queue_worker()
        worker.pause()
        return {"success": True, "paused": True}

    @server.handler("generation.resumeWorker")
    async def handle_resume_worker() -> Dict[str, bool]:
        """Resume the queue worker."""
        from scenemachine.services.queue_worker import get_queue_worker

        worker = get_queue_worker()
        worker.resume()
        return {"success": True, "paused": False}

    # Assembly/Export handlers
    @server.handler("assembly.getStatus")
    async def handle_get_assembly_status(project_id: str) -> Dict[str, Any]:
        """Get assembly status for a project."""
        from scenemachine.services.assembly import AssemblyService

        pid = UUID(project_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AssemblyService(session)
            timeline = await service.get_timeline(pid)

            # Calculate stats
            total_shots = 0
            generated_shots = 0
            missing_shots = []

            for scene in timeline.scenes:
                for shot in scene.shots:
                    total_shots += 1
                    if shot.output_path:
                        generated_shots += 1
                    else:
                        missing_shots.append(f"{scene.scene_number}-{shot.shot_number}")

            return {
                "projectId": str(pid),
                "isReady": generated_shots == total_shots and total_shots > 0,
                "totalScenes": len(timeline.scenes),
                "totalShots": total_shots,
                "generatedShots": generated_shots,
                "missingShots": missing_shots[:10],
                "totalDuration": timeline.total_duration,
            }

    @server.handler("assembly.getTimeline")
    async def handle_get_timeline(project_id: str) -> Dict[str, Any]:
        """Get timeline for a project."""
        from scenemachine.services.assembly import AssemblyService

        pid = UUID(project_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AssemblyService(session)
            timeline = await service.get_timeline(pid)

            scenes_data = []
            for scene in timeline.scenes:
                scenes_data.append({
                    "sceneId": str(scene.scene_id),
                    "sceneNumber": scene.scene_number,
                    "title": scene.title,
                    "duration": scene.duration,
                    "shots": [
                        {
                            "shotId": str(shot.shot_id),
                            "shotNumber": shot.shot_number,
                            "duration": shot.duration,
                            "hasOutput": shot.output_path is not None,
                            "thumbnail": shot.thumbnail_path,
                        }
                        for shot in scene.shots
                    ],
                })

            return {
                "projectId": str(pid),
                "totalDuration": timeline.total_duration,
                "scenes": scenes_data,
            }

    @server.handler("assembly.assembleScene")
    async def handle_assemble_scene(scene_id: str) -> Dict[str, Any]:
        """Assemble a single scene from its shots."""
        from scenemachine.services.assembly import AssemblyService

        sid = UUID(scene_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AssemblyService(session)
            result = await service.assemble_scene(sid)

            return {
                "sceneId": str(sid),
                "outputPath": result.output_path,
                "duration": result.duration,
                "success": True,
            }

    @server.handler("assembly.assembleMovie")
    async def handle_assemble_movie(project_id: str) -> Dict[str, Any]:
        """Assemble all scenes into a movie."""
        from scenemachine.services.assembly import AssemblyService

        pid = UUID(project_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AssemblyService(session)
            output_path = await service.assemble_movie(pid)

            return {
                "projectId": str(pid),
                "outputPath": output_path,
                "success": True,
            }

    @server.handler("assembly.export")
    async def handle_export_movie(
        project_id: str,
        format: str = "mp4_h264",
        quality: str = "high",
        resolution: str = "1920x1080",
        frame_rate: int = 24,
        include_audio: bool = True,
        include_subtitles: bool = False,
        include_text_overlays: bool = True,
        watermark: bool = False,
        watermark_path: Optional[str] = None,
        watermark_position: str = "bottom_right",
        watermark_opacity: float = 0.7,
        output_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Export movie with specified settings."""
        from scenemachine.services.assembly import (
            AssemblyService,
            ExportFormat,
            ExportQuality,
            ExportSettings,
        )

        pid = UUID(project_id)
        db_manager = get_db_manager()

        # Determine watermark path: use custom path if provided, otherwise None
        effective_watermark = watermark_path if watermark and watermark_path else None

        settings = ExportSettings(
            format=ExportFormat(format),
            quality=ExportQuality(quality),
            resolution=resolution,
            frame_rate=frame_rate,
            include_audio=include_audio,
            include_subtitles=include_subtitles,
            include_text_overlays=include_text_overlays,
            watermark=effective_watermark,
            watermark_position=watermark_position,
            watermark_opacity=watermark_opacity,
        )

        async with db_manager.session() as session:
            service = AssemblyService(session)
            result = await service.export_movie(pid, settings, output_filename)

            return {
                "success": result.success,
                "outputPath": result.output_path,
                "fileSize": result.file_size,
                "durationSeconds": result.duration_seconds,
                "errorMessage": result.error_message,
            }

    @server.handler("assembly.getExportHistory")
    async def handle_get_export_history(project_id: str) -> List[Dict[str, Any]]:
        """Get export history for a project."""
        from scenemachine.services.assembly import AssemblyService

        pid = UUID(project_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AssemblyService(session)
            history = await service.get_export_history(pid)
            return history

    @server.handler("assembly.getFormats")
    async def handle_get_export_formats() -> List[Dict[str, Any]]:
        """Get available export formats."""
        from scenemachine.services.assembly import AssemblyService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AssemblyService(session)
            return await service.get_export_formats()

    @server.handler("assembly.getQualityPresets")
    async def handle_get_quality_presets() -> List[Dict[str, Any]]:
        """Get available quality presets."""
        from scenemachine.services.assembly import AssemblyService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AssemblyService(session)
            return await service.get_quality_presets()

    @server.handler("timeline.save")
    async def handle_save_timeline(
        project_id: str,
        clips: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Save timeline clip edits (order, duration, visibility, locking)."""
        from scenemachine.models.shot import Shot

        pid = UUID(project_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            updated_count = 0

            for clip_data in clips:
                shot_id = UUID(clip_data["shotId"])

                # Build update dict with only provided fields
                updates = {}
                if "duration" in clip_data:
                    updates["duration_seconds"] = clip_data["duration"]
                if "isVisible" in clip_data:
                    updates["timeline_visible"] = clip_data["isVisible"]
                if "isLocked" in clip_data:
                    updates["timeline_locked"] = clip_data["isLocked"]
                if "orderIndex" in clip_data:
                    updates["timeline_order"] = clip_data["orderIndex"]
                if "transition" in clip_data:
                    updates["transition_type"] = clip_data["transition"].get("type")
                    updates["transition_duration"] = clip_data["transition"].get("duration")

                if updates:
                    from sqlalchemy import update

                    stmt = (
                        update(Shot)
                        .where(Shot.id == shot_id)
                        .values(**updates)
                    )
                    await session.execute(stmt)
                    updated_count += 1

            await session.commit()

            return {
                "success": True,
                "projectId": str(pid),
                "updatedClips": updated_count,
            }

    @server.handler("timeline.getClipDetails")
    async def handle_get_clip_details(shot_id: str) -> Dict[str, Any]:
        """Get detailed clip information for timeline editing."""
        from scenemachine.models.shot import Shot
        from scenemachine.models.scene import Scene

        sid = UUID(shot_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            from sqlalchemy import select
            from sqlalchemy.orm import joinedload

            stmt = (
                select(Shot)
                .options(joinedload(Shot.scene))
                .where(Shot.id == sid)
            )
            result = await session.execute(stmt)
            shot = result.scalar_one_or_none()

            if not shot:
                raise ValueError(f"Shot not found: {shot_id}")

            return {
                "shotId": str(shot.id),
                "shotNumber": shot.shot_number,
                "sceneId": str(shot.scene_id),
                "sceneNumber": shot.scene.sequence_number if shot.scene else 0,
                "duration": shot.duration_seconds or 3.0,
                "description": shot.description,
                "cameraAngle": shot.camera_angle,
                "cameraMovement": shot.camera_movement,
                "thumbnailPath": shot.thumbnail_path,
                "outputPath": shot.output_path,
                "isVisible": getattr(shot, "timeline_visible", True),
                "isLocked": getattr(shot, "timeline_locked", False),
                "orderIndex": getattr(shot, "timeline_order", 0),
                "transitionType": getattr(shot, "transition_type", None),
                "transitionDuration": getattr(shot, "transition_duration", None),
            }

    # Text Overlay handlers
    @server.handler("overlays.save")
    async def handle_save_overlays(
        project_id: str,
        overlays: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Save text overlays for a project."""
        from scenemachine.models import Project

        pid = UUID(project_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = select(Project).where(Project.id == pid)
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project not found: {project_id}")

            # Store overlays in project metadata
            if not project.metadata:
                project.metadata = {}

            project.metadata["text_overlays"] = overlays
            await session.commit()

            return {
                "success": True,
                "projectId": str(pid),
                "overlayCount": len(overlays),
            }

    @server.handler("overlays.get")
    async def handle_get_overlays(project_id: str) -> List[Dict[str, Any]]:
        """Get text overlays for a project."""
        from scenemachine.models import Project

        pid = UUID(project_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = select(Project).where(Project.id == pid)
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project not found: {project_id}")

            overlays = (project.metadata or {}).get("text_overlays", [])
            return overlays

    # Color Grading handlers
    @server.handler("colorGrade.save")
    async def handle_save_color_grade(
        project_id: str,
        grade: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Save color grading settings for a project."""
        from scenemachine.models import Project

        pid = UUID(project_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = select(Project).where(Project.id == pid)
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project not found: {project_id}")

            # Store grade in project metadata
            if not project.metadata:
                project.metadata = {}

            project.metadata["color_grade"] = grade
            await session.commit()

            return {
                "success": True,
                "projectId": str(pid),
            }

    @server.handler("colorGrade.get")
    async def handle_get_color_grade(project_id: str) -> Dict[str, Any]:
        """Get color grading settings for a project."""
        from scenemachine.models import Project

        pid = UUID(project_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = select(Project).where(Project.id == pid)
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project not found: {project_id}")

            grade = (project.metadata or {}).get("color_grade", {})
            return grade

    @server.handler("colorGrade.getPresets")
    async def handle_get_color_presets() -> List[Dict[str, Any]]:
        """Get built-in color grading presets."""
        return [
            {
                "id": "teal-orange",
                "name": "Teal & Orange",
                "category": "cinematic",
                "grade": {
                    "temperature": 15,
                    "tint": -5,
                    "contrast": 20,
                    "saturation": 10,
                    "shadows": -10,
                },
            },
            {
                "id": "blockbuster",
                "name": "Blockbuster",
                "category": "cinematic",
                "grade": {
                    "contrast": 25,
                    "saturation": -10,
                    "blacks": -15,
                    "highlights": -10,
                    "temperature": 5,
                    "vignetteAmount": 20,
                },
            },
            {
                "id": "vintage-film",
                "name": "Vintage Film",
                "category": "vintage",
                "grade": {
                    "temperature": 20,
                    "contrast": -10,
                    "saturation": -15,
                    "blacks": 10,
                    "grainAmount": 25,
                },
            },
            {
                "id": "noir",
                "name": "Film Noir",
                "category": "cinematic",
                "grade": {
                    "saturation": -100,
                    "contrast": 40,
                    "blacks": -20,
                    "whites": 10,
                    "vignetteAmount": 35,
                    "grainAmount": 15,
                },
            },
            {
                "id": "golden-hour",
                "name": "Golden Hour",
                "category": "natural",
                "grade": {
                    "temperature": 35,
                    "tint": 10,
                    "exposure": 0.15,
                    "contrast": 5,
                    "vibrance": 15,
                },
            },
            {
                "id": "dark-moody",
                "name": "Dark & Moody",
                "category": "dramatic",
                "grade": {
                    "exposure": -0.3,
                    "contrast": 20,
                    "shadows": -20,
                    "blacks": -30,
                    "saturation": -10,
                    "vignetteAmount": 40,
                },
            },
        ]

    # Settings handlers
    @server.handler("settings.get")
    async def handle_get_settings() -> Dict[str, Any]:
        """Get current user settings."""
        from scenemachine.services.settings import SettingsService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SettingsService(session)
            settings = await service.get_settings()
            return settings.to_dict(include_keys=True)

    @server.handler("settings.update")
    async def handle_update_settings(
        llm_provider: Optional[str] = None,
        video_provider: Optional[str] = None,
        max_concurrent_generations: Optional[int] = None,
        generation_timeout_seconds: Optional[int] = None,
        default_video_resolution: Optional[str] = None,
        default_video_fps: Optional[int] = None,
        theme_mode: Optional[str] = None,
        auto_save_enabled: Optional[bool] = None,
        show_advanced_options: Optional[bool] = None,
        auto_cleanup_temp_files: Optional[bool] = None,
        max_cache_size_gb: Optional[int] = None,
        default_export_format: Optional[str] = None,
        default_export_quality: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update user settings."""
        from scenemachine.services.settings import SettingsService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SettingsService(session)
            settings = await service.update_settings(
                llm_provider=llm_provider,
                video_provider=video_provider,
                max_concurrent_generations=max_concurrent_generations,
                generation_timeout_seconds=generation_timeout_seconds,
                default_video_resolution=default_video_resolution,
                default_video_fps=default_video_fps,
                theme_mode=theme_mode,
                auto_save_enabled=auto_save_enabled,
                show_advanced_options=show_advanced_options,
                auto_cleanup_temp_files=auto_cleanup_temp_files,
                max_cache_size_gb=max_cache_size_gb,
                default_export_format=default_export_format,
                default_export_quality=default_export_quality,
            )
            return settings.to_dict(include_keys=True)

    @server.handler("settings.setApiKey")
    async def handle_set_api_key(provider: str, api_key: str) -> Dict[str, Any]:
        """Set API key for a provider."""
        from scenemachine.services.settings import SettingsService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SettingsService(session)
            await service.set_api_key(provider, api_key)
            return {"success": True, "provider": provider}

    @server.handler("settings.removeApiKey")
    async def handle_remove_api_key(provider: str) -> Dict[str, Any]:
        """Remove API key for a provider."""
        from scenemachine.services.settings import SettingsService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SettingsService(session)
            await service.remove_api_key(provider)
            return {"success": True, "provider": provider}

    @server.handler("settings.validateApiKey")
    async def handle_validate_api_key(
        provider: str,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate an API key."""
        from scenemachine.services.settings import SettingsService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SettingsService(session)
            status = await service.validate_api_key(provider, api_key)
            return {
                "provider": status.provider,
                "name": status.name,
                "available": status.available,
                "configured": status.configured,
                "message": status.message,
                "latencyMs": status.latency_ms,
            }

    @server.handler("settings.checkProviders")
    async def handle_check_providers() -> List[Dict[str, Any]]:
        """Check status of all providers."""
        from scenemachine.services.settings import SettingsService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SettingsService(session)
            statuses = await service.check_all_providers()
            return [
                {
                    "provider": s.provider,
                    "name": s.name,
                    "available": s.available,
                    "configured": s.configured,
                    "message": s.message,
                    "latencyMs": s.latency_ms,
                }
                for s in statuses
            ]

    @server.handler("settings.getStorageStats")
    async def handle_get_storage_stats() -> Dict[str, Any]:
        """Get storage statistics."""
        from scenemachine.services.settings import SettingsService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SettingsService(session)
            stats = await service.get_storage_stats()
            return {
                "dataDir": stats.data_dir,
                "uploadDir": stats.upload_dir,
                "outputDir": stats.output_dir,
                "cacheDir": stats.cache_dir,
                "totalSizeBytes": stats.total_size_bytes,
                "uploadSizeBytes": stats.upload_size_bytes,
                "outputSizeBytes": stats.output_size_bytes,
                "cacheSizeBytes": stats.cache_size_bytes,
                "tempFilesCount": stats.temp_files_count,
            }

    @server.handler("settings.clearCache")
    async def handle_clear_cache(cache_type: str = "all") -> Dict[str, Any]:
        """Clear cached files."""
        from scenemachine.services.settings import SettingsService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SettingsService(session)
            result = await service.clear_cache(cache_type)
            return {
                "modelCacheCleared": result["model_cache"],
                "tempFilesCleared": result["temp_files"],
                "bytesFreed": result["bytes_freed"],
            }

    @server.handler("settings.getLlmProviders")
    async def handle_get_llm_providers() -> List[Dict[str, Any]]:
        """Get available LLM providers."""
        from scenemachine.services.settings import SettingsService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SettingsService(session)
            return await service.get_available_llm_providers()

    @server.handler("settings.getVideoProviders")
    async def handle_get_video_providers() -> List[Dict[str, Any]]:
        """Get available video providers."""
        from scenemachine.services.settings import SettingsService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SettingsService(session)
            return await service.get_available_video_providers()

    @server.handler("settings.getThemeOptions")
    async def handle_get_theme_options() -> List[Dict[str, str]]:
        """Get available theme options."""
        from scenemachine.services.settings import SettingsService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SettingsService(session)
            return await service.get_theme_options()

    @server.handler("settings.export")
    async def handle_export_settings() -> Dict[str, Any]:
        """Export settings for backup."""
        from scenemachine.services.settings import SettingsService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SettingsService(session)
            return await service.export_settings()

    @server.handler("settings.import")
    async def handle_import_settings(data: Dict[str, Any]) -> Dict[str, Any]:
        """Import settings from backup."""
        from scenemachine.services.settings import SettingsService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SettingsService(session)
            settings = await service.import_settings(data)
            return settings.to_dict(include_keys=True)

    # Audio/TTS handlers
    @server.handler("audio.getVoices")
    async def handle_get_voices(
        provider: Optional[str] = None,
        gender: Optional[str] = None,
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get available TTS voices."""
        from scenemachine.services.audio import AudioService, TTSProvider, VoiceGender

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AudioService(session)
            await service.initialize_providers()

            provider_enum = TTSProvider(provider) if provider else None
            gender_enum = VoiceGender(gender) if gender else None

            voices = await service.get_available_voices(
                provider=provider_enum,
                gender=gender_enum,
                language=language,
            )

            return [
                {
                    "id": v.id,
                    "name": v.name,
                    "provider": v.provider.value,
                    "gender": v.gender.value,
                    "language": v.language,
                    "accent": v.accent,
                    "previewUrl": v.preview_url,
                    "description": v.description,
                }
                for v in voices
            ]

    @server.handler("audio.getProviders")
    async def handle_get_audio_providers() -> List[Dict[str, Any]]:
        """Get available TTS providers."""
        from scenemachine.services.audio import AudioService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AudioService(session)
            await service.initialize_providers()
            return await service.get_available_providers()

    @server.handler("audio.generateSpeech")
    async def handle_generate_speech(
        text: str,
        voice_id: str,
        provider: str = "mock",
        speed: float = 1.0,
    ) -> Dict[str, Any]:
        """Generate speech from text."""
        from scenemachine.services.audio import AudioService, TTSProvider

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AudioService(session)
            await service.initialize_providers()

            result = await service.generate_speech(
                text=text,
                voice_id=voice_id,
                provider=TTSProvider(provider),
                speed=speed,
            )

            return {
                "success": result.success,
                "audioPath": result.audio_path,
                "durationSeconds": result.duration_seconds,
                "errorMessage": result.error_message,
                "costUsd": result.cost_usd,
            }

    @server.handler("audio.generateDialogue")
    async def handle_generate_dialogue(
        shot_id: str,
        emotion: str = "neutral",
        speed: float = 1.0,
    ) -> Dict[str, Any]:
        """Generate dialogue audio for a shot.

        FEAT-057: Accepts emotion modifier for expressive TTS.

        Args:
            shot_id: UUID of the shot to generate dialogue for
            emotion: Emotion style — neutral, happy, sad, angry, whisper
            speed: Speech speed multiplier (0.5–2.0)
        """
        from scenemachine.services.audio import AudioService

        VALID_EMOTIONS = {"neutral", "happy", "sad", "angry", "whisper"}
        if emotion not in VALID_EMOTIONS:
            emotion = "neutral"
        speed = max(0.5, min(2.0, speed))

        sid = UUID(shot_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AudioService(session)
            await service.initialize_providers()

            result = await service.generate_dialogue(
                sid, emotion=emotion, speed=speed,
            )

            return {
                "success": result.success,
                "audioPath": result.audio_path,
                "durationSeconds": result.duration_seconds,
                "errorMessage": result.error_message,
                "emotion": emotion,
                "speed": speed,
            }

    @server.handler("audio.generateSceneDialogue")
    async def handle_generate_scene_dialogue(
        scene_id: str,
    ) -> Dict[str, Any]:
        """Generate dialogue audio for all shots in a scene (batch).

        FEAT-061: One-click "Generate All Dialogue" for a scene.
        Iterates through every shot in the scene, auto-assigns voices
        if needed, then generates TTS for each dialogue line.
        """
        from scenemachine.services.audio import AudioService

        sid = UUID(scene_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AudioService(session)
            await service.initialize_providers()

            # Get all shots in the scene
            from scenemachine.models.shot import Shot
            from sqlalchemy import select

            stmt = select(Shot).where(Shot.scene_id == sid).order_by(Shot.order)
            result_rows = await session.execute(stmt)
            shots = result_rows.scalars().all()

            results = []
            success_count = 0
            total_cost = 0.0

            for shot in shots:
                try:
                    result = await service.generate_dialogue(shot.id)
                    results.append({
                        "shotId": str(shot.id),
                        "success": result.success,
                        "audioPath": result.audio_path,
                        "durationSeconds": result.duration_seconds,
                        "errorMessage": result.error_message,
                    })
                    if result.success:
                        success_count += 1
                    if hasattr(result, "cost_usd") and result.cost_usd:
                        total_cost += result.cost_usd
                except Exception as e:
                    results.append({
                        "shotId": str(shot.id),
                        "success": False,
                        "audioPath": None,
                        "durationSeconds": 0,
                        "errorMessage": str(e),
                    })

            return {
                "sceneId": scene_id,
                "totalShots": len(shots),
                "successCount": success_count,
                "totalCostUsd": total_cost,
                "results": results,
            }


    @server.handler("audio.assignVoice")
    async def handle_assign_voice(
        character_id: str,
        voice_id: str,
        provider: str,
    ) -> Dict[str, Any]:
        """Assign a voice to a character."""
        from scenemachine.services.audio import AudioService, TTSProvider

        cid = UUID(character_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AudioService(session)
            success = await service.assign_voice_to_character(
                cid,
                voice_id,
                TTSProvider(provider),
            )
            return {"success": success}

    @server.handler("audio.getCharacterVoice")
    async def handle_get_character_voice(character_id: str) -> Optional[Dict[str, str]]:
        """Get voice assignment for a character."""
        from scenemachine.services.audio import AudioService

        cid = UUID(character_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AudioService(session)
            return await service.get_character_voice(cid)

    @server.handler("audio.getDialogueLines")
    async def handle_get_dialogue_lines(
        project_id: str,
        scene_id: Optional[str] = None,
        shot_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get dialogue lines for a project/scene/shot.

        Args:
            project_id: Project UUID
            scene_id: Optional scene filter
            shot_id: Optional shot filter
        """
        from scenemachine.services.audio import AudioService

        pid = UUID(project_id)
        sid = UUID(scene_id) if scene_id else None
        shid = UUID(shot_id) if shot_id else None
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AudioService(session)
            lines = await service.get_dialogue_lines(pid, sid, shid)

            return [
                {
                    "id": str(line.id),
                    "characterId": str(line.character_id),
                    "characterName": line.character_name,
                    "text": line.text,
                    "sceneNumber": line.scene_number,
                    "shotId": str(line.shot_id) if line.shot_id else None,
                    "audioUrl": line.audio_url,
                    "audioDuration": line.audio_duration,
                    "generationStatus": line.generation_status,
                    "syncOffset": line.sync_offset,
                }
                for line in lines
            ]

    @server.handler("audio.deleteDialogueAudio")
    async def handle_delete_dialogue_audio(dialogue_id: str) -> Dict[str, bool]:
        """Delete generated audio for a dialogue line.

        Args:
            dialogue_id: Dialogue line UUID
        """
        from scenemachine.services.audio import AudioService

        did = UUID(dialogue_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AudioService(session)
            success = await service.delete_dialogue_audio(did)
            return {"success": success}

    # Lip Sync handlers
    @server.handler("lipSync.getProviders")
    async def handle_get_lipsync_providers() -> List[Dict[str, Any]]:
        """Get available lip sync providers with status."""
        from scenemachine.services.lipsync import get_lip_sync_service

        service = get_lip_sync_service()
        await service.initialize_providers()
        return await service.get_available_providers()

    @server.handler("lipSync.analyzeAudio")
    async def handle_lipsync_analyze(
        audio_path: str,
        provider: str = "mock",
    ) -> Dict[str, Any]:
        """Analyze audio and extract phoneme timing data."""
        from scenemachine.services.lipsync import LipSyncProvider, get_lip_sync_service

        service = get_lip_sync_service()
        await service.initialize_providers()

        result = await service.analyze_audio(
            audio_path=audio_path,
            provider=LipSyncProvider(provider),
        )

        return {
            "success": result.success,
            "errorMessage": result.error_message,
            "processingTimeSeconds": result.processing_time_seconds,
            "lipSyncData": result.lip_sync_data.to_dict() if result.lip_sync_data else None,
        }

    @server.handler("lipSync.applyToVideo")
    async def handle_lipsync_apply(
        video_path: str,
        audio_path: str,
        output_path: str,
        provider: str = "mock",
    ) -> Dict[str, Any]:
        """Full pipeline: analyze audio and apply lip sync to video."""
        from scenemachine.services.lipsync import LipSyncProvider, get_lip_sync_service

        service = get_lip_sync_service()
        await service.initialize_providers()

        result = await service.apply_to_video(
            video_path=video_path,
            audio_path=audio_path,
            output_path=output_path,
            provider=LipSyncProvider(provider),
        )

        return {
            "success": result.success,
            "outputVideoPath": result.output_video_path,
            "errorMessage": result.error_message,
            "processingTimeSeconds": result.processing_time_seconds,
            "lipSyncData": result.lip_sync_data.to_dict() if result.lip_sync_data else None,
        }

    # Production Pipeline handlers
    @server.handler("pipeline.run")
    async def handle_pipeline_run(
        project_id: str,
        screenplay_path: str,
        file_format: str = "fountain",
        mode: str = "full_auto",
        max_parallel: int = 2,
        quality_threshold: float = 0.7,
        budget_limit: float = 100.0,
    ) -> Dict[str, Any]:
        """Run the full production pipeline (one-click generate).
        
        This is the main entry point for the screenplay-to-movie pipeline.
        It orchestrates parsing, shot generation, TTS, lip sync, and assembly.
        """
        from scenemachine.services.production_pipeline import (
            ProductionPipeline,
            PipelineMode,
        )
        
        pipeline = ProductionPipeline(
            project_id=project_id,
            max_parallel=max_parallel,
            quality_threshold=quality_threshold,
            budget_limit=budget_limit,
        )
        
        try:
            pipeline_mode = PipelineMode(mode)
        except ValueError:
            pipeline_mode = PipelineMode.FULL_AUTO
        
        result = await pipeline.run(
            screenplay_path=screenplay_path,
            file_format=file_format,
            mode=pipeline_mode,
        )
        
        return result.to_dict()

    @server.handler("pipeline.getStatus")
    async def handle_pipeline_status(project_id: str) -> Dict[str, Any]:
        """Get status of a running pipeline.
        
        Note: In a production system, pipeline instances would be stored
        in a registry. For now, returns basic project info.
        """
        return {
            "project_id": project_id,
            "stage": "unknown",
            "message": "Pipeline status tracking requires a running pipeline instance",
        }

    # Crew IPC handlers — mirrors /api/crew/* REST endpoints for Electron
    @server.handler("crew.listAgents")
    async def handle_crew_list_agents() -> List[Dict[str, Any]]:
        """List all registered agents in the orchestrator crew."""
        from scenemachine.agents import (
            OrchestratorAgent, ParserAgent, CharacterAgent,
            GeneratorAgent, AssemblerAgent, ReviewerAgent,
        )
        orchestrator = OrchestratorAgent(name="Director")
        orchestrator.register_agent(ParserAgent(name="Parser"))
        orchestrator.register_agent(CharacterAgent(name="Character"))
        orchestrator.register_agent(GeneratorAgent(name="Generator"))
        orchestrator.register_agent(AssemblerAgent(name="Assembler"))
        orchestrator.register_agent(ReviewerAgent(name="Reviewer"))
        
        return [
            {
                "type": atype.value,
                "name": agent.name,
                "capabilities": agent.capabilities,
                "requires_approval": agent.requires_approval,
            }
            for atype, agent in orchestrator._agents.items()
        ]

    @server.handler("crew.getActionLogs")
    async def handle_crew_get_logs(
        agent_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get action logs from the agent crew."""
        from scenemachine.agents import AgentActionLogger, AgentType
        
        action_logger = AgentActionLogger()
        type_filter = None
        if agent_type:
            try:
                type_filter = AgentType(agent_type)
            except ValueError:
                pass
        
        logs = action_logger.get_logs(agent_type=type_filter, limit=limit)
        return [log.to_dict() for log in logs]

    @server.handler("crew.startPipeline")
    async def handle_crew_start_pipeline(
        project_id: str,
        screenplay_path: Optional[str] = None,
        phases: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Start the agentic crew pipeline."""
        from scenemachine.agents import OrchestratorAgent, ActionContext
        from scenemachine.api.routes.crew import get_orchestrator
        from uuid import UUID
        
        orchestrator = get_orchestrator()
        context = ActionContext(
            project_id=UUID(project_id),
            dry_run=dry_run,
        )
        result = await orchestrator.execute(
            "run_pipeline",
            context,
            screenplay_path=screenplay_path or "",
            phases=phases,
        )
        return {
            "success": result.success,
            "status": result.status.value,
            "output": result.output,
            "cost_usd": result.cost_usd,
        }

    @server.handler("crew.getPipelineStatus")
    async def handle_crew_pipeline_status(
        project_id: str,
    ) -> Dict[str, Any]:
        """Get crew pipeline execution status."""
        from scenemachine.agents import ActionContext
        from scenemachine.api.routes.crew import get_orchestrator
        from uuid import UUID
        
        orchestrator = get_orchestrator()
        context = ActionContext(project_id=UUID(project_id))
        result = await orchestrator.execute("get_status", context)
        output = result.output or {}
        
        return {
            "project_id": output.get("project_id", project_id),
            "status": output.get("status", "idle"),
            "current_phase": output.get("current_phase", "none"),
            "progress_percent": output.get("progress_percent", 0),
            "total_cost_usd": output.get("total_cost_usd", 0),
            "errors": output.get("errors", []),
        }

    @server.handler("crew.controlPipeline")
    async def handle_crew_control_pipeline(
        project_id: str,
        action: str = "pause",
    ) -> Dict[str, str]:
        """Control pipeline: pause, resume, or cancel."""
        from scenemachine.agents import ActionContext
        from scenemachine.api.routes.crew import get_orchestrator
        from uuid import UUID
        
        orchestrator = get_orchestrator()
        context = ActionContext(project_id=UUID(project_id))
        
        action_map = {
            "pause": "pause_pipeline",
            "resume": "resume_pipeline",
            "cancel": "cancel_pipeline",
        }
        method = action_map.get(action, "pause_pipeline")
        result = await orchestrator.execute(method, context)
        return {"message": result.output.get("message", f"Pipeline {action}d")}

    @server.handler("crew.getTotalCost")
    async def handle_crew_total_cost() -> Dict[str, float]:
        """Get total cost of all crew actions."""
        from scenemachine.agents import AgentActionLogger
        action_logger = AgentActionLogger()
        return {"total_cost_usd": action_logger.get_total_cost()}

    # Analytics handlers
    @server.handler("analytics.getGenerationStats")
    async def handle_get_generation_stats(
        time_range: str = "7d",
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get generation job statistics.

        Args:
            time_range: Time range filter (24h, 7d, 30d, all)
            project_id: Optional project filter
        """
        from scenemachine.services.analytics import AnalyticsService

        pid = UUID(project_id) if project_id else None
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AnalyticsService(session)
            stats = await service.get_generation_stats(time_range, pid)

            return {
                "total_jobs": stats.total_jobs,
                "completed_jobs": stats.completed_jobs,
                "failed_jobs": stats.failed_jobs,
                "cancelled_jobs": stats.cancelled_jobs,
                "pending_jobs": stats.pending_jobs,
                "success_rate": stats.success_rate,
                "avg_generation_time_seconds": stats.avg_generation_time_seconds,
                "total_generation_time_seconds": stats.total_generation_time_seconds,
            }

    @server.handler("analytics.getCostStats")
    async def handle_get_cost_stats(
        time_range: str = "7d",
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get cost statistics.

        Args:
            time_range: Time range filter (24h, 7d, 30d, all)
            project_id: Optional project filter
        """
        from scenemachine.services.analytics import AnalyticsService

        pid = UUID(project_id) if project_id else None
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AnalyticsService(session)
            stats = await service.get_cost_stats(time_range, pid)

            return {
                "total_cost_usd": stats.total_cost_usd,
                "cost_by_provider": stats.cost_by_provider,
                "cost_by_project": stats.cost_by_project,
                "avg_cost_per_shot": stats.avg_cost_per_shot,
            }

    @server.handler("analytics.getProjectStats")
    async def handle_get_project_stats() -> Dict[str, Any]:
        """Get project statistics."""
        from scenemachine.services.analytics import AnalyticsService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AnalyticsService(session)
            stats = await service.get_project_stats()

            return {
                "total_projects": stats.total_projects,
                "active_projects": stats.active_projects,
                "total_scenes": stats.total_scenes,
                "total_shots": stats.total_shots,
                "total_characters": stats.total_characters,
            }

    @server.handler("analytics.getPerformanceStats")
    async def handle_get_performance_stats() -> Dict[str, Any]:
        """Get performance statistics."""
        from scenemachine.services.analytics import AnalyticsService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AnalyticsService(session)
            stats = await service.get_performance_stats()

            return {
                "avg_wait_time_seconds": stats.avg_wait_time_seconds,
                "avg_processing_time_seconds": stats.avg_processing_time_seconds,
                "peak_concurrent_jobs": stats.peak_concurrent_jobs,
                "current_queue_size": stats.current_queue_size,
            }

    @server.handler("analytics.getProviderUsage")
    async def handle_get_provider_usage(
        time_range: str = "7d",
    ) -> List[Dict[str, Any]]:
        """Get usage statistics by provider.

        Args:
            time_range: Time range filter
        """
        from scenemachine.services.analytics import AnalyticsService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AnalyticsService(session)
            return await service.get_provider_usage(time_range)

    @server.handler("analytics.getDailyStats")
    async def handle_get_daily_stats(
        days: int = 7,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get daily generation statistics.

        Args:
            days: Number of days to include
            project_id: Optional project filter
        """
        from scenemachine.services.analytics import AnalyticsService

        pid = UUID(project_id) if project_id else None
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AnalyticsService(session)
            return await service.get_daily_stats(days, pid)

    # Templates handlers
    @server.handler("templates.list")
    async def handle_list_templates(
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get all available project templates.

        Args:
            category: Optional category filter
        """
        from scenemachine.services.templates import TemplateCategory, TemplatesService

        service = TemplatesService()
        cat = TemplateCategory(category) if category else None
        templates = await service.get_all_templates(cat)

        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "category": t.category.value,
                "thumbnail": t.thumbnail,
                "defaultResolution": t.default_resolution,
                "defaultFps": t.default_fps,
                "defaultShotDuration": t.default_shot_duration,
                "visualStyle": t.visual_style,
                "colorPalette": t.color_palette,
                "lightingStyle": t.lighting_style,
                "pacing": t.pacing,
                "avgShotsPerScene": t.avg_shots_per_scene,
                "tags": t.tags,
            }
            for t in templates
        ]

    @server.handler("templates.get")
    async def handle_get_template(template_id: str) -> Optional[Dict[str, Any]]:
        """Get a template by ID.

        Args:
            template_id: Template identifier
        """
        from scenemachine.services.templates import TemplatesService

        service = TemplatesService()
        template = await service.get_template(template_id)

        if not template:
            return None

        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "category": template.category.value,
            "thumbnail": template.thumbnail,
            "defaultResolution": template.default_resolution,
            "defaultFps": template.default_fps,
            "defaultShotDuration": template.default_shot_duration,
            "visualStyle": template.visual_style,
            "colorPalette": template.color_palette,
            "lightingStyle": template.lighting_style,
            "defaultProvider": template.default_provider,
            "recommendedModel": template.recommended_model,
            "defaultShotTypes": template.default_shot_types,
            "pacing": template.pacing,
            "avgShotsPerScene": template.avg_shots_per_scene,
            "tags": template.tags,
        }

    @server.handler("templates.getCategories")
    async def handle_get_template_categories() -> List[Dict[str, Any]]:
        """Get available template categories."""
        from scenemachine.services.templates import TemplatesService

        service = TemplatesService()
        return await service.get_template_categories()

    @server.handler("templates.search")
    async def handle_search_templates(
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search templates.

        Args:
            query: Search query
            limit: Max results
        """
        from scenemachine.services.templates import TemplatesService

        service = TemplatesService()
        templates = await service.search_templates(query, limit)

        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "category": t.category.value,
                "tags": t.tags,
            }
            for t in templates
        ]

    @server.handler("templates.getFeatured")
    async def handle_get_featured_templates(limit: int = 6) -> List[Dict[str, Any]]:
        """Get featured templates.

        Args:
            limit: Max templates to return
        """
        from scenemachine.services.templates import TemplatesService

        service = TemplatesService()
        templates = await service.get_featured_templates(limit)

        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "category": t.category.value,
                "thumbnail": t.thumbnail,
                "visualStyle": t.visual_style,
                "colorPalette": t.color_palette,
                "tags": t.tags,
            }
            for t in templates
        ]

    @server.handler("templates.getSettings")
    async def handle_get_template_settings(template_id: str) -> Optional[Dict[str, Any]]:
        """Get project settings from a template.

        Args:
            template_id: Template identifier
        """
        from scenemachine.services.templates import TemplatesService

        service = TemplatesService()
        template = await service.get_template(template_id)

        if not template:
            return None

        return service.get_template_project_settings(template)

    # Queue management handlers
    @server.handler("queue.getAll")
    async def handle_get_queue(
        project_id: Optional[str] = None,
        include_completed: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get all jobs in the queue.

        Args:
            project_id: Optional project filter
            include_completed: Include completed/failed jobs
            limit: Max jobs to return
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from scenemachine.models import Shot
        from scenemachine.models.generation_job import GenerationJob, JobStatus

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            query = select(GenerationJob).options(selectinload(GenerationJob.shot))

            # Filter by status
            if not include_completed:
                query = query.where(
                    GenerationJob.status.in_([
                        JobStatus.PENDING,
                        JobStatus.PREPARING,
                        JobStatus.RUNNING,
                        JobStatus.POST_PROCESSING,
                    ])
                )

            # Filter by project
            if project_id:
                pid = UUID(project_id)
                query = query.join(Shot).where(Shot.project_id == pid)

            # Order by priority (in parameters) and queued_at
            query = query.order_by(
                GenerationJob.queued_at.asc()
            ).limit(limit)

            result = await session.execute(query)
            jobs = result.scalars().all()

            return [
                {
                    "id": str(job.id),
                    "shotId": str(job.shot_id),
                    "shotNumber": job.shot.shot_number if job.shot else None,
                    "sceneId": str(job.shot.scene_id) if job.shot else None,
                    "jobNumber": job.job_number,
                    "status": job.status.value,
                    "provider": job.provider.value,
                    "priority": job.parameters.get("priority", 0) if job.parameters else 0,
                    "progressPercent": job.progress_percent,
                    "progressMessage": job.progress_message,
                    "errorMessage": job.error_message,
                    "queuedAt": job.queued_at.isoformat() if job.queued_at else None,
                    "startedAt": job.started_at.isoformat() if job.started_at else None,
                    "estimatedCompletionAt": None,  # Could calculate based on avg time
                }
                for job in jobs
            ]

    @server.handler("queue.setPriority")
    async def handle_set_priority(
        job_id: str,
        priority: int,
    ) -> Dict[str, Any]:
        """Set priority for a queued job.

        Args:
            job_id: Job UUID
            priority: New priority value (higher = process sooner)
        """
        from sqlalchemy import select

        from scenemachine.models.generation_job import GenerationJob, JobStatus

        jid = UUID(job_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = select(GenerationJob).where(GenerationJob.id == jid)
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found")

            if job.status != JobStatus.PENDING:
                raise ValueError("Can only change priority of pending jobs")

            # Update priority in parameters
            params = job.parameters or {}
            params["priority"] = priority
            job.parameters = params

            await session.commit()

            return {
                "id": str(job.id),
                "priority": priority,
                "status": job.status.value,
            }

    @server.handler("queue.moveToTop")
    async def handle_move_to_top(job_id: str) -> Dict[str, Any]:
        """Move a job to the top of the queue.

        Args:
            job_id: Job UUID
        """
        from sqlalchemy import func, select

        from scenemachine.models.generation_job import GenerationJob, JobStatus

        jid = UUID(job_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            # Get the job
            stmt = select(GenerationJob).where(GenerationJob.id == jid)
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found")

            if job.status != JobStatus.PENDING:
                raise ValueError("Can only reorder pending jobs")

            # Get highest priority
            max_priority = await session.execute(
                select(func.max(GenerationJob.parameters["priority"].as_integer()))
                .where(GenerationJob.status == JobStatus.PENDING)
            )
            current_max = max_priority.scalar() or 0

            # Set higher priority
            params = job.parameters or {}
            params["priority"] = current_max + 10
            job.parameters = params

            await session.commit()

            return {
                "id": str(job.id),
                "priority": params["priority"],
                "status": job.status.value,
            }

    @server.handler("queue.moveToBottom")
    async def handle_move_to_bottom(job_id: str) -> Dict[str, Any]:
        """Move a job to the bottom of the queue.

        Args:
            job_id: Job UUID
        """
        from sqlalchemy import func, select

        from scenemachine.models.generation_job import GenerationJob, JobStatus

        jid = UUID(job_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = select(GenerationJob).where(GenerationJob.id == jid)
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found")

            if job.status != JobStatus.PENDING:
                raise ValueError("Can only reorder pending jobs")

            # Get lowest priority
            min_priority = await session.execute(
                select(func.min(GenerationJob.parameters["priority"].as_integer()))
                .where(GenerationJob.status == JobStatus.PENDING)
            )
            current_min = min_priority.scalar() or 0

            params = job.parameters or {}
            params["priority"] = current_min - 10
            job.parameters = params

            await session.commit()

            return {
                "id": str(job.id),
                "priority": params["priority"],
                "status": job.status.value,
            }

    @server.handler("queue.cancelAll")
    async def handle_cancel_all(project_id: Optional[str] = None) -> Dict[str, Any]:
        """Cancel all pending jobs.

        Args:
            project_id: Optional project filter
        """
        from sqlalchemy import select, update

        from scenemachine.models import Shot
        from scenemachine.models.generation_job import GenerationJob, JobStatus

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            query = select(GenerationJob.id).where(
                GenerationJob.status == JobStatus.PENDING
            )

            if project_id:
                pid = UUID(project_id)
                query = query.join(Shot).where(Shot.project_id == pid)

            result = await session.execute(query)
            job_ids = [row[0] for row in result.all()]

            if job_ids:
                await session.execute(
                    update(GenerationJob)
                    .where(GenerationJob.id.in_(job_ids))
                    .values(status=JobStatus.CANCELLED)
                )
                await session.commit()

            return {
                "cancelledCount": len(job_ids),
                "success": True,
            }

    @server.handler("queue.retryFailed")
    async def handle_retry_failed(project_id: Optional[str] = None) -> Dict[str, Any]:
        """Retry all failed jobs.

        Args:
            project_id: Optional project filter
        """
        from scenemachine.services.generation import GenerationService

        pid = UUID(project_id) if project_id else None
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = GenerationService(session)

            # Get failed jobs
            from sqlalchemy import select

            from scenemachine.models import Shot
            from scenemachine.models.generation_job import GenerationJob, JobStatus

            query = select(GenerationJob).where(
                GenerationJob.status.in_([JobStatus.FAILED, JobStatus.TIMEOUT])
            )

            if pid:
                query = query.join(Shot).where(Shot.project_id == pid)

            result = await session.execute(query)
            failed_jobs = result.scalars().all()

            retried = []
            for job in failed_jobs:
                try:
                    new_job = await service.retry_job(job.id)
                    if new_job:
                        retried.append(str(new_job.id))
                except Exception as e:
                    logger.warning(f"Failed to retry job {job.id}: {e}")

            return {
                "retriedCount": len(retried),
                "jobIds": retried,
                "success": True,
            }

    @server.handler("queue.getStats")
    async def handle_get_queue_stats(project_id: Optional[str] = None) -> Dict[str, Any]:
        """Get queue statistics.

        Args:
            project_id: Optional project filter
        """
        from sqlalchemy import func, select

        from scenemachine.models import Shot
        from scenemachine.models.generation_job import GenerationJob, JobStatus

        pid = UUID(project_id) if project_id else None
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stats = {}

            for status in JobStatus:
                query = select(func.count(GenerationJob.id)).where(
                    GenerationJob.status == status
                )

                if pid:
                    query = query.join(Shot).where(Shot.project_id == pid)

                result = await session.execute(query)
                stats[status.value] = result.scalar() or 0

            # Calculate totals
            pending_total = stats.get("pending", 0)
            running_total = sum([
                stats.get("preparing", 0),
                stats.get("running", 0),
                stats.get("post_processing", 0),
            ])
            completed_total = stats.get("completed", 0)
            failed_total = stats.get("failed", 0) + stats.get("timeout", 0)

            return {
                "byStatus": stats,
                "pending": pending_total,
                "running": running_total,
                "completed": completed_total,
                "failed": failed_total,
                "total": sum(stats.values()),
            }

    # Project archive handlers (import/export)
    @server.handler("project.export")
    async def handle_export_project(
        project_id: str,
        output_path: Optional[str] = None,
        include_assets: bool = True,
        include_outputs: bool = True,
        include_videos: bool = False,
    ) -> Dict[str, Any]:
        """Export a project to an archive file.

        Args:
            project_id: Project UUID
            output_path: Optional custom output path
            include_assets: Include uploaded assets
            include_outputs: Include thumbnails
            include_videos: Include generated videos (large files)
        """
        from pathlib import Path

        from scenemachine.services.project_archive import ProjectArchiveService

        pid = UUID(project_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = ProjectArchiveService(session)
            result = await service.export_project(
                pid,
                output_path=Path(output_path) if output_path else None,
                include_assets=include_assets,
                include_outputs=include_outputs,
                include_generated_videos=include_videos,
            )

            return {
                "success": result.success,
                "archivePath": result.archive_path,
                "fileSizeBytes": result.file_size_bytes,
                "manifest": result.manifest.__dict__ if result.manifest else None,
                "error": result.error,
            }

    @server.handler("project.import")
    async def handle_import_project(
        archive_path: str,
        new_name: Optional[str] = None,
        import_assets: bool = True,
    ) -> Dict[str, Any]:
        """Import a project from an archive file.

        Args:
            archive_path: Path to the archive file
            new_name: Optional new name for the project
            import_assets: Whether to import asset files
        """
        from pathlib import Path

        from scenemachine.services.project_archive import ProjectArchiveService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = ProjectArchiveService(session)
            result = await service.import_project(
                Path(archive_path),
                new_name=new_name,
                import_assets=import_assets,
            )

            return {
                "success": result.success,
                "projectId": result.project_id,
                "projectName": result.project_name,
                "scenesImported": result.scenes_imported,
                "shotsImported": result.shots_imported,
                "charactersImported": result.characters_imported,
                "assetsImported": result.assets_imported,
                "warnings": result.warnings,
                "error": result.error,
            }

    @server.handler("project.getArchiveInfo")
    async def handle_get_archive_info(archive_path: str) -> Optional[Dict[str, Any]]:
        """Get information about an archive without importing.

        Args:
            archive_path: Path to the archive file
        """
        from pathlib import Path

        from scenemachine.services.project_archive import ProjectArchiveService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = ProjectArchiveService(session)
            manifest = await service.get_archive_info(Path(archive_path))

            if manifest:
                return manifest.__dict__
            return None

    @server.handler("project.listExports")
    async def handle_list_exports() -> List[Dict[str, Any]]:
        """List all exported project archives."""
        from scenemachine.services.project_archive import ProjectArchiveService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = ProjectArchiveService(session)
            return await service.list_exports()

    # Project sharing handlers
    @server.handler("sharing.createShare")
    async def handle_create_share(
        project_id: str,
        permission: str = "view",
        recipient_email: Optional[str] = None,
        recipient_name: Optional[str] = None,
        message: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        is_public: bool = False,
    ) -> Dict[str, Any]:
        """Create a project share link.

        Args:
            project_id: Project UUID
            permission: Permission level (view, comment, edit, admin)
            recipient_email: Optional recipient email
            recipient_name: Optional recipient name
            message: Optional message
            expires_in_days: Optional expiration
            is_public: Whether publicly accessible
        """
        from scenemachine.models.share import SharePermission
        from scenemachine.services.sharing import SharingService

        pid = UUID(project_id)
        perm = SharePermission(permission)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SharingService(session)
            result = await service.create_share(
                pid,
                permission=perm,
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                message=message,
                expires_in_days=expires_in_days,
                is_public=is_public,
            )

            return {
                "success": result.success,
                "shareId": result.share_id,
                "shareCode": result.share_code,
                "shareUrl": result.share_url,
                "error": result.error,
            }

    @server.handler("sharing.getProjectShares")
    async def handle_get_project_shares(project_id: str) -> List[Dict[str, Any]]:
        """Get all shares for a project.

        Args:
            project_id: Project UUID
        """
        from scenemachine.services.sharing import SharingService

        pid = UUID(project_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SharingService(session)
            shares = await service.get_project_shares(pid)

            return [
                {
                    "id": s.id,
                    "projectId": s.project_id,
                    "projectName": s.project_name,
                    "shareCode": s.share_code,
                    "permission": s.permission,
                    "status": s.status,
                    "recipientEmail": s.recipient_email,
                    "recipientName": s.recipient_name,
                    "isPublic": s.is_public,
                    "expiresAt": s.expires_at,
                    "createdAt": s.created_at,
                    "accessCount": s.access_count,
                }
                for s in shares
            ]

    @server.handler("sharing.acceptShare")
    async def handle_accept_share(share_code: str) -> Dict[str, Any]:
        """Accept a share invitation.

        Args:
            share_code: The share code
        """
        from scenemachine.services.sharing import SharingService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SharingService(session)
            return await service.accept_share(share_code)

    @server.handler("sharing.revokeShare")
    async def handle_revoke_share(share_id: str) -> Dict[str, Any]:
        """Revoke a share.

        Args:
            share_id: Share UUID
        """
        from scenemachine.services.sharing import SharingService

        sid = UUID(share_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SharingService(session)
            success = await service.revoke_share(sid)
            return {"success": success}

    @server.handler("sharing.updatePermission")
    async def handle_update_share_permission(
        share_id: str,
        permission: str,
    ) -> Dict[str, Any]:
        """Update share permission.

        Args:
            share_id: Share UUID
            permission: New permission level
        """
        from scenemachine.models.share import SharePermission
        from scenemachine.services.sharing import SharingService

        sid = UUID(share_id)
        perm = SharePermission(permission)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SharingService(session)
            success = await service.update_share_permission(sid, perm)
            return {"success": success}

    @server.handler("sharing.addComment")
    async def handle_add_comment(
        project_id: str,
        author_name: str,
        content: str,
        shot_id: Optional[str] = None,
        author_email: Optional[str] = None,
        parent_id: Optional[str] = None,
        timecode_seconds: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Add a comment to a project.

        Args:
            project_id: Project UUID
            author_name: Name of commenter
            content: Comment text
            shot_id: Optional shot UUID
            author_email: Optional email
            parent_id: Optional parent comment for replies
            timecode_seconds: Optional timecode
        """
        from scenemachine.services.sharing import SharingService

        pid = UUID(project_id)
        shot_uuid = UUID(shot_id) if shot_id else None
        parent_uuid = UUID(parent_id) if parent_id else None
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SharingService(session)
            comment = await service.add_comment(
                pid,
                author_name,
                content,
                shot_id=shot_uuid,
                author_email=author_email,
                parent_id=parent_uuid,
                timecode_seconds=timecode_seconds,
            )

            if comment:
                return {
                    "id": str(comment.id),
                    "projectId": str(comment.project_id),
                    "content": comment.content,
                    "authorName": comment.author_name,
                    "createdAt": comment.created_at.isoformat(),
                }
            return None

    @server.handler("sharing.getComments")
    async def handle_get_comments(
        project_id: str,
        shot_id: Optional[str] = None,
        include_resolved: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get comments for a project.

        Args:
            project_id: Project UUID
            shot_id: Optional shot filter
            include_resolved: Include resolved comments
        """
        from scenemachine.services.sharing import SharingService

        pid = UUID(project_id)
        shot_uuid = UUID(shot_id) if shot_id else None
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SharingService(session)
            return await service.get_project_comments(
                pid,
                shot_id=shot_uuid,
                include_resolved=include_resolved,
            )

    @server.handler("sharing.resolveComment")
    async def handle_resolve_comment(comment_id: str) -> Dict[str, Any]:
        """Resolve a comment.

        Args:
            comment_id: Comment UUID
        """
        from scenemachine.services.sharing import SharingService

        cid = UUID(comment_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = SharingService(session)
            success = await service.resolve_comment(cid)
            return {"success": success}

    # System handlers
    @server.handler("system.logError")
    async def handle_log_error(
        type: str,
        message: str,
        stack: Optional[str] = None,
        context: Optional[str] = None,
        componentStack: Optional[str] = None,
        timestamp: Optional[str] = None,
        url: Optional[str] = None,
        userAgent: Optional[str] = None,
        filename: Optional[str] = None,
        lineno: Optional[int] = None,
        colno: Optional[int] = None,
    ) -> Dict[str, bool]:
        """Log a frontend error for tracking.

        Args:
            type: Error type (react_error_boundary, unhandled_rejection, etc.)
            message: Error message
            stack: Stack trace
            context: Error context
            componentStack: React component stack
            timestamp: When the error occurred
            url: Page URL
            userAgent: Browser user agent
            filename: Source file (for uncaught errors)
            lineno: Line number
            colno: Column number
        """
        error_details = {
            "type": type,
            "message": message,
            "timestamp": timestamp,
            "url": url,
        }

        if stack:
            error_details["stack"] = stack[:2000]
        if context:
            error_details["context"] = context
        if componentStack:
            error_details["componentStack"] = componentStack[:1000]
        if filename:
            error_details["filename"] = filename
            error_details["lineno"] = lineno
            error_details["colno"] = colno

        logger.error(f"Frontend error ({type}): {message}", extra=error_details)
        return {"success": True}

    @server.handler("system.getHealth")
    async def handle_get_health() -> Dict[str, Any]:
        """Get system health status."""
        import psutil

        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "status": "healthy",
                "cpu": {"percent": cpu_percent},
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                },
                "disk": {
                    "total": disk.total,
                    "free": disk.free,
                    "percent": disk.percent,
                },
            }
        except Exception as e:
            logger.warning(f"Failed to get system health: {e}")
            return {"status": "unknown", "error": str(e)}

    # Analytics handlers
    @server.handler("analytics.getDashboard")
    async def handle_analytics_dashboard(
        time_range: str = "7d",
    ) -> Dict[str, Any]:
        """Get analytics dashboard data."""
        from scenemachine.services.analytics import AnalyticsService
        from scenemachine.services.cost_tracking import CostTrackingService

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            service = AnalyticsService(session)
            cost_service = CostTrackingService(session)

            generation_stats = await service.get_generation_stats(time_range)
            cost_stats = await service.get_cost_stats(time_range)
            project_stats = await service.get_project_stats()
            performance_stats = await service.get_performance_stats()
            provider_usage = await service.get_provider_usage(time_range)
            daily_stats = await service.get_daily_stats(7)
            budget_alert = await cost_service.check_budget_alert()

            return {
                "generation": {
                    "totalJobs": generation_stats.total_jobs,
                    "completedJobs": generation_stats.completed_jobs,
                    "failedJobs": generation_stats.failed_jobs,
                    "pendingJobs": generation_stats.pending_jobs,
                    "successRate": round(generation_stats.success_rate, 2),
                    "avgGenerationTimeSeconds": round(generation_stats.avg_generation_time_seconds, 2),
                },
                "costs": {
                    "totalCostUsd": round(cost_stats.total_cost_usd, 4),
                    "costByProvider": {k: round(v, 4) for k, v in cost_stats.cost_by_provider.items()},
                    "avgCostPerShot": round(cost_stats.avg_cost_per_shot, 4),
                },
                "projects": {
                    "totalProjects": project_stats.total_projects,
                    "activeProjects": project_stats.active_projects,
                    "totalScenes": project_stats.total_scenes,
                    "totalShots": project_stats.total_shots,
                    "totalCharacters": project_stats.total_characters,
                },
                "performance": {
                    "avgWaitTimeSeconds": round(performance_stats.avg_wait_time_seconds, 2),
                    "avgProcessingTimeSeconds": round(performance_stats.avg_processing_time_seconds, 2),
                    "peakConcurrentJobs": performance_stats.peak_concurrent_jobs,
                    "currentQueueSize": performance_stats.current_queue_size,
                },
                "providerUsage": [
                    {
                        "provider": item["provider"],
                        "totalJobs": item["total_jobs"],
                        "successRate": round(item["success_rate"], 2),
                        "totalCostUsd": round(item["total_cost_usd"], 4),
                    }
                    for item in provider_usage
                ],
                "dailyStats": [
                    {
                        "date": item["date"],
                        "totalJobs": item["total_jobs"],
                        "successRate": round(item["success_rate"], 2),
                        "totalCostUsd": round(item["total_cost_usd"], 4),
                    }
                    for item in daily_stats
                ],
                "budgetAlert": budget_alert,
                "timeRange": time_range,
            }

    # Sharing handlers
    @server.handler("sharing.create")
    async def handle_create_share(
        project_id: str,
        permission: str = "view",
        recipient_email: Optional[str] = None,
        recipient_name: Optional[str] = None,
        message: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        is_public: bool = False,
    ) -> Dict[str, Any]:
        """Create a project share."""
        from scenemachine.models.share import SharePermission
        from scenemachine.services.sharing import SharingService

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            service = SharingService(session)
            result = await service.create_share(
                project_id=UUID(project_id),
                permission=SharePermission(permission),
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                message=message,
                expires_in_days=expires_in_days,
                is_public=is_public,
            )

            if not result.success:
                raise ValueError(result.error)

            return {
                "success": True,
                "shareId": result.share_id,
                "shareCode": result.share_code,
                "shareUrl": result.share_url,
            }

    @server.handler("sharing.accept")
    async def handle_accept_share(
        share_code: str,
    ) -> Dict[str, Any]:
        """Accept a share invitation."""
        from scenemachine.services.sharing import SharingService

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            service = SharingService(session)
            result = await service.accept_share(share_code)

            if not result.get("success"):
                raise ValueError(result.get("error", "Failed to accept share"))

            return result

    @server.handler("sharing.revoke")
    async def handle_revoke_share(
        share_id: str,
    ) -> Dict[str, Any]:
        """Revoke a share."""
        from scenemachine.services.sharing import SharingService

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            service = SharingService(session)
            success = await service.revoke_share(UUID(share_id))

            if not success:
                raise ValueError("Share not found")

            return {"success": True}

    # Archive handlers
    @server.handler("archive.export")
    async def handle_export_project(
        project_id: str,
        include_assets: bool = True,
        include_outputs: bool = True,
        include_generated_videos: bool = False,
    ) -> Dict[str, Any]:
        """Export a project to archive."""
        from scenemachine.services.project_archive import ProjectArchiveService

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            service = ProjectArchiveService(session)
            result = await service.export_project(
                project_id=UUID(project_id),
                include_assets=include_assets,
                include_outputs=include_outputs,
                include_generated_videos=include_generated_videos,
            )

            if not result.success:
                raise ValueError(result.error)

            return {
                "success": True,
                "archivePath": result.archive_path,
                "fileSizeBytes": result.file_size_bytes,
                "manifest": result.manifest.__dict__ if result.manifest else None,
            }

    @server.handler("archive.import")
    async def handle_import_project(
        archive_path: str,
        new_name: Optional[str] = None,
        import_assets: bool = True,
    ) -> Dict[str, Any]:
        """Import a project from archive."""
        from pathlib import Path
        from scenemachine.services.project_archive import ProjectArchiveService

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            service = ProjectArchiveService(session)
            result = await service.import_project(
                archive_path=Path(archive_path),
                new_name=new_name,
                import_assets=import_assets,
            )

            if not result.success:
                raise ValueError(result.error)

            return {
                "success": True,
                "projectId": result.project_id,
                "projectName": result.project_name,
                "scenesImported": result.scenes_imported,
                "shotsImported": result.shots_imported,
                "charactersImported": result.characters_imported,
                "assetsImported": result.assets_imported,
                "warnings": result.warnings,
            }

    @server.handler("archive.list")
    async def handle_list_archives() -> List[Dict[str, Any]]:
        """List all exported archives."""
        from scenemachine.services.project_archive import ProjectArchiveService

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            service = ProjectArchiveService(session)
            archives = await service.list_exports()

            return [
                {
                    "path": archive["path"],
                    "filename": archive["filename"],
                    "sizeBytes": archive["size_bytes"],
                    "createdAt": archive["created_at"],
                    "manifest": archive["manifest"],
                }
                for archive in archives
            ]

    @server.handler("archive.getInfo")
    async def handle_get_archive_info(
        archive_path: str,
    ) -> Dict[str, Any]:
        """Get archive information."""
        from pathlib import Path
        from scenemachine.services.project_archive import ProjectArchiveService

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            service = ProjectArchiveService(session)
            manifest = await service.get_archive_info(Path(archive_path))

            if not manifest:
                raise ValueError("Invalid archive")

            return manifest.__dict__

    # ================================================================
    # Health & Circuit Breaker Handlers
    # ================================================================

    @server.handler("health.getCircuitBreakers")
    async def handle_get_circuit_breakers() -> Dict[str, Any]:
        """Get status of all circuit breakers."""
        from scenemachine.utils.circuit_breaker import CircuitBreakerRegistry

        registry = CircuitBreakerRegistry.get_instance()
        all_status = registry.get_all_status()

        circuits = []
        open_count = 0
        half_open_count = 0

        for name, status in all_status.items():
            stats = status.get("stats", {})
            config = status.get("config", {})

            total = stats.get("total_calls", 0)
            successful = stats.get("successful_calls", 0)
            success_rate = (successful / total * 100) if total > 0 else 100.0

            state = status.get("state", "closed")
            if state == "open":
                open_count += 1
            elif state == "half_open":
                half_open_count += 1

            circuits.append({
                "name": name,
                "state": state,
                "totalCalls": stats.get("total_calls", 0),
                "successfulCalls": stats.get("successful_calls", 0),
                "failedCalls": stats.get("failed_calls", 0),
                "rejectedCalls": stats.get("rejected_calls", 0),
                "consecutiveFailures": stats.get("consecutive_failures", 0),
                "consecutiveSuccesses": stats.get("consecutive_successes", 0),
                "lastFailureTime": stats.get("last_failure"),
                "lastSuccessTime": stats.get("last_success"),
                "failureThreshold": config.get("failure_threshold", 5),
                "recoveryTimeout": config.get("recovery_timeout", 30.0),
                "remainingTimeout": status.get("remaining_timeout", 0.0),
                "successRate": round(success_rate, 1),
            })

        return {
            "circuits": circuits,
            "totalCount": len(circuits),
            "openCount": open_count,
            "halfOpenCount": half_open_count,
        }

    @server.handler("health.resetCircuitBreaker")
    async def handle_reset_circuit_breaker(name: str) -> Dict[str, Any]:
        """Reset a specific circuit breaker to closed state."""
        from scenemachine.utils.circuit_breaker import CircuitBreakerRegistry

        registry = CircuitBreakerRegistry.get_instance()
        cb = registry.get(name)

        if not cb:
            return {"success": False, "error": f"Circuit breaker '{name}' not found"}

        cb.reset()
        return {"success": True, "message": f"Circuit '{name}' reset to closed state"}

    # ================================================================
    # Watermark Handlers
    # ================================================================

    @server.handler("watermarks.list")
    async def handle_list_watermarks() -> Dict[str, Any]:
        """List all available watermarks."""
        from scenemachine.api.routes.watermarks import list_watermarks

        result = await list_watermarks()
        return {
            "watermarks": [w.model_dump() for w in result.watermarks],
            "totalCount": result.total_count,
        }

    @server.handler("watermarks.upload")
    async def handle_upload_watermark(
        filename: str,
        content_base64: str,
    ) -> Dict[str, Any]:
        """Upload a new watermark from base64-encoded content."""
        import base64
        from datetime import datetime
        from pathlib import Path
        from uuid import uuid4

        from scenemachine.api.routes.watermarks import (
            ALLOWED_EXTENSIONS,
            MAX_FILE_SIZE,
            get_watermarks_dir,
        )

        # Validate extension
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return {
                "success": False,
                "error": f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            }

        # Decode content
        try:
            content = base64.b64decode(content_base64)
        except Exception as e:
            return {"success": False, "error": f"Invalid base64 content: {e}"}

        # Check size
        if len(content) > MAX_FILE_SIZE:
            return {
                "success": False,
                "error": f"File too large. Maximum: {MAX_FILE_SIZE // (1024*1024)}MB",
            }

        # Generate unique filename
        watermark_id = str(uuid4())[:8]
        safe_name = "".join(c for c in Path(filename).stem if c.isalnum() or c in "-_")[:32]
        new_filename = f"{safe_name}_{watermark_id}{ext}"

        # Save file
        watermarks_dir = get_watermarks_dir()
        file_path = watermarks_dir / new_filename

        try:
            with open(file_path, "wb") as f:
                f.write(content)

            stat = file_path.stat()
            return {
                "success": True,
                "watermark": {
                    "id": file_path.stem,
                    "filename": new_filename,
                    "path": str(file_path),
                    "sizeBytes": stat.st_size,
                    "createdAt": datetime.now().isoformat(),
                    "isDefault": False,
                },
            }
        except Exception as e:
            if file_path.exists():
                file_path.unlink()
            return {"success": False, "error": f"Failed to save: {e}"}

    @server.handler("watermarks.delete")
    async def handle_delete_watermark(watermark_id: str) -> Dict[str, Any]:
        """Delete a user-uploaded watermark."""
        from scenemachine.api.routes.watermarks import get_watermarks_dir

        if watermark_id.startswith("default_"):
            return {"success": False, "error": "Cannot delete built-in watermarks"}

        watermarks_dir = get_watermarks_dir()

        # Find matching file
        for file in watermarks_dir.iterdir():
            if file.is_file() and file.stem == watermark_id:
                try:
                    file.unlink()
                    return {"success": True}
                except Exception as e:
                    return {"success": False, "error": str(e)}

        return {"success": False, "error": f"Watermark '{watermark_id}' not found"}

    # =============== Audio Library Handlers ===============

    @server.handler("sfx.getEffects")
    async def handle_get_sound_effects(
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        favorites_only: bool = False,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get sound effects with optional filtering."""
        from scenemachine.services.audio_library import AudioLibraryService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AudioLibraryService(session)
            effects = await service.get_sound_effects(
                category=category,
                subcategory=subcategory,
                favorites_only=favorites_only,
                search=search,
            )

            return [
                {
                    "id": str(e.id),
                    "name": e.name,
                    "category": e.category,
                    "subcategory": e.subcategory,
                    "duration": e.duration_seconds,
                    "audioUrl": f"file://{e.file_path}",
                    "tags": e.tags or [],
                    "isFavorite": e.is_favorite,
                    "isCustom": not e.is_system,
                }
                for e in effects
            ]

    @server.handler("sfx.toggleFavorite")
    async def handle_toggle_sfx_favorite(effect_id: str) -> Dict[str, bool]:
        """Toggle favorite status for a sound effect."""
        from scenemachine.services.audio_library import AudioLibraryService

        eid = UUID(effect_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AudioLibraryService(session)
            new_status = await service.toggle_favorite(eid)
            return {"isFavorite": new_status}

    @server.handler("music.getTracks")
    async def handle_get_music_tracks(
        genre: Optional[str] = None,
        mood: Optional[str] = None,
        favorites_only: bool = False,
        custom_only: bool = False,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get music tracks with optional filtering."""
        from scenemachine.services.audio_library import AudioLibraryService

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AudioLibraryService(session)
            tracks = await service.get_music_tracks(
                genre=genre,
                mood=mood,
                favorites_only=favorites_only,
                custom_only=custom_only,
                search=search,
            )

            return [
                {
                    "id": str(t.id),
                    "title": t.name,
                    "artist": t.artist,
                    "duration": t.duration_seconds,
                    "genre": t.genre or "Cinematic",
                    "mood": t.mood or [],
                    "bpm": t.bpm,
                    "audioUrl": f"file://{t.file_path}",
                    "waveformUrl": f"file://{t.waveform_path}" if t.waveform_path else None,
                    "isFavorite": t.is_favorite,
                    "isCustom": not t.is_system,
                    "tags": t.tags or [],
                }
                for t in tracks
            ]

    @server.handler("music.getTrack")
    async def handle_get_music_track(track_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific music track."""
        from scenemachine.services.audio_library import AudioLibraryService
        from scenemachine.models.audio_asset import AudioAssetType

        tid = UUID(track_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AudioLibraryService(session)
            track = await service.get_audio_asset(tid)

            if not track or track.asset_type != AudioAssetType.MUSIC:
                return None

            return {
                "id": str(track.id),
                "title": track.name,
                "artist": track.artist,
                "duration": track.duration_seconds,
                "genre": track.genre or "Cinematic",
                "mood": track.mood or [],
                "bpm": track.bpm,
                "audioUrl": f"file://{track.file_path}",
                "waveformUrl": f"file://{track.waveform_path}" if track.waveform_path else None,
                "isFavorite": track.is_favorite,
                "isCustom": not track.is_system,
                "tags": track.tags or [],
            }

    @server.handler("music.toggleFavorite")
    async def handle_toggle_music_favorite(track_id: str) -> Dict[str, bool]:
        """Toggle favorite status for a music track."""
        from scenemachine.services.audio_library import AudioLibraryService

        tid = UUID(track_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AudioLibraryService(session)
            new_status = await service.toggle_favorite(tid)
            return {"isFavorite": new_status}

    @server.handler("music.uploadTrack")
    async def handle_upload_music_track(
        file_path: str,
        genre: str = "Cinematic",
        mood: Optional[str] = None,
        artist: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a custom music track."""
        from scenemachine.services.audio_library import AudioLibraryService
        from scenemachine.models.audio_asset import AudioAssetType

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            try:
                moods = [mood] if mood else None
                service = AudioLibraryService(session)
                asset = await service.upload_audio(
                    file_path=file_path,
                    asset_type=AudioAssetType.MUSIC,
                    genre=genre,
                    mood=moods,
                    artist=artist,
                )

                return {
                    "success": True,
                    "id": str(asset.id),
                    "name": asset.name,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

    @server.handler("sfx.uploadEffect")
    async def handle_upload_sound_effect(
        file_path: str,
        category: str = "other",
        subcategory: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a custom sound effect."""
        from scenemachine.services.audio_library import AudioLibraryService
        from scenemachine.models.audio_asset import AudioAssetType

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            try:
                service = AudioLibraryService(session)
                asset = await service.upload_audio(
                    file_path=file_path,
                    asset_type=AudioAssetType.SOUND_EFFECT,
                    category=category,
                    subcategory=subcategory,
                )

                return {
                    "success": True,
                    "id": str(asset.id),
                    "name": asset.name,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

    # =========================================================================
    # Text Overlay Handlers
    # =========================================================================

    @server.handler("textOverlays.getPresets")
    async def handle_get_text_overlay_presets() -> List[Dict[str, Any]]:
        """Get available text overlay presets."""
        from scenemachine.models.text_overlay import (
            TextOverlayType,
            DEFAULT_STYLES,
        )

        return [
            {"type": "title", "label": "Title", "style": DEFAULT_STYLES[TextOverlayType.TITLE]},
            {"type": "subtitle", "label": "Subtitle", "style": DEFAULT_STYLES[TextOverlayType.SUBTITLE]},
            {"type": "lower_third", "label": "Lower Third", "style": DEFAULT_STYLES[TextOverlayType.LOWER_THIRD]},
            {"type": "caption", "label": "Caption", "style": DEFAULT_STYLES[TextOverlayType.CAPTION]},
            {"type": "custom", "label": "Custom", "style": DEFAULT_STYLES[TextOverlayType.CUSTOM]},
        ]

    @server.handler("textOverlays.getForShot")
    async def handle_get_shot_text_overlays(shot_id: str) -> List[Dict[str, Any]]:
        """Get text overlays for a shot."""
        from scenemachine.models.text_overlay import TextOverlay
        from sqlalchemy import select

        sid = UUID(shot_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = (
                select(TextOverlay)
                .where(TextOverlay.shot_id == sid)
                .order_by(TextOverlay.z_index)
            )
            result = await session.execute(stmt)
            overlays = result.scalars().all()

            return [o.to_dict() for o in overlays]

    @server.handler("textOverlays.getForScene")
    async def handle_get_scene_text_overlays(scene_id: str) -> List[Dict[str, Any]]:
        """Get text overlays for a scene."""
        from scenemachine.models.text_overlay import TextOverlay
        from sqlalchemy import select

        sid = UUID(scene_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = (
                select(TextOverlay)
                .where(TextOverlay.scene_id == sid)
                .order_by(TextOverlay.z_index)
            )
            result = await session.execute(stmt)
            overlays = result.scalars().all()

            return [o.to_dict() for o in overlays]

    @server.handler("textOverlays.getForProject")
    async def handle_get_project_text_overlays(project_id: str) -> List[Dict[str, Any]]:
        """Get text overlays for a project."""
        from scenemachine.models.text_overlay import TextOverlay
        from sqlalchemy import select

        pid = UUID(project_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = (
                select(TextOverlay)
                .where(TextOverlay.project_id == pid)
                .order_by(TextOverlay.z_index)
            )
            result = await session.execute(stmt)
            overlays = result.scalars().all()

            return [o.to_dict() for o in overlays]

    @server.handler("textOverlays.create")
    async def handle_create_text_overlay(
        text: str,
        shot_id: Optional[str] = None,
        scene_id: Optional[str] = None,
        project_id: Optional[str] = None,
        overlay_type: str = "custom",
        position: str = "center",
        custom_x: Optional[float] = None,
        custom_y: Optional[float] = None,
        style: Optional[Dict[str, Any]] = None,
        animation_in: str = "fade_in",
        animation_out: str = "fade_out",
        animation_in_duration_ms: int = 500,
        animation_out_duration_ms: int = 500,
        start_time_ms: int = 0,
        duration_ms: int = 5000,
        is_visible: bool = True,
        z_index: int = 1,
    ) -> Dict[str, Any]:
        """Create a new text overlay."""
        from scenemachine.models.text_overlay import (
            TextOverlay,
            TextOverlayType,
            TextPosition,
            TextAnimation,
            DEFAULT_STYLES,
        )

        db_manager = get_db_manager()

        # Validate parent
        shot_uuid = UUID(shot_id) if shot_id else None
        scene_uuid = UUID(scene_id) if scene_id else None
        project_uuid = UUID(project_id) if project_id else None

        if not any([shot_uuid, scene_uuid, project_uuid]):
            return {"success": False, "error": "One of shot_id, scene_id, or project_id is required"}

        # Get enums
        try:
            otype = TextOverlayType(overlay_type)
        except ValueError:
            otype = TextOverlayType.CUSTOM

        try:
            pos = TextPosition(position)
        except ValueError:
            pos = TextPosition.CENTER

        try:
            anim_in = TextAnimation(animation_in)
        except ValueError:
            anim_in = TextAnimation.FADE_IN

        try:
            anim_out = TextAnimation(animation_out)
        except ValueError:
            anim_out = TextAnimation.FADE_OUT

        # Merge style with defaults
        default_style = DEFAULT_STYLES.get(otype, DEFAULT_STYLES[TextOverlayType.CUSTOM])
        merged_style = {**default_style}
        if style:
            merged_style.update(style)

        async with db_manager.session() as session:
            overlay = TextOverlay(
                shot_id=shot_uuid,
                scene_id=scene_uuid,
                project_id=project_uuid,
                overlay_type=otype,
                text=text,
                position=pos,
                custom_x=custom_x,
                custom_y=custom_y,
                style=merged_style,
                animation_in=anim_in,
                animation_out=anim_out,
                animation_in_duration_ms=animation_in_duration_ms,
                animation_out_duration_ms=animation_out_duration_ms,
                start_time_ms=start_time_ms,
                duration_ms=duration_ms,
                is_visible=is_visible,
                z_index=z_index,
            )

            session.add(overlay)
            await session.commit()
            await session.refresh(overlay)

            return {"success": True, "overlay": overlay.to_dict()}

    @server.handler("textOverlays.update")
    async def handle_update_text_overlay(
        overlay_id: str,
        text: Optional[str] = None,
        overlay_type: Optional[str] = None,
        position: Optional[str] = None,
        custom_x: Optional[float] = None,
        custom_y: Optional[float] = None,
        style: Optional[Dict[str, Any]] = None,
        animation_in: Optional[str] = None,
        animation_out: Optional[str] = None,
        animation_in_duration_ms: Optional[int] = None,
        animation_out_duration_ms: Optional[int] = None,
        start_time_ms: Optional[int] = None,
        duration_ms: Optional[int] = None,
        is_visible: Optional[bool] = None,
        z_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Update a text overlay."""
        from scenemachine.models.text_overlay import (
            TextOverlay,
            TextOverlayType,
            TextPosition,
            TextAnimation,
        )
        from sqlalchemy import select

        oid = UUID(overlay_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = select(TextOverlay).where(TextOverlay.id == oid)
            result = await session.execute(stmt)
            overlay = result.scalar_one_or_none()

            if not overlay:
                return {"success": False, "error": f"Text overlay {overlay_id} not found"}

            # Update fields
            if text is not None:
                overlay.text = text

            if overlay_type is not None:
                try:
                    overlay.overlay_type = TextOverlayType(overlay_type)
                except ValueError:
                    pass

            if position is not None:
                try:
                    overlay.position = TextPosition(position)
                except ValueError:
                    pass

            if custom_x is not None:
                overlay.custom_x = custom_x

            if custom_y is not None:
                overlay.custom_y = custom_y

            if style is not None:
                current_style = overlay.style or {}
                current_style.update(style)
                overlay.style = current_style

            if animation_in is not None:
                try:
                    overlay.animation_in = TextAnimation(animation_in)
                except ValueError:
                    pass

            if animation_out is not None:
                try:
                    overlay.animation_out = TextAnimation(animation_out)
                except ValueError:
                    pass

            if animation_in_duration_ms is not None:
                overlay.animation_in_duration_ms = animation_in_duration_ms

            if animation_out_duration_ms is not None:
                overlay.animation_out_duration_ms = animation_out_duration_ms

            if start_time_ms is not None:
                overlay.start_time_ms = start_time_ms

            if duration_ms is not None:
                overlay.duration_ms = duration_ms

            if is_visible is not None:
                overlay.is_visible = is_visible

            if z_index is not None:
                overlay.z_index = z_index

            await session.commit()
            await session.refresh(overlay)

            return {"success": True, "overlay": overlay.to_dict()}

    @server.handler("textOverlays.delete")
    async def handle_delete_text_overlay(overlay_id: str) -> Dict[str, bool]:
        """Delete a text overlay."""
        from scenemachine.models.text_overlay import TextOverlay
        from sqlalchemy import delete

        oid = UUID(overlay_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = delete(TextOverlay).where(TextOverlay.id == oid)
            result = await session.execute(stmt)
            await session.commit()

            return {"success": result.rowcount > 0}

    @server.handler("textOverlays.batchUpdateForShot")
    async def handle_batch_update_shot_overlays(
        shot_id: str,
        overlays: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Replace all text overlays for a shot with a new set.

        This is useful for syncing the frontend state with the backend.
        """
        from scenemachine.models.text_overlay import (
            TextOverlay,
            TextOverlayType,
            TextPosition,
            TextAnimation,
            DEFAULT_STYLES,
        )
        from sqlalchemy import delete, select

        sid = UUID(shot_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            # Delete existing overlays
            await session.execute(
                delete(TextOverlay).where(TextOverlay.shot_id == sid)
            )

            # Create new overlays
            new_overlays = []
            for data in overlays:
                # Get overlay type
                try:
                    otype = TextOverlayType(data.get("type", "custom"))
                except ValueError:
                    otype = TextOverlayType.CUSTOM

                # Get position
                try:
                    pos = TextPosition(data.get("position", "center"))
                except ValueError:
                    pos = TextPosition.CENTER

                # Get animations
                try:
                    anim_in = TextAnimation(data.get("animation", {}).get("in", "fade_in"))
                except ValueError:
                    anim_in = TextAnimation.FADE_IN

                try:
                    anim_out = TextAnimation(data.get("animation", {}).get("out", "fade_out"))
                except ValueError:
                    anim_out = TextAnimation.FADE_OUT

                animation = data.get("animation", {})
                timing = data.get("timing", {})

                # Merge style with defaults
                default_style = DEFAULT_STYLES.get(otype, DEFAULT_STYLES[TextOverlayType.CUSTOM])
                merged_style = {**default_style}
                if data.get("style"):
                    merged_style.update(data["style"])

                overlay = TextOverlay(
                    shot_id=sid,
                    overlay_type=otype,
                    text=data.get("text", ""),
                    position=pos,
                    custom_x=data.get("customX"),
                    custom_y=data.get("customY"),
                    style=merged_style,
                    animation_in=anim_in,
                    animation_out=anim_out,
                    animation_in_duration_ms=animation.get("inDuration", 500),
                    animation_out_duration_ms=animation.get("outDuration", 500),
                    start_time_ms=timing.get("startTime", 0),
                    duration_ms=timing.get("duration", 5000),
                    is_visible=data.get("isVisible", True),
                    z_index=data.get("zIndex", 1),
                )
                session.add(overlay)
                new_overlays.append(overlay)

            await session.commit()

            # Refresh to get IDs
            for overlay in new_overlays:
                await session.refresh(overlay)

            return {
                "success": True,
                "overlays": [o.to_dict() for o in new_overlays],
            }

    # =========================================================================
    # GPU Exchange Handlers
    # =========================================================================

    @server.handler("gpuExchange.listProviders")
    async def handle_list_gpu_providers() -> List[Dict[str, Any]]:
        """List all GPU providers."""
        from scenemachine.gpu_exchange.registry import get_provider_registry

        registry = get_provider_registry()
        providers = []

        for provider_id in registry.list_providers_by_priority():
            info = registry.get_provider_info(provider_id)
            if info:
                providers.append(info)

        return providers

    @server.handler("gpuExchange.getProvider")
    async def handle_get_gpu_provider(providerId: str) -> Dict[str, Any]:
        """Get a specific GPU provider."""
        from scenemachine.gpu_exchange.registry import get_provider_registry

        registry = get_provider_registry()
        info = registry.get_provider_info(providerId)

        if not info:
            raise ValueError(f"Provider '{providerId}' not found")

        return info

    @server.handler("gpuExchange.getProviderHealth")
    async def handle_get_gpu_provider_health(providerId: str) -> Dict[str, Any]:
        """Get health status of a GPU provider."""
        from scenemachine.gpu_exchange.registry import get_provider_registry

        registry = get_provider_registry()
        provider = registry.get_provider(providerId)

        if not provider:
            raise ValueError(f"Provider '{providerId}' not found")

        health = await provider.check_health()

        return {
            "provider_id": providerId,
            "available": health.available,
            "message": health.message,
            "latency_ms": health.latency_ms,
            "instances_available": health.instances_available,
            "queue_depth": health.queue_depth,
            "error_code": health.error_code,
            "last_check": health.last_check.isoformat(),
        }

    @server.handler("gpuExchange.getAllProvidersHealth")
    async def handle_get_all_gpu_providers_health() -> Dict[str, Any]:
        """Get health status of all GPU providers."""
        from scenemachine.gpu_exchange.registry import get_provider_registry

        registry = get_provider_registry()
        all_health = await registry.get_all_health()

        providers = {}
        healthy_count = 0

        for provider_id, health in all_health.items():
            if health.available:
                healthy_count += 1

            providers[provider_id] = {
                "provider_id": provider_id,
                "available": health.available,
                "message": health.message,
                "latency_ms": health.latency_ms,
                "instances_available": health.instances_available,
                "queue_depth": health.queue_depth,
                "error_code": health.error_code,
                "last_check": health.last_check.isoformat(),
            }

        return {
            "providers": providers,
            "healthy_count": healthy_count,
            "total_count": len(all_health),
        }

    @server.handler("gpuExchange.getProvidersForGPU")
    async def handle_get_providers_for_gpu(gpuType: str) -> List[str]:
        """Get providers that support a specific GPU type."""
        from scenemachine.gpu_exchange.base import GPUType
        from scenemachine.gpu_exchange.registry import get_provider_registry

        try:
            gpu = GPUType(gpuType)
        except ValueError:
            raise ValueError(f"Invalid GPU type: {gpuType}")

        registry = get_provider_registry()
        return registry.get_providers_for_gpu(gpu)

    @server.handler("gpuExchange.getPricing")
    async def handle_get_gpu_pricing(
        providerId: str,
        gpuType: str,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get pricing for a GPU type from a provider."""
        from scenemachine.gpu_exchange.base import GPUType
        from scenemachine.gpu_exchange.pricing import get_pricing_service

        try:
            gpu = GPUType(gpuType)
        except ValueError:
            raise ValueError(f"Invalid GPU type: {gpuType}")

        pricing_service = get_pricing_service()
        pricing = await pricing_service.get_pricing(
            providerId, gpu, region or "us-east-1"
        )

        if not pricing:
            raise ValueError(f"Pricing not available for {providerId}/{gpuType}")

        return {
            "gpu_type": gpuType,
            "price_per_hour": pricing.price_per_hour,
            "price_per_second": pricing.price_per_second,
            "spot_price_per_hour": pricing.spot_price_per_hour,
            "reserved_price_per_hour": pricing.reserved_price_per_hour,
            "currency": pricing.currency,
            "region": pricing.region,
            "availability": pricing.availability,
            "last_updated": pricing.last_updated.isoformat(),
        }

    @server.handler("gpuExchange.comparePricing")
    async def handle_compare_gpu_pricing(
        gpuType: str,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare pricing across providers for a GPU type."""
        from scenemachine.gpu_exchange.base import GPUType
        from scenemachine.gpu_exchange.pricing import get_pricing_service

        try:
            gpu = GPUType(gpuType)
        except ValueError:
            raise ValueError(f"Invalid GPU type: {gpuType}")

        pricing_service = get_pricing_service()
        comparison = await pricing_service.compare_pricing(gpu, region or "us-east-1")

        return {
            "gpu_type": gpuType,
            "region": comparison.region,
            "cheapest_provider": comparison.cheapest_provider,
            "cheapest_price": comparison.cheapest_price,
            "fastest_provider": comparison.fastest_provider,
            "best_value_provider": comparison.best_value_provider,
            "all_options": comparison.all_options,
            "generated_at": comparison.generated_at.isoformat(),
        }

    @server.handler("gpuExchange.getAllPricing")
    async def handle_get_all_gpu_pricing(
        gpuType: str,
        region: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Get pricing from all providers for a GPU type."""
        from scenemachine.gpu_exchange.base import GPUType
        from scenemachine.gpu_exchange.pricing import get_pricing_service

        try:
            gpu = GPUType(gpuType)
        except ValueError:
            raise ValueError(f"Invalid GPU type: {gpuType}")

        pricing_service = get_pricing_service()
        all_pricing = await pricing_service.get_all_pricing(gpu, region or "us-east-1")

        result = {}
        for provider_id, pricing in all_pricing.items():
            result[provider_id] = {
                "gpu_type": gpuType,
                "price_per_hour": pricing.price_per_hour,
                "price_per_second": pricing.price_per_second,
                "spot_price_per_hour": pricing.spot_price_per_hour,
                "reserved_price_per_hour": pricing.reserved_price_per_hour,
                "currency": pricing.currency,
                "region": pricing.region,
                "availability": pricing.availability,
                "last_updated": pricing.last_updated.isoformat(),
            }

        return result

    @server.handler("gpuExchange.estimateCost")
    async def handle_estimate_gpu_cost(
        gpuType: str,
        durationSeconds: float,
        providerId: Optional[str] = None,
        useSpot: bool = False,
    ) -> Dict[str, Any]:
        """Estimate cost for GPU usage."""
        from scenemachine.gpu_exchange.base import GPUType
        from scenemachine.gpu_exchange.pricing import get_pricing_service, PricingTier

        try:
            gpu = GPUType(gpuType)
        except ValueError:
            raise ValueError(f"Invalid GPU type: {gpuType}")

        pricing_service = get_pricing_service()

        if providerId:
            pricing = await pricing_service.get_pricing(providerId, gpu)
            if not pricing:
                raise ValueError(f"Pricing not available for {providerId}")

            if useSpot and pricing.spot_price_per_hour:
                price_per_hour = pricing.spot_price_per_hour
            else:
                price_per_hour = pricing.price_per_hour

            estimated_cost = (price_per_hour / 3600) * durationSeconds

            return {
                "provider_id": providerId,
                "gpu_type": gpuType,
                "duration_seconds": durationSeconds,
                "use_spot": useSpot and pricing.spot_price_per_hour is not None,
                "estimated_cost_usd": round(estimated_cost, 4),
                "price_per_hour": price_per_hour,
                "currency": "USD",
            }
        else:
            tier = PricingTier.BUDGET if useSpot else PricingTier.STANDARD
            result = await pricing_service.get_optimal_provider(
                gpu, durationSeconds, tier=tier
            )

            if not result:
                raise ValueError(f"No providers available for {gpuType}")

            provider_id, pricing = result

            if useSpot and pricing.spot_price_per_hour:
                price_per_hour = pricing.spot_price_per_hour
            else:
                price_per_hour = pricing.price_per_hour

            estimated_cost = (price_per_hour / 3600) * durationSeconds

            return {
                "provider_id": provider_id,
                "gpu_type": gpuType,
                "duration_seconds": durationSeconds,
                "use_spot": useSpot and pricing.spot_price_per_hour is not None,
                "estimated_cost_usd": round(estimated_cost, 4),
                "price_per_hour": price_per_hour,
                "currency": "USD",
            }

    @server.handler("gpuExchange.selectProvider")
    async def handle_select_gpu_provider(
        gpuType: str,
        durationSeconds: float,
        config: Optional[Dict[str, Any]] = None,
        requiredCapability: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Select optimal provider for a job."""
        from scenemachine.gpu_exchange.base import GPUType, ProviderCapability
        from scenemachine.gpu_exchange.router import (
            RoutingConfig,
            RoutingPriority,
            get_gpu_exchange,
        )

        try:
            gpu = GPUType(gpuType)
        except ValueError:
            raise ValueError(f"Invalid GPU type: {gpuType}")

        capability = ProviderCapability.VIDEO_GENERATION
        if requiredCapability:
            try:
                capability = ProviderCapability(requiredCapability)
            except ValueError:
                raise ValueError(f"Invalid capability: {requiredCapability}")

        # Build routing config
        routing_config = RoutingConfig()
        if config:
            if "priority" in config:
                try:
                    routing_config.priority = RoutingPriority(config["priority"])
                except ValueError:
                    pass

            if "max_price_usd" in config:
                routing_config.max_price_usd = config["max_price_usd"]
            if "preferred_providers" in config:
                routing_config.preferred_providers = config["preferred_providers"]
            if "excluded_providers" in config:
                routing_config.excluded_providers = config["excluded_providers"]
            if "preferred_regions" in config:
                routing_config.preferred_regions = config["preferred_regions"]
            if "allow_spot" in config:
                routing_config.allow_spot = config["allow_spot"]

        exchange = get_gpu_exchange()
        selection = await exchange.select_provider(
            gpu, durationSeconds, routing_config, capability
        )

        if not selection:
            raise ValueError("No suitable provider found")

        return {
            "provider_id": selection.provider_id,
            "provider_name": selection.provider.name,
            "price_per_hour": selection.pricing.price_per_hour,
            "estimated_cost": round(selection.estimated_cost, 4),
            "use_spot": selection.use_spot,
            "fallback_providers": selection.fallback_providers,
            "score_breakdown": {
                "total": selection.score.total_score,
                "cost": selection.score.cost_score,
                "latency": selection.score.latency_score,
                "reliability": selection.score.reliability_score,
                "queue": selection.score.queue_score,
            },
        }

    @server.handler("gpuExchange.getRoutingStats")
    async def handle_get_gpu_routing_stats() -> Dict[str, Any]:
        """Get routing statistics."""
        from scenemachine.gpu_exchange.router import get_gpu_exchange

        exchange = get_gpu_exchange()
        stats = exchange.get_routing_stats()

        return stats

    @server.handler("gpuExchange.setBudgetLimit")
    async def handle_set_gpu_budget_limit(
        projectId: str,
        limitUsd: float,
    ) -> Dict[str, str]:
        """Set a budget limit for a project."""
        from scenemachine.gpu_exchange.pricing import get_pricing_service

        pricing_service = get_pricing_service()
        pricing_service.set_budget_limit(projectId, limitUsd)

        return {"status": "success"}

    @server.handler("gpuExchange.checkBudget")
    async def handle_check_gpu_budget(
        projectId: str,
        estimatedCost: float,
        currentSpent: float = 0.0,
    ) -> Dict[str, Any]:
        """Check if a job would exceed budget."""
        from scenemachine.gpu_exchange.pricing import get_pricing_service

        pricing_service = get_pricing_service()
        allowed, warning = pricing_service.check_budget(
            projectId, estimatedCost, currentSpent
        )

        return {"allowed": allowed, "warning": warning}

    @server.handler("gpuExchange.listGPUTypes")
    async def handle_list_gpu_types() -> List[Dict[str, str]]:
        """List all GPU types."""
        from scenemachine.gpu_exchange.base import GPUType

        return [
            {"id": gpu.value, "name": gpu.name.replace("_", " ")}
            for gpu in GPUType
        ]

    @server.handler("gpuExchange.listCapabilities")
    async def handle_list_gpu_capabilities() -> List[Dict[str, str]]:
        """List all GPU capabilities."""
        from scenemachine.gpu_exchange.base import ProviderCapability

        return [
            {"id": cap.value, "name": cap.name.replace("_", " ").title()}
            for cap in ProviderCapability
        ]

    @server.handler("gpuExchange.listPricingTiers")
    async def handle_list_gpu_pricing_tiers() -> List[Dict[str, str]]:
        """List all pricing tiers."""
        from scenemachine.gpu_exchange.pricing import PricingTier

        descriptions = {
            "budget": "Cheapest available, may use spot instances",
            "standard": "Balanced price and reliability",
            "premium": "Fastest, most reliable",
            "reserved": "Reserved capacity discount",
        }

        return [
            {
                "id": tier.value,
                "name": tier.name.title(),
                "description": descriptions.get(tier.value, ""),
            }
            for tier in PricingTier
        ]

    # =========================================================================
    # Co-pilot (Steven) Handlers
    # =========================================================================

    @server.handler("copilot.chat")
    async def handle_copilot_chat(
        projectId: str,
        message: str,
        context: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Send a chat message to the co-pilot."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from scenemachine.services.llm import get_llm_service

        llm_service = get_llm_service()
        db_manager = get_db_manager()

        # Build project context from database
        project_context: Dict[str, Any] = {}

        try:
            project_id = UUID(projectId)
            async with db_manager.session() as session:
                stmt = (
                    select(Project)
                    .options(
                        selectinload(Project.screenplay),
                        selectinload(Project.scenes),
                    )
                    .where(Project.id == project_id)
                )
                result = await session.execute(stmt)
                project = result.scalar_one_or_none()

                if project:
                    project_context["project_name"] = project.name
                    if project.screenplay:
                        project_context["screenplay_title"] = project.screenplay.title

                    # Add current scene context if provided
                    if context and context.get("sceneId"):
                        for scene in project.scenes:
                            if str(scene.id) == context["sceneId"]:
                                project_context["current_scene"] = {
                                    "heading": scene.heading,
                                    "description": scene.description or "",
                                }
                                break

                    # Add current shot context if provided
                    if context and context.get("shotId"):
                        project_context["current_shot"] = {
                            "id": context["shotId"],
                        }
        except Exception as e:
            logger.warning(f"Failed to load project context: {e}")

        # Get conversation history from context if provided
        conversation_history = None
        if context and context.get("conversationHistory"):
            try:
                import json
                conversation_history = json.loads(context["conversationHistory"])
            except (json.JSONDecodeError, TypeError):
                pass

        # Call LLM service
        result = await llm_service.chat(
            message=message,
            project_context=project_context,
            conversation_history=conversation_history,
        )

        return result

    @server.handler("copilot.analyze")
    async def handle_copilot_analyze(projectId: str) -> Dict[str, Any]:
        """Analyze a project with the co-pilot."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from scenemachine.services.llm import get_llm_service

        llm_service = get_llm_service()
        db_manager = get_db_manager()

        # Load project data
        project_context: Dict[str, Any] = {"id": projectId}
        scenes: List[Dict[str, Any]] = []
        characters: List[Dict[str, Any]] = []

        try:
            project_id = UUID(projectId)
            async with db_manager.session() as session:
                stmt = (
                    select(Project)
                    .options(
                        selectinload(Project.screenplay),
                        selectinload(Project.scenes),
                        selectinload(Project.characters),
                    )
                    .where(Project.id == project_id)
                )
                result = await session.execute(stmt)
                project = result.scalar_one_or_none()

                if project:
                    project_context["name"] = project.name
                    project_context["genre"] = project.genre.value if project.genre else "Unknown"

                    # Extract scenes
                    for scene in project.scenes:
                        scenes.append({
                            "sequence": scene.sequence,
                            "heading": scene.heading,
                            "description": scene.description or "",
                        })

                    # Extract characters
                    for char in project.characters:
                        characters.append({
                            "name": char.name,
                            "description": char.description or "",
                        })
        except Exception as e:
            logger.warning(f"Failed to load project data for analysis: {e}")

        # Call LLM service for analysis
        result = await llm_service.analyze_project(
            project_context=project_context,
            scenes=scenes,
            characters=characters,
        )

        return result

    @server.handler("copilot.suggestScene")
    async def handle_copilot_suggest_scene(
        projectId: str,
        sceneId: str,
    ) -> List[Dict[str, Any]]:
        """Get suggestions for a scene."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from scenemachine.models import Scene
        from scenemachine.services.llm import get_llm_service

        llm_service = get_llm_service()
        db_manager = get_db_manager()

        # Load scene data
        scene_data: Dict[str, Any] = {}
        characters: List[Dict[str, Any]] = []
        adjacent_scenes: Optional[Dict[str, Any]] = None

        try:
            scene_uuid = UUID(sceneId)
            async with db_manager.session() as session:
                stmt = (
                    select(Scene)
                    .options(selectinload(Scene.shots))
                    .where(Scene.id == scene_uuid)
                )
                result = await session.execute(stmt)
                scene = result.scalar_one_or_none()

                if scene:
                    scene_data = {
                        "heading": scene.heading,
                        "description": scene.description or "",
                        "mood": scene.mood.value if scene.mood else "Unknown",
                        "shots": [
                            {"description": s.description or ""}
                            for s in scene.shots[:10]
                        ],
                    }

                    # Get adjacent scenes
                    project_id = scene.project_id
                    seq = scene.sequence

                    # Previous scene
                    prev_stmt = (
                        select(Scene)
                        .where(Scene.project_id == project_id, Scene.sequence == seq - 1)
                    )
                    prev_result = await session.execute(prev_stmt)
                    prev_scene = prev_result.scalar_one_or_none()

                    # Next scene
                    next_stmt = (
                        select(Scene)
                        .where(Scene.project_id == project_id, Scene.sequence == seq + 1)
                    )
                    next_result = await session.execute(next_stmt)
                    next_scene = next_result.scalar_one_or_none()

                    if prev_scene or next_scene:
                        adjacent_scenes = {}
                        if prev_scene:
                            adjacent_scenes["previous"] = {"heading": prev_scene.heading}
                        if next_scene:
                            adjacent_scenes["next"] = {"heading": next_scene.heading}

                    # Load characters in scene (from project)
                    project_stmt = (
                        select(Project)
                        .options(selectinload(Project.characters))
                        .where(Project.id == project_id)
                    )
                    proj_result = await session.execute(project_stmt)
                    project = proj_result.scalar_one_or_none()
                    if project:
                        characters = [
                            {"name": c.name}
                            for c in project.characters[:10]
                        ]
        except Exception as e:
            logger.warning(f"Failed to load scene data: {e}")

        # Call LLM service
        result = await llm_service.suggest_scene(
            scene=scene_data,
            characters=characters,
            adjacent_scenes=adjacent_scenes,
        )

        return result

    @server.handler("copilot.suggestShot")
    async def handle_copilot_suggest_shot(
        projectId: str,
        shotId: str,
    ) -> List[Dict[str, Any]]:
        """Get suggestions for a shot."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from scenemachine.models import Scene, Shot
        from scenemachine.services.llm import get_llm_service

        llm_service = get_llm_service()
        db_manager = get_db_manager()

        # Load shot data
        shot_data: Dict[str, Any] = {}
        scene_context: Dict[str, Any] = {}
        adjacent_shots: Optional[Dict[str, Any]] = None

        try:
            shot_uuid = UUID(shotId)
            async with db_manager.session() as session:
                stmt = select(Shot).where(Shot.id == shot_uuid)
                result = await session.execute(stmt)
                shot = result.scalar_one_or_none()

                if shot:
                    shot_data = {
                        "shot_type": shot.shot_type.value if shot.shot_type else "Unknown",
                        "camera_movement": shot.camera_movement.value if shot.camera_movement else "None",
                        "description": shot.description or "",
                        "generation_prompt": shot.generation_prompt or "",
                    }

                    # Load scene context
                    scene_stmt = select(Scene).where(Scene.id == shot.scene_id)
                    scene_result = await session.execute(scene_stmt)
                    scene = scene_result.scalar_one_or_none()

                    if scene:
                        scene_context = {
                            "heading": scene.heading,
                            "mood": scene.mood.value if scene.mood else "Unknown",
                        }

                    # Get adjacent shots
                    seq = shot.sequence

                    prev_stmt = (
                        select(Shot)
                        .where(Shot.scene_id == shot.scene_id, Shot.sequence == seq - 1)
                    )
                    prev_result = await session.execute(prev_stmt)
                    prev_shot = prev_result.scalar_one_or_none()

                    next_stmt = (
                        select(Shot)
                        .where(Shot.scene_id == shot.scene_id, Shot.sequence == seq + 1)
                    )
                    next_result = await session.execute(next_stmt)
                    next_shot = next_result.scalar_one_or_none()

                    if prev_shot or next_shot:
                        adjacent_shots = {}
                        if prev_shot:
                            adjacent_shots["previous"] = {"description": prev_shot.description or ""}
                        if next_shot:
                            adjacent_shots["next"] = {"description": next_shot.description or ""}

        except Exception as e:
            logger.warning(f"Failed to load shot data: {e}")

        # Call LLM service
        result = await llm_service.suggest_shot(
            shot=shot_data,
            scene_context=scene_context,
            adjacent_shots=adjacent_shots,
        )

        return result

    @server.handler("copilot.applySuggestion")
    async def handle_copilot_apply_suggestion(
        projectId: str,
        suggestionId: str,
        suggestionData: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Apply a co-pilot suggestion.

        Suggestions are applied based on their type:
        - scene: Updates scene properties
        - shot: Updates shot properties
        - dialogue: Updates dialogue text
        - pacing: May reorder or trim scenes
        - visual: Updates visual settings
        """
        # For now, log the suggestion application and return success
        # Full implementation would modify the database based on suggestion type
        logger.info(f"Applying suggestion {suggestionId} to project {projectId}")

        changes: Dict[str, Any] = {}

        if suggestionData:
            suggestion_type = suggestionData.get("type", "")
            changes["type"] = suggestion_type
            changes["applied"] = True

            # Log what would be applied
            if suggestion_type == "scene":
                changes["action"] = "scene_modified"
            elif suggestion_type == "shot":
                changes["action"] = "shot_modified"
            elif suggestion_type == "dialogue":
                changes["action"] = "dialogue_updated"
            elif suggestion_type == "pacing":
                changes["action"] = "pacing_adjusted"
            elif suggestion_type == "visual":
                changes["action"] = "visual_settings_updated"

        return {"success": True, "changes": changes}

    @server.handler("copilot.dismissSuggestion")
    async def handle_copilot_dismiss_suggestion(
        projectId: str,
        suggestionId: str,
    ) -> Dict[str, bool]:
        """Dismiss a co-pilot suggestion."""
        return {"success": True}

    @server.handler("copilot.getQuickActions")
    async def handle_copilot_quick_actions(
        projectId: str,
        sceneId: Optional[str] = None,
        shotId: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Get quick actions for current context."""
        actions = [
            {"id": "analyze", "label": "Analyze Project", "action": "analyze_project"},
            {"id": "improve_pacing", "label": "Improve Pacing", "action": "suggest_pacing"},
        ]

        if sceneId:
            actions.extend([
                {"id": "scene_suggest", "label": "Suggest Improvements", "action": "suggest_scene"},
                {"id": "scene_visualize", "label": "Visualize Scene", "action": "visualize_scene"},
            ])

        if shotId:
            actions.extend([
                {"id": "shot_suggest", "label": "Suggest Shot Changes", "action": "suggest_shot"},
                {"id": "shot_regenerate", "label": "Regenerate Prompt", "action": "regenerate_prompt"},
            ])

        return actions

    @server.handler("copilot.enhancePrompt")
    async def handle_copilot_enhance_prompt(
        projectId: str,
        shotId: str,
        originalPrompt: str,
    ) -> Dict[str, str]:
        """Enhance a video generation prompt using AI."""
        from sqlalchemy import select

        from scenemachine.models import Scene, Shot
        from scenemachine.services.llm import get_llm_service

        llm_service = get_llm_service()
        db_manager = get_db_manager()

        # Load shot context
        shot_context: Dict[str, Any] = {}

        try:
            shot_uuid = UUID(shotId)
            async with db_manager.session() as session:
                stmt = select(Shot).where(Shot.id == shot_uuid)
                result = await session.execute(stmt)
                shot = result.scalar_one_or_none()

                if shot:
                    shot_context = {
                        "shot_type": shot.shot_type.value if shot.shot_type else "Unknown",
                        "camera_movement": shot.camera_movement.value if shot.camera_movement else "Static",
                    }

                    # Load scene for mood
                    scene_stmt = select(Scene).where(Scene.id == shot.scene_id)
                    scene_result = await session.execute(scene_stmt)
                    scene = scene_result.scalar_one_or_none()

                    if scene:
                        shot_context["mood"] = scene.mood.value if scene.mood else "neutral"

        except Exception as e:
            logger.warning(f"Failed to load shot context for prompt enhancement: {e}")

        # Enhance prompt
        enhanced = await llm_service.enhance_prompt(
            original_prompt=originalPrompt,
            shot_context=shot_context,
        )

        return {"enhancedPrompt": enhanced}

    @server.handler("copilot.generateShotBreakdown")
    async def handle_copilot_generate_shot_breakdown(
        projectId: str,
        sceneId: str,
    ) -> Dict[str, Any]:
        """Generate a shot breakdown for a scene using AI."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from scenemachine.models import Scene
        from scenemachine.services.llm import get_llm_service

        llm_service = get_llm_service()
        db_manager = get_db_manager()

        # Load scene data
        scene_data: Dict[str, Any] = {}
        characters: List[Dict[str, Any]] = []

        try:
            scene_uuid = UUID(sceneId)
            async with db_manager.session() as session:
                stmt = select(Scene).where(Scene.id == scene_uuid)
                result = await session.execute(stmt)
                scene = result.scalar_one_or_none()

                if scene:
                    scene_data = {
                        "heading": scene.heading,
                        "description": scene.description or "",
                        "mood": scene.mood.value if scene.mood else "Unknown",
                        "content": scene.content or "",
                    }

                    # Load project characters
                    project_stmt = (
                        select(Project)
                        .options(selectinload(Project.characters))
                        .where(Project.id == scene.project_id)
                    )
                    proj_result = await session.execute(project_stmt)
                    project = proj_result.scalar_one_or_none()

                    if project:
                        characters = [
                            {"name": c.name}
                            for c in project.characters[:10]
                        ]

        except Exception as e:
            logger.warning(f"Failed to load scene data for shot breakdown: {e}")

        # Generate breakdown
        breakdown = await llm_service.generate_shot_breakdown(
            scene=scene_data,
            characters=characters,
        )

        return breakdown

    # ==========================================================================
    # PERFORMER HANDLERS (ActForge)
    # ==========================================================================

    @server.handler("performers.search")
    async def handle_search_performers(
        query: Optional[str] = None,
        performer_type: Optional[str] = None,
        min_aci: Optional[float] = None,
        max_aci: Optional[float] = None,
        specialties: Optional[List[str]] = None,
        availability: Optional[str] = None,
        verification: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "aci_score",
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """Search performers with filters."""
        from sqlalchemy import select, func, or_
        from sqlalchemy.orm import selectinload
        from scenemachine.models import Performer, PerformerType as PT, PerformerAvailability, PerformerVerification

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            stmt = select(Performer).options(selectinload(Performer.ratings))

            # Apply filters
            if query:
                search = f"%{query}%"
                stmt = stmt.where(
                    or_(
                        Performer.stage_name.ilike(search),
                        Performer.bio.ilike(search),
                    )
                )

            if performer_type:
                try:
                    pt = PT(performer_type)
                    stmt = stmt.where(Performer.performer_type == pt)
                except ValueError:
                    pass

            if min_aci is not None:
                stmt = stmt.where(Performer.aci_score >= min_aci)

            if max_aci is not None:
                stmt = stmt.where(Performer.aci_score <= max_aci)

            if availability:
                try:
                    av = PerformerAvailability(availability)
                    stmt = stmt.where(Performer.availability_status == av)
                except ValueError:
                    pass

            if verification:
                try:
                    vf = PerformerVerification(verification)
                    stmt = stmt.where(Performer.verification_status == vf)
                except ValueError:
                    pass

            # Count total
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total_result = await session.execute(count_stmt)
            total = total_result.scalar() or 0

            # Apply sorting
            sort_column = getattr(Performer, sort_by, Performer.aci_score)
            if sort_order == "asc":
                stmt = stmt.order_by(sort_column.asc())
            else:
                stmt = stmt.order_by(sort_column.desc())

            # Apply pagination
            stmt = stmt.offset(offset).limit(limit)

            result = await session.execute(stmt)
            performers = result.scalars().all()

            return {
                "performers": [_performer_to_dict(p) for p in performers],
                "total": total,
                "hasMore": offset + len(performers) < total,
            }

    @server.handler("performers.featured")
    async def handle_featured_performers(limit: int = 6) -> List[Dict[str, Any]]:
        """Get featured performers (highest ACI scores)."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from scenemachine.models import Performer, PerformerAvailability

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            stmt = (
                select(Performer)
                .options(selectinload(Performer.ratings))
                .where(Performer.availability_status == PerformerAvailability.AVAILABLE)
                .order_by(Performer.aci_score.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            performers = result.scalars().all()

            return [_performer_to_dict(p) for p in performers]

    @server.handler("performers.leaderboard")
    async def handle_performer_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
        """Get performer leaderboard by ACI score."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from scenemachine.models import Performer

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            stmt = (
                select(Performer)
                .options(selectinload(Performer.ratings))
                .order_by(Performer.aci_score.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            performers = result.scalars().all()

            return [
                {
                    "rank": idx + 1,
                    "performer_id": str(p.id),
                    "stage_name": p.stage_name,
                    "aci_score": p.aci_score,
                    "completed_bookings": p.completed_bookings,
                    "average_rating": p.average_rating or 4.5,
                    "avatar_url": p.profile_image_path,
                }
                for idx, p in enumerate(performers)
            ]

    @server.handler("performers.get")
    async def handle_get_performer(id: str) -> Dict[str, Any]:
        """Get performer details by ID."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from scenemachine.models import Performer

        performer_id = UUID(id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = (
                select(Performer)
                .options(selectinload(Performer.ratings))
                .where(Performer.id == performer_id)
            )
            result = await session.execute(stmt)
            performer = result.scalar_one_or_none()

            if not performer:
                raise ValueError(f"Performer {id} not found")

            return _performer_to_dict(performer)

    @server.handler("performers.getACI")
    async def handle_get_performer_aci(performerId: str) -> Dict[str, Any]:
        """Get ACI breakdown for a performer."""
        from sqlalchemy import select
        from scenemachine.models import Performer

        performer_id = UUID(performerId)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = select(Performer).where(Performer.id == performer_id)
            result = await session.execute(stmt)
            performer = result.scalar_one_or_none()

            if not performer:
                raise ValueError(f"Performer {performerId} not found")

            # Calculate ACI breakdown components
            # These are approximate breakdowns based on the score
            base_score = performer.aci_score
            return {
                "overall": base_score,
                "consistency": min(100, base_score + 2),  # Slightly higher for good performers
                "versatility": max(50, base_score - 5),  # Range of styles
                "delivery_speed": max(60, base_score - 3),  # On-time delivery
                "client_satisfaction": min(100, base_score + 1),  # Reviews
            }

    @server.handler("performers.seed")
    async def handle_seed_performers() -> Dict[str, Any]:
        """Seed the database with sample performers (admin action)."""
        from scenemachine.seeds.performers import seed_performers

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            performers = await seed_performers(session)
            await session.commit()
            count = len(performers)

        return {
            "success": True,
            "message": f"Seeded {count} performers",
            "count": count,
        }

    def _performer_to_dict(performer: Any) -> Dict[str, Any]:
        """Convert performer model to dictionary for frontend consumption."""
        pricing = performer.pricing or {}
        motion = performer.motion_capabilities or {}

        # Calculate completion rate
        completion_rate = (
            performer.completed_bookings / performer.total_bookings
            if performer.total_bookings > 0
            else 1.0
        )

        # Determine verification status as boolean
        is_verified = performer.verification_status.value in ("verified", "elite")

        # Determine availability
        is_available = performer.availability_status.value == "available"

        return {
            "id": str(performer.id),
            "stage_name": performer.stage_name,
            "bio": performer.bio,
            "specialties": performer.specialties or [],
            "aci_score": performer.aci_score,
            "performer_type": performer.performer_type.value.upper(),  # HUMAN or SYNTHETIC
            "is_verified": is_verified,
            "is_available": is_available,
            "is_featured": performer.aci_score >= 85,  # Featured if high ACI
            "total_bookings": performer.total_bookings,
            "completed_bookings": performer.completed_bookings,
            "completion_rate": completion_rate,
            "lifetime_earnings_usd": performer.lifetime_earnings_usd,
            "average_rating": performer.average_rating or 4.5,  # Default rating
            "rating": performer.average_rating or 4.5,  # Alias for frontend
            "total_ratings": performer.completed_bookings,  # Approximate
            "revenue_tier": _get_revenue_tier(performer.lifetime_earnings_usd),
            "revenue_split_percent": performer.revenue_split_percent,
            # Pricing fields - extract from pricing dict
            "pricing_blink_usd": pricing.get("blink", 5.0),
            "pricing_deep_usd": pricing.get("deep", 25.0),
            "pricing_epic_usd": pricing.get("epic_per_minute", 10.0),
            "base_price_usd": pricing.get("blink", 5.0),  # Alias for frontend
            # Motion capabilities
            "motion_capabilities": {
                "live_portrait": motion.get("supports_liveportrait", True),
                "roop_gs_anim": motion.get("supports_roop_gs_anim", False),
                "emotion_range": motion.get("emotion_range", ["neutral", "happy", "sad"]),
                "body_types": motion.get("body_types", ["standard"]),
            },
            # URLs
            "avatar_url": performer.profile_image_path,
            "profile_image_url": performer.profile_image_path,  # Alias
            "demo_video_url": None,  # Not stored in model
            "demo_reel_url": None,  # Alias
            # Delivery estimate
            "avg_delivery_hours": 24,  # Default
            # Timestamps
            "created_at": performer.created_at.isoformat() if performer.created_at else None,
            "updated_at": performer.updated_at.isoformat() if performer.updated_at else None,
        }

    def _get_revenue_tier(lifetime_earnings: float) -> int:
        """Get revenue tier based on lifetime earnings."""
        if lifetime_earnings >= 10_000_000:
            return 6
        elif lifetime_earnings >= 1_000_000:
            return 5
        elif lifetime_earnings >= 100_000:
            return 4
        elif lifetime_earnings >= 10_000:
            return 3
        elif lifetime_earnings >= 1_000:
            return 2
        else:
            return 1

    # ==========================================================================
    # BOOKING HANDLERS (ActForge)
    # ==========================================================================

    @server.handler("bookings.blink")
    async def handle_blink_booking(
        project_id: str,
        performer_id: Optional[str] = None,
        shot_id: Optional[str] = None,
        duration_seconds: int = 10,
        special_instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Blink (quick auto-match) booking."""
        return await _create_booking(
            project_id=project_id,
            performer_id=performer_id,
            shot_id=shot_id,
            booking_mode="blink",
            duration_seconds=duration_seconds,
            special_instructions=special_instructions,
        )

    @server.handler("bookings.deep")
    async def handle_deep_booking(
        project_id: str,
        performer_id: str,
        shot_id: Optional[str] = None,
        duration_seconds: int = 120,
        emotion_markers: Optional[List[str]] = None,
        special_instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Deep (method acting) booking."""
        return await _create_booking(
            project_id=project_id,
            performer_id=performer_id,
            shot_id=shot_id,
            booking_mode="deep",
            duration_seconds=duration_seconds,
            emotion_markers=emotion_markers,
            special_instructions=special_instructions,
        )

    @server.handler("bookings.epic")
    async def handle_epic_booking(
        project_id: str,
        performer_id: str,
        shot_id: Optional[str] = None,
        duration_seconds: int = 300,
        emotion_markers: Optional[List[str]] = None,
        special_instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create an Epic (extended performance) booking."""
        return await _create_booking(
            project_id=project_id,
            performer_id=performer_id,
            shot_id=shot_id,
            booking_mode="epic",
            duration_seconds=duration_seconds,
            emotion_markers=emotion_markers,
            special_instructions=special_instructions,
        )

    @server.handler("bookings.get")
    async def handle_get_booking(id: str) -> Dict[str, Any]:
        """Get booking by ID."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from scenemachine.models import Booking

        booking_id = UUID(id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = (
                select(Booking)
                .options(
                    selectinload(Booking.performer),
                    selectinload(Booking.rating),
                )
                .where(Booking.id == booking_id)
            )
            result = await session.execute(stmt)
            booking = result.scalar_one_or_none()

            if not booking:
                raise ValueError(f"Booking {id} not found")

            return _booking_to_dict(
                booking,
                performer_name=booking.performer.stage_name if booking.performer else None,
                rating_score=booking.rating.overall_score if booking.rating else None,
                rating_review=booking.rating.review_text if booking.rating else None,
            )

    @server.handler("bookings.listByProject")
    async def handle_list_project_bookings(
        projectId: str,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List bookings for a project."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from scenemachine.models import Booking, BookingStatus

        project_id = UUID(projectId)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = (
                select(Booking)
                .options(
                    selectinload(Booking.performer),
                    selectinload(Booking.rating),
                )
                .where(Booking.project_id == project_id)
                .order_by(Booking.created_at.desc())
            )

            if status:
                try:
                    bs = BookingStatus(status.lower())
                    stmt = stmt.where(Booking.status == bs)
                except ValueError:
                    pass

            result = await session.execute(stmt)
            bookings = result.scalars().all()

            return [
                _booking_to_dict(
                    b,
                    performer_name=b.performer.stage_name if b.performer else None,
                    rating_score=b.rating.overall_score if b.rating else None,
                    rating_review=b.rating.review_text if b.rating else None,
                )
                for b in bookings
            ]

    @server.handler("bookings.accept")
    async def handle_accept_booking(bookingId: str) -> Dict[str, Any]:
        """Accept a booking (performer action)."""
        from datetime import datetime, timezone
        from sqlalchemy import select
        from scenemachine.models import Booking, BookingStatus

        booking_id = UUID(bookingId)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = select(Booking).where(Booking.id == booking_id)
            result = await session.execute(stmt)
            booking = result.scalar_one_or_none()

            if not booking:
                raise ValueError(f"Booking {bookingId} not found")

            if not booking.can_transition_to(BookingStatus.ACCEPTED):
                raise ValueError(f"Cannot accept booking in {booking.status.value} status")

            booking.status = BookingStatus.ACCEPTED
            booking.accepted_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(booking)

            return _booking_to_dict(booking)

    @server.handler("bookings.deliver")
    async def handle_deliver_booking(
        bookingId: str,
        deliveryUrl: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mark a booking as delivered (performer action)."""
        from datetime import datetime, timezone
        from sqlalchemy import select
        from scenemachine.models import Booking, BookingStatus

        booking_id = UUID(bookingId)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = select(Booking).where(Booking.id == booking_id)
            result = await session.execute(stmt)
            booking = result.scalar_one_or_none()

            if not booking:
                raise ValueError(f"Booking {bookingId} not found")

            if not booking.can_transition_to(BookingStatus.DELIVERED):
                raise ValueError(f"Cannot deliver booking in {booking.status.value} status")

            booking.status = BookingStatus.DELIVERED
            booking.delivered_at = datetime.now(timezone.utc)
            booking.performer_notes = notes

            await session.commit()
            await session.refresh(booking)

            return _booking_to_dict(booking)

    @server.handler("bookings.approve")
    async def handle_approve_booking(bookingId: str) -> Dict[str, Any]:
        """Approve a delivered booking (director action)."""
        from datetime import datetime, timezone
        from sqlalchemy import select
        from scenemachine.models import Booking, BookingStatus, PaymentStatus

        booking_id = UUID(bookingId)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = select(Booking).where(Booking.id == booking_id)
            result = await session.execute(stmt)
            booking = result.scalar_one_or_none()

            if not booking:
                raise ValueError(f"Booking {bookingId} not found")

            if not booking.can_transition_to(BookingStatus.APPROVED):
                raise ValueError(f"Cannot approve booking in {booking.status.value} status")

            booking.status = BookingStatus.APPROVED
            booking.approved_at = datetime.now(timezone.utc)

            # Transition to completed and release payment
            if booking.can_transition_to(BookingStatus.COMPLETED):
                booking.status = BookingStatus.COMPLETED
                booking.completed_at = datetime.now(timezone.utc)
                booking.payment_status = PaymentStatus.RELEASED
                booking.released_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(booking)

            return _booking_to_dict(booking)

    @server.handler("bookings.dispute")
    async def handle_dispute_booking(bookingId: str, reason: str) -> Dict[str, Any]:
        """Dispute a delivered booking (director action)."""
        from datetime import datetime, timezone
        from sqlalchemy import select
        from scenemachine.models import Booking, BookingStatus

        booking_id = UUID(bookingId)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = select(Booking).where(Booking.id == booking_id)
            result = await session.execute(stmt)
            booking = result.scalar_one_or_none()

            if not booking:
                raise ValueError(f"Booking {bookingId} not found")

            if not booking.can_transition_to(BookingStatus.DISPUTED):
                raise ValueError(f"Cannot dispute booking in {booking.status.value} status")

            booking.status = BookingStatus.DISPUTED
            booking.is_disputed = True
            booking.dispute_reason = reason
            booking.disputed_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(booking)

            return _booking_to_dict(booking)

    @server.handler("bookings.rate")
    async def handle_rate_booking(
        bookingId: str,
        rating: int,
        review: Optional[str] = None,
        wouldRehire: bool = True,
    ) -> Dict[str, Any]:
        """Rate a completed booking (director action)."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from scenemachine.models import Booking, PerformerRating

        booking_id = UUID(bookingId)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            stmt = (
                select(Booking)
                .options(
                    selectinload(Booking.performer),
                    selectinload(Booking.rating),
                )
                .where(Booking.id == booking_id)
            )
            result = await session.execute(stmt)
            booking = result.scalar_one_or_none()

            if not booking:
                raise ValueError(f"Booking {bookingId} not found")

            if not booking.performer_id:
                raise ValueError("Booking has no performer to rate")

            # Create or update rating
            from datetime import datetime, timezone

            existing_rating = booking.rating
            if existing_rating:
                existing_rating.overall_score = rating
                existing_rating.review_text = review
                existing_rating.would_rehire = wouldRehire
            else:
                new_rating = PerformerRating(
                    performer_id=booking.performer_id,
                    booking_id=booking.id,
                    rater_user_id=booking.requester_user_id,
                    overall_score=rating,
                    review_text=review,
                    would_rehire=wouldRehire,
                    rated_at=datetime.now(timezone.utc),
                )
                session.add(new_rating)

            await session.commit()

            # Get performer name for response
            performer_name = booking.performer.stage_name if booking.performer else None

            # Return with the rating values we just set
            return _booking_to_dict(
                booking,
                performer_name=performer_name,
                rating_score=rating,  # Use the input value
                rating_review=review,  # Use the input value
            )

    async def _create_booking(
        project_id: str,
        booking_mode: str,
        duration_seconds: int,
        performer_id: Optional[str] = None,
        shot_id: Optional[str] = None,
        emotion_markers: Optional[List[str]] = None,
        special_instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new booking."""
        from datetime import datetime, timezone
        from sqlalchemy import select
        from scenemachine.models import Booking, BookingMode, BookingStatus, Performer

        db_manager = get_db_manager()

        async with db_manager.session() as session:
            # Get performer if specified
            performer = None
            price_usd = 5.0  # Default base price
            if performer_id:
                stmt = select(Performer).where(Performer.id == UUID(performer_id))
                result = await session.execute(stmt)
                performer = result.scalar_one_or_none()
                if performer and performer.pricing:
                    if booking_mode == "blink":
                        price_usd = performer.pricing.get("blink", 5.0)
                    elif booking_mode == "deep":
                        price_usd = performer.pricing.get("deep", 25.0)
                    elif booking_mode == "epic":
                        price_usd = performer.pricing.get("epic_per_minute", 10.0) * (duration_seconds / 60)

            # Calculate duration-based pricing
            if booking_mode == "blink":
                # Blink is fixed 10s
                final_price = price_usd
            else:
                # Scale price by duration
                final_price = price_usd * (duration_seconds / 10)

            # Create booking
            booking = Booking(
                project_id=UUID(project_id),
                shot_id=UUID(shot_id) if shot_id else None,
                performer_id=UUID(performer_id) if performer_id else None,
                requester_user_id=UUID("00000000-0000-0000-0000-000000000001"),  # Placeholder
                booking_mode=BookingMode(booking_mode),
                status=BookingStatus.MATCHING if not performer_id else BookingStatus.MATCHED,
                duration_requested_seconds=duration_seconds,
                emotion_requirements=emotion_markers,
                special_instructions=special_instructions,
                price_usd=final_price,
                requested_at=datetime.now(timezone.utc),
            )

            session.add(booking)
            await session.commit()
            await session.refresh(booking)

            return _booking_to_dict(booking)

    def _booking_to_dict(
        booking: Any,
        performer_name: Optional[str] = None,
        rating_score: Optional[int] = None,
        rating_review: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convert booking to dictionary.

        Args:
            booking: The booking model instance
            performer_name: Pre-loaded performer stage name (to avoid lazy loading)
            rating_score: Pre-loaded rating score (to avoid lazy loading)
            rating_review: Pre-loaded rating review (to avoid lazy loading)
        """
        # Try to get performer name if not provided (may trigger lazy load)
        if performer_name is None:
            try:
                from sqlalchemy.orm import object_session
                from sqlalchemy.orm.attributes import instance_state

                state = instance_state(booking)
                if "performer" in state.dict:
                    performer_name = booking.performer.stage_name if booking.performer else None
            except Exception:
                pass

        # Try to get rating if not provided (may trigger lazy load)
        if rating_score is None:
            try:
                from sqlalchemy.orm.attributes import instance_state

                state = instance_state(booking)
                if "rating" in state.dict:
                    rating_score = booking.rating.overall_score if booking.rating else None
                    rating_review = booking.rating.review_text if booking.rating else None
            except Exception:
                pass

        return {
            "id": str(booking.id),
            "project_id": str(booking.project_id),
            "shot_id": str(booking.shot_id) if booking.shot_id else None,
            "performer_id": str(booking.performer_id) if booking.performer_id else None,
            "performer_stage_name": performer_name,
            "booking_mode": booking.booking_mode.value.upper(),
            "status": booking.status.value.upper(),
            "price_usd": booking.price_usd,
            "platform_fee_usd": booking.platform_fee_usd,
            "performer_payout_usd": booking.performer_payout_usd,
            "payment_status": booking.payment_status.value.upper(),
            "requirements": {
                "duration_seconds": booking.duration_requested_seconds,
                "emotion_markers": booking.emotion_requirements or [],
                "special_instructions": booking.special_instructions,
                "reference_images": [],
            },
            "delivery_url": None,  # Would come from take
            "delivery_notes": booking.performer_notes,
            "rating": rating_score,
            "review": rating_review,
            "created_at": booking.created_at.isoformat() if booking.created_at else None,
            "updated_at": booking.updated_at.isoformat() if booking.updated_at else None,
            "accepted_at": booking.accepted_at.isoformat() if booking.accepted_at else None,
            "delivered_at": booking.delivered_at.isoformat() if booking.delivered_at else None,
        }

    # ==========================================================================
    # SNAPSHOT HANDLERS
    # ==========================================================================

    @server.handler("snapshots.compare")
    async def handle_compare_snapshots(
        snapshot_id_a: str,
        snapshot_id_b: str,
    ) -> Dict[str, Any]:
        """Compare two snapshots and return delta report."""
        from scenemachine.services.snapshots import SnapshotService

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            service = SnapshotService(session)
            report = await service.compare_snapshots(
                UUID(snapshot_id_a),
                UUID(snapshot_id_b),
            )
            return {
                "snapshot_a": snapshot_id_a,
                "snapshot_b": snapshot_id_b,
                "total_changes": report.total_changes,
                "changes": [
                    {
                        "field": c.field,
                        "old_value": c.old_value,
                        "new_value": c.new_value,
                        "change_type": c.change_type,
                    }
                    for c in report.changes
                ],
            }

    logger.info(f"Registered {len(server.handlers)} IPC handlers")
