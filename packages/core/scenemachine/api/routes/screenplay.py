"""Screenplay API routes."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.auth.dependencies import OptionalUser
from scenemachine.database import get_session
from scenemachine.models import Character, Project, Scene, Screenplay
from scenemachine.schemas.screenplay import (
    ScreenplayDetail,
    ScreenplayResponse,
    ScreenplaySummary,
)
from scenemachine.services.screenplay import ScreenplayService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/screenplays", tags=["screenplays"])


@router.post(
    "/upload/{project_id}",
    response_model=ScreenplayResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_screenplay(
    project_id: UUID,
    file: Annotated[UploadFile, File(description="Screenplay file")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScreenplayResponse:
    """Upload a screenplay file.

    Supports:
    - .fountain / .spmd (Fountain format)
    - .pdf (PDF, including scanned documents)
    - .fdx (Final Draft XML)
    - .txt (Plain text, parsed as Fountain)
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    service = ScreenplayService(session)

    try:
        screenplay = await service.upload_screenplay(
            project_id=project_id,
            file=file.file,
            filename=file.filename,
        )

        return ScreenplayResponse(
            id=screenplay.id,
            project_id=screenplay.project_id,
            original_filename=screenplay.original_filename,
            original_format=screenplay.original_format,
            is_parsed=screenplay.is_parsed,
            parse_errors=screenplay.parse_errors,
            created_at=screenplay.created_at,
            updated_at=screenplay.updated_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception(f"Failed to upload screenplay: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload screenplay",
        ) from e


@router.post(
    "/{screenplay_id}/parse",
    response_model=ScreenplayResponse,
)
async def parse_screenplay(
    screenplay_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScreenplayResponse:
    """Parse an uploaded screenplay.

    Extracts:
    - Characters
    - Scenes
    - Dialogue
    - Action lines
    """
    service = ScreenplayService(session)

    try:
        screenplay = await service.parse_screenplay(screenplay_id)

        return ScreenplayResponse(
            id=screenplay.id,
            project_id=screenplay.project_id,
            original_filename=screenplay.original_filename,
            original_format=screenplay.original_format,
            is_parsed=screenplay.is_parsed,
            parse_errors=screenplay.parse_errors,
            created_at=screenplay.created_at,
            updated_at=screenplay.updated_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception(f"Failed to parse screenplay: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse screenplay",
        ) from e


@router.get(
    "/{screenplay_id}",
    response_model=ScreenplayDetail,
)
async def get_screenplay(
    screenplay_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScreenplayDetail:
    """Get screenplay details including parsed content."""
    stmt = select(Screenplay).where(Screenplay.id == screenplay_id)
    result = await session.execute(stmt)
    screenplay = result.scalar_one_or_none()

    if not screenplay:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screenplay {screenplay_id} not found",
        )

    # Get associated characters and scenes
    chars_stmt = select(Character).where(Character.project_id == screenplay.project_id)
    chars_result = await session.execute(chars_stmt)
    characters = chars_result.scalars().all()

    scenes_stmt = (
        select(Scene)
        .where(Scene.project_id == screenplay.project_id)
        .order_by(Scene.sequence_number)
    )
    scenes_result = await session.execute(scenes_stmt)
    scenes = scenes_result.scalars().all()

    return ScreenplayDetail(
        id=screenplay.id,
        project_id=screenplay.project_id,
        original_filename=screenplay.original_filename,
        original_format=screenplay.original_format,
        is_parsed=screenplay.is_parsed,
        parse_errors=screenplay.parse_errors,
        parsed_content=screenplay.parsed_content,
        character_count=len(characters),
        scene_count=len(scenes),
        characters=[
            {
                "id": str(c.id),
                "name": c.name,
                "dialogue_count": c.dialogue_count,
                "scene_count": c.scene_count,
            }
            for c in characters
        ],
        scenes=[
            {
                "id": str(s.id),
                "scene_number": s.scene_number,
                "sequence_number": s.sequence_number,
                "scene_type": s.scene_type.value,
                "location": s.location,
                "time_of_day": s.time_of_day.value,
            }
            for s in scenes
        ],
        created_at=screenplay.created_at,
        updated_at=screenplay.updated_at,
    )


@router.get(
    "/project/{project_id}",
    response_model=ScreenplaySummary | None,
)
async def get_project_screenplay(
    project_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScreenplaySummary | None:
    """Get screenplay for a project."""
    stmt = select(Screenplay).where(Screenplay.project_id == project_id)
    result = await session.execute(stmt)
    screenplay = result.scalar_one_or_none()

    if not screenplay:
        return None

    return ScreenplaySummary(
        id=screenplay.id,
        project_id=screenplay.project_id,
        original_filename=screenplay.original_filename,
        original_format=screenplay.original_format,
        is_parsed=screenplay.is_parsed,
        created_at=screenplay.created_at,
    )


@router.delete(
    "/{screenplay_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_screenplay(
    screenplay_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: OptionalUser = None,
) -> None:
    """Delete a screenplay and all associated data.

    A screenplay inherits its parent project's owner: a *different*
    authenticated user can't delete it (403). Unowned projects and
    unauthenticated (desktop/IPC) callers stay allowed for back-compat.
    """
    sp = (
        await session.execute(select(Screenplay).where(Screenplay.id == screenplay_id))
    ).scalar_one_or_none()
    if sp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screenplay {screenplay_id} not found",
        )
    project = (
        await session.execute(select(Project).where(Project.id == sp.project_id))
    ).scalar_one_or_none()
    if (
        project is not None
        and project.owner_id is not None
        and current_user is not None
        and project.owner_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this screenplay",
        )

    service = ScreenplayService(session)
    deleted = await service.delete_screenplay(screenplay_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Screenplay {screenplay_id} not found",
        )
