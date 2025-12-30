"""Movie Plan API routes."""

import logging
from typing import Annotated, Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.database import get_session
from scenemachine.services.movie_plan import MoviePlanService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/movie-plans", tags=["movie-plans"])


class MoviePlanResponse(BaseModel):
    """Movie plan response schema."""

    screenplay_id: str
    generated_at: str
    ai_model: str
    title: str
    logline: str
    genre: str
    tone: str
    themes: list[str]
    estimated_runtime_minutes: int
    visual_style: Dict[str, Any]
    color_palette: list[str]
    cinematography_notes: str
    characters: list[Dict[str, Any]]
    protagonist: Optional[str]
    antagonist: Optional[str]
    scenes: list[Dict[str, Any]]
    act_structure: Dict[str, list[str]]
    location_requirements: list[Dict[str, Any]]
    prop_requirements: list[str]
    special_effects_notes: list[str]
    generation_notes: list[str]
    warnings: list[str]


class GenerateRequest(BaseModel):
    """Request to generate a movie plan."""

    regenerate: bool = False


class ApproveResponse(BaseModel):
    """Response for plan approval."""

    success: bool
    message: str


@router.post(
    "/generate/{screenplay_id}",
    response_model=MoviePlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_movie_plan(
    screenplay_id: UUID,
    request: GenerateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MoviePlanResponse:
    """Generate a movie plan for a screenplay.

    Analyzes the screenplay and creates a comprehensive production plan
    including character analysis, scene breakdowns, and visual style suggestions.
    """
    service = MoviePlanService(session)

    try:
        plan = await service.generate_movie_plan(
            screenplay_id=screenplay_id,
            regenerate=request.regenerate,
        )

        return MoviePlanResponse(
            screenplay_id=plan.screenplay_id,
            generated_at=plan.generated_at,
            ai_model=plan.ai_model,
            title=plan.title,
            logline=plan.logline,
            genre=plan.genre,
            tone=plan.tone,
            themes=plan.themes,
            estimated_runtime_minutes=plan.estimated_runtime_minutes,
            visual_style=plan.visual_style,
            color_palette=plan.color_palette,
            cinematography_notes=plan.cinematography_notes,
            characters=plan.characters,
            protagonist=plan.protagonist,
            antagonist=plan.antagonist,
            scenes=plan.scenes,
            act_structure=plan.act_structure,
            location_requirements=plan.location_requirements,
            prop_requirements=plan.prop_requirements,
            special_effects_notes=plan.special_effects_notes,
            generation_notes=plan.generation_notes,
            warnings=plan.warnings,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception(f"Failed to generate movie plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate movie plan",
        ) from e


@router.get(
    "/{screenplay_id}",
    response_model=MoviePlanResponse | None,
)
async def get_movie_plan(
    screenplay_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MoviePlanResponse | None:
    """Get the movie plan for a screenplay."""
    service = MoviePlanService(session)

    plan = await service.get_movie_plan(screenplay_id)

    if not plan:
        return None

    return MoviePlanResponse(
        screenplay_id=plan.screenplay_id,
        generated_at=plan.generated_at,
        ai_model=plan.ai_model,
        title=plan.title,
        logline=plan.logline,
        genre=plan.genre,
        tone=plan.tone,
        themes=plan.themes,
        estimated_runtime_minutes=plan.estimated_runtime_minutes,
        visual_style=plan.visual_style,
        color_palette=plan.color_palette,
        cinematography_notes=plan.cinematography_notes,
        characters=plan.characters,
        protagonist=plan.protagonist,
        antagonist=plan.antagonist,
        scenes=plan.scenes,
        act_structure=plan.act_structure,
        location_requirements=plan.location_requirements,
        prop_requirements=plan.prop_requirements,
        special_effects_notes=plan.special_effects_notes,
        generation_notes=plan.generation_notes,
        warnings=plan.warnings,
    )


@router.post(
    "/{screenplay_id}/approve",
    response_model=ApproveResponse,
)
async def approve_movie_plan(
    screenplay_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApproveResponse:
    """Approve the movie plan to proceed to character design."""
    service = MoviePlanService(session)

    try:
        await service.approve_movie_plan(screenplay_id)
        return ApproveResponse(
            success=True,
            message="Movie plan approved. You can now proceed to Character Lab.",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception(f"Failed to approve movie plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve movie plan",
        ) from e
