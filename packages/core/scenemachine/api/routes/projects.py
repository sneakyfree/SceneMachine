"""Project API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scenemachine.api.dependencies import get_db
from scenemachine.auth.dependencies import OptionalUser
from scenemachine.models import Project
from scenemachine.schemas import (
    ProjectCreate,
    ProjectDetail,
    ProjectSummary,
    ProjectUpdate,
    SuccessResponse,
)
from scenemachine.services.project_duplicator import duplicate_project

router = APIRouter()


def _owner_id_of(current_user):
    """The UUID to record as a row's owner, or None for an anonymous caller."""
    return current_user.id if current_user is not None else None


async def _get_owned_project_or_403(db, project_id, current_user):
    """Load a project and enforce ownership.

    - 404 if it doesn't exist.
    - 403 if it HAS an owner and the caller is a *different* authenticated user.
    - Allowed if unowned (legacy/desktop), the caller is unauthenticated
      (desktop/IPC back-compat), or the caller is the owner.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    if (
        project.owner_id is not None
        and current_user is not None
        and project.owner_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this project",
        )
    return project


@router.get("", response_model=list[ProjectSummary])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> list[ProjectSummary]:
    """List all projects.

    Returns a paginated list of projects with summary information.
    """
    stmt = (
        select(Project)
        .options(
            selectinload(Project.screenplay),
            selectinload(Project.characters),
            selectinload(Project.scenes),
        )
        .offset(skip)
        .limit(limit)
        .order_by(Project.updated_at.desc())
    )
    result = await db.execute(stmt)
    projects = result.scalars().all()

    return [
        ProjectSummary(
            id=p.id,
            name=p.name,
            description=p.description,
            state=p.state,
            screenplay_title=p.screenplay.title if p.screenplay else None,
            character_count=p.character_count,
            scene_count=p.scene_count,
            locked_character_count=p.locked_character_count,
            approved_scene_count=p.approved_scene_count,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in projects
    ]


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: OptionalUser = None,
) -> ProjectDetail:
    """Create a new project.

    Creates a new project in the EMPTY state, ready for screenplay upload.
    When the request is authenticated, the project is owned by that user so
    other authenticated users can't later delete it (see delete_project).
    """
    project = Project(
        name=project_in.name,
        description=project_in.description,
        settings=project_in.settings or {},
        owner_id=_owner_id_of(current_user),
    )

    db.add(project)
    await db.commit()
    await db.refresh(project)

    # For newly created project, can_advance is False (no screenplay)
    # Avoid accessing relationships which would trigger lazy loads
    return ProjectDetail(
        id=project.id,
        name=project.name,
        description=project.description,
        state=project.state,
        settings=project.settings,
        can_advance=False,  # New projects can't advance without screenplay
        screenplay=None,
        characters=[],
        scenes=[],
        character_count=0,
        scene_count=0,
        locked_character_count=0,
        approved_scene_count=0,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ProjectDetail:
    """Get project details.

    Returns full project information including relationships.
    """
    stmt = (
        select(Project)
        .options(
            selectinload(Project.screenplay),
            selectinload(Project.characters),
            selectinload(Project.scenes),
        )
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # Build response with nested data
    from scenemachine.schemas import (
        CharacterSummaryBrief,
        SceneSummaryBrief,
        ScreenplaySummary,
    )

    screenplay_summary = None
    if project.screenplay:
        screenplay_summary = ScreenplaySummary(
            id=project.screenplay.id,
            title=project.screenplay.title,
            original_filename=project.screenplay.original_filename,
            is_parsed=project.screenplay.is_parsed,
            movie_plan_approved=project.screenplay.movie_plan_approved,
            page_count=project.screenplay.page_count,
        )

    character_summaries = [
        CharacterSummaryBrief(
            id=c.id,
            name=c.name,
            screenplay_name=c.screenplay_name,
            is_locked=c.is_locked,
            is_protagonist=c.is_protagonist,
        )
        for c in project.characters
    ]

    scene_summaries = [
        SceneSummaryBrief(
            id=s.id,
            scene_number=s.scene_number,
            heading=s.heading,
            shot_breakdown_approved=s.shot_breakdown_approved,
        )
        for s in project.scenes
    ]

    return ProjectDetail(
        id=project.id,
        name=project.name,
        description=project.description,
        state=project.state,
        settings=project.settings,
        can_advance=project.can_advance,
        screenplay=screenplay_summary,
        characters=character_summaries,
        scenes=scene_summaries,
        character_count=project.character_count,
        scene_count=project.scene_count,
        locked_character_count=project.locked_character_count,
        approved_scene_count=project.approved_scene_count,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.patch("/{project_id}", response_model=ProjectDetail)
async def update_project(
    project_id: UUID,
    project_in: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProjectDetail:
    """Update project details.

    Updates project name, description, or settings.
    """
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # Update fields if provided
    if project_in.name is not None:
        project.name = project_in.name
    if project_in.description is not None:
        project.description = project_in.description
    if project_in.settings is not None:
        project.settings = {**project.settings, **project_in.settings}

    await db.commit()
    await db.refresh(project)

    # Return updated project (simplified - would need full load for complete detail)
    return await get_project(project_id, db)


@router.delete("/{project_id}", response_model=SuccessResponse)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: OptionalUser = None,
) -> SuccessResponse:
    """Delete a project.

    Permanently deletes the project and all associated data.
    This action cannot be undone. A project owned by one authenticated user
    cannot be deleted by a *different* authenticated user (403); unowned and
    unauthenticated (desktop/IPC) calls stay allowed for back-compat.
    """
    project = await _get_owned_project_or_403(db, project_id, current_user)

    await db.delete(project)
    await db.commit()

    return SuccessResponse(
        success=True,
        message=f"Project {project_id} deleted successfully",
    )


from pydantic import BaseModel


class ProjectDuplicateRequest(BaseModel):
    """Request to duplicate a project."""

    new_name: str | None = None
    include_generated_videos: bool = False


@router.post(
    "/{project_id}/duplicate", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED
)
async def duplicate_project_endpoint(
    project_id: UUID,
    request: ProjectDuplicateRequest,
    db: AsyncSession = Depends(get_db),
) -> ProjectDetail:
    """Duplicate a project.

    Creates a complete copy of the project including all characters,
    scenes, and shots. Generated videos are not copied by default.
    """
    try:
        new_project = await duplicate_project(
            session=db,
            project_id=project_id,
            new_name=request.new_name,
            include_generated_videos=request.include_generated_videos,
        )
        await db.commit()
        await db.refresh(new_project)

        # Return the new project details
        return await get_project(new_project.id, db)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to duplicate project: {str(e)}",
        )
