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
        watermark: bool = False,
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

        settings = ExportSettings(
            format=ExportFormat(format),
            quality=ExportQuality(quality),
            resolution=resolution,
            frame_rate=frame_rate,
            include_audio=include_audio,
            include_subtitles=include_subtitles,
            watermark=watermark,
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
    async def handle_generate_dialogue(shot_id: str) -> Dict[str, Any]:
        """Generate dialogue audio for a shot."""
        from scenemachine.services.audio import AudioService

        sid = UUID(shot_id)
        db_manager = get_db_manager()

        async with db_manager.session() as session:
            service = AudioService(session)
            await service.initialize_providers()

            result = await service.generate_dialogue(sid)

            return {
                "success": result.success,
                "audioPath": result.audio_path,
                "durationSeconds": result.duration_seconds,
                "errorMessage": result.error_message,
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

    @server.handler("analytics.getGenerationStats")
    async def handle_generation_stats(
        time_range: str = "7d",
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get generation statistics."""
        from scenemachine.services.analytics import AnalyticsService

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            service = AnalyticsService(session)
            pid = UUID(project_id) if project_id else None
            stats = await service.get_generation_stats(time_range, pid)

            return {
                "totalJobs": stats.total_jobs,
                "completedJobs": stats.completed_jobs,
                "failedJobs": stats.failed_jobs,
                "pendingJobs": stats.pending_jobs,
                "successRate": round(stats.success_rate, 2),
                "avgGenerationTimeSeconds": round(stats.avg_generation_time_seconds, 2),
            }

    @server.handler("analytics.getCostStats")
    async def handle_cost_stats(
        time_range: str = "7d",
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get cost statistics."""
        from scenemachine.services.analytics import AnalyticsService

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            service = AnalyticsService(session)
            pid = UUID(project_id) if project_id else None
            stats = await service.get_cost_stats(time_range, pid)

            return {
                "totalCostUsd": round(stats.total_cost_usd, 4),
                "costByProvider": {k: round(v, 4) for k, v in stats.cost_by_provider.items()},
                "avgCostPerShot": round(stats.avg_cost_per_shot, 4),
            }

    @server.handler("analytics.getDailyStats")
    async def handle_daily_stats(
        days: int = 7,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get daily generation statistics."""
        from scenemachine.services.analytics import AnalyticsService

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            service = AnalyticsService(session)
            pid = UUID(project_id) if project_id else None
            stats = await service.get_daily_stats(days, pid)

            return [
                {
                    "date": item["date"],
                    "totalJobs": item["total_jobs"],
                    "completedJobs": item["completed_jobs"],
                    "failedJobs": item["failed_jobs"],
                    "successRate": round(item["success_rate"], 2),
                    "totalCostUsd": round(item["total_cost_usd"], 4),
                }
                for item in stats
            ]

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

    @server.handler("sharing.getProjectShares")
    async def handle_get_project_shares(
        project_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all shares for a project."""
        from scenemachine.services.sharing import SharingService

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            service = SharingService(session)
            shares = await service.get_project_shares(UUID(project_id))

            return [
                {
                    "id": share.id,
                    "projectId": share.project_id,
                    "shareCode": share.share_code,
                    "permission": share.permission,
                    "status": share.status,
                    "recipientEmail": share.recipient_email,
                    "isPublic": share.is_public,
                    "expiresAt": share.expires_at,
                    "createdAt": share.created_at,
                    "accessCount": share.access_count,
                }
                for share in shares
            ]

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

    @server.handler("sharing.getComments")
    async def handle_get_comments(
        project_id: str,
        shot_id: Optional[str] = None,
        include_resolved: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get comments for a project."""
        from scenemachine.services.sharing import SharingService

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            service = SharingService(session)
            comments = await service.get_project_comments(
                project_id=UUID(project_id),
                shot_id=UUID(shot_id) if shot_id else None,
                include_resolved=include_resolved,
            )
            return comments

    @server.handler("sharing.addComment")
    async def handle_add_comment(
        project_id: str,
        author_name: str,
        content: str,
        shot_id: Optional[str] = None,
        author_email: Optional[str] = None,
        parent_id: Optional[str] = None,
        timecode_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Add a comment."""
        from scenemachine.services.sharing import SharingService

        db_manager = get_db_manager()
        async with db_manager.session() as session:
            service = SharingService(session)
            comment = await service.add_comment(
                project_id=UUID(project_id),
                author_name=author_name,
                content=content,
                shot_id=UUID(shot_id) if shot_id else None,
                author_email=author_email,
                parent_id=UUID(parent_id) if parent_id else None,
                timecode_seconds=timecode_seconds,
            )

            if not comment:
                raise ValueError("Failed to add comment")

            return {
                "id": str(comment.id),
                "projectId": str(comment.project_id),
                "authorName": comment.author_name,
                "content": comment.content,
                "createdAt": comment.created_at.isoformat(),
            }

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

    logger.info(f"Registered {len(server.handlers)} IPC handlers")
