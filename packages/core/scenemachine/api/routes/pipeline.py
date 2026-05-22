"""Pipeline API routes for agentic screenplay processing.

Implements the DNA strand master plan's agentic crew endpoints.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from scenemachine.workflows.agentic_crew import Orchestrator, create_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

# Store orchestrators by project (in production, use Redis/database)
_orchestrators: dict[str, Orchestrator] = {}


# --- Request/Response Models ---


class StartPipelineRequest(BaseModel):
    """Request to start the screenplay-to-movie pipeline."""

    project_id: str = Field(..., description="Unique project identifier")
    screenplay_path: str = Field(..., description="Path to screenplay file")
    file_format: str = Field(..., description="File format: fountain, pdf, fdx")
    settings: dict[str, Any] | None = Field(None, description="Generation settings")


class StartPipelineResponse(BaseModel):
    """Response from starting pipeline."""

    success: bool
    project_id: str
    stage: str
    message: str | None = None
    summary: dict[str, Any] | None = None
    blockers: dict[str, Any] | None = None
    pending_approvals: list[dict[str, Any]] | None = None


class ApproveActionRequest(BaseModel):
    """Request to approve a pending action."""

    project_id: str
    action_id: str
    approver_id: str


class ApproveActionResponse(BaseModel):
    """Response from action approval."""

    success: bool
    message: str


class RejectActionRequest(BaseModel):
    """Request to reject a pending action."""

    project_id: str
    action_id: str
    approver_id: str
    reason: str = ""


class PipelineStatusResponse(BaseModel):
    """Current pipeline status."""

    project_id: str
    context: dict[str, Any]
    agents: dict[str, Any]
    pending_approvals: int
    action_count: int


# --- Endpoints ---


@router.post("/start", response_model=StartPipelineResponse)
async def start_pipeline(request: StartPipelineRequest):
    """Start the screenplay-to-movie pipeline.

    This initiates the agentic crew processing:
    1. Parse screenplay
    2. Extract characters
    3. Generate shot list
    4. Analyze blockers
    5. Return status with any blockers or approval requests
    """
    try:
        # Create or get orchestrator for this project
        orchestrator = create_orchestrator()
        orchestrator.context.project_id = request.project_id

        if request.settings:
            orchestrator.context.settings = request.settings

        _orchestrators[request.project_id] = orchestrator

        # Run the pipeline
        result = await orchestrator.run_pipeline(
            screenplay_path=request.screenplay_path,
            file_format=request.file_format,
        )

        return StartPipelineResponse(
            success=result.get("success", False),
            project_id=request.project_id,
            stage=result.get("stage", "unknown"),
            message=result.get("message"),
            summary=result.get("summary"),
            blockers=result.get("blockers"),
            pending_approvals=result.get("pending_approvals"),
        )

    except Exception as e:
        logger.exception(f"Pipeline error for project {request.project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{project_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(project_id: str):
    """Get current status of a pipeline."""
    orchestrator = _orchestrators.get(project_id)

    if not orchestrator:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {project_id}")

    status = orchestrator.get_status()

    return PipelineStatusResponse(
        project_id=project_id,
        context=status.get("context", {}),
        agents=status.get("agents", {}),
        pending_approvals=status.get("pending_approvals", 0),
        action_count=status.get("action_count", 0),
    )


@router.get("/actions/{project_id}")
async def get_action_log(project_id: str):
    """Get the action log for a pipeline."""
    orchestrator = _orchestrators.get(project_id)

    if not orchestrator:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {project_id}")

    return {
        "project_id": project_id,
        "actions": orchestrator.get_action_log(),
    }


@router.post("/approve", response_model=ApproveActionResponse)
async def approve_action(request: ApproveActionRequest):
    """Approve a pending action.

    Required for:
    - High-cost generations (>$10)
    - Using real person likeness
    - Final export
    - Quality escalations
    """
    orchestrator = _orchestrators.get(request.project_id)

    if not orchestrator:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {request.project_id}")

    success = orchestrator.approve_action(
        action_id=request.action_id,
        approver_id=request.approver_id,
    )

    if not success:
        raise HTTPException(status_code=404, detail=f"Action not found: {request.action_id}")

    return ApproveActionResponse(
        success=True,
        message=f"Action {request.action_id} approved",
    )


@router.post("/reject", response_model=ApproveActionResponse)
async def reject_action(request: RejectActionRequest):
    """Reject a pending action."""
    orchestrator = _orchestrators.get(request.project_id)

    if not orchestrator:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {request.project_id}")

    success = orchestrator.reject_action(
        action_id=request.action_id,
        approver_id=request.approver_id,
        reason=request.reason,
    )

    if not success:
        raise HTTPException(status_code=404, detail=f"Action not found: {request.action_id}")

    return ApproveActionResponse(
        success=True,
        message=f"Action {request.action_id} rejected: {request.reason}",
    )


@router.get("/pending-approvals/{project_id}")
async def get_pending_approvals(project_id: str):
    """Get all pending approvals for a project."""
    orchestrator = _orchestrators.get(project_id)

    if not orchestrator:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {project_id}")

    pending = orchestrator.context.get_pending_approvals()

    return {
        "project_id": project_id,
        "pending_approvals": [a.to_dict() for a in pending],
        "count": len(pending),
    }


@router.delete("/{project_id}")
async def delete_pipeline(project_id: str):
    """Delete a pipeline and free resources."""
    if project_id in _orchestrators:
        del _orchestrators[project_id]
        return {"success": True, "message": f"Pipeline {project_id} deleted"}

    raise HTTPException(status_code=404, detail=f"Pipeline not found: {project_id}")
