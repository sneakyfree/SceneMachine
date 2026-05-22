"""
Crew API Routes - Agentic pipeline execution.

Provides endpoints for:
- Running the full screenplay-to-movie pipeline
- Getting pipeline status
- Controlling pipeline execution (pause/resume/cancel)
- Viewing action logs
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from scenemachine.agents import (
    ActionContext,
    AgentActionLogger,
    AgentType,
    AssemblerAgent,
    CharacterAgent,
    GeneratorAgent,
    OrchestratorAgent,
    ParserAgent,
    ReviewerAgent,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/crew", tags=["crew"])


# Request/Response models
class PipelineStartRequest(BaseModel):
    project_id: str
    screenplay_path: str | None = None
    phases: list[str] | None = None
    dry_run: bool = False


class PipelineStatusResponse(BaseModel):
    project_id: str
    status: str
    current_phase: str
    progress_percent: float
    total_cost_usd: float
    errors: list[str]


class ActionLogResponse(BaseModel):
    id: str
    agent_type: str
    agent_name: str
    action_name: str
    status: str
    confidence: float
    cost_usd: float
    started_at: str
    completed_at: str | None


# Global orchestrator instance
_orchestrator: OrchestratorAgent | None = None


def get_orchestrator() -> OrchestratorAgent:
    """Get or create the orchestrator instance."""
    global _orchestrator

    if _orchestrator is None:
        _orchestrator = OrchestratorAgent(name="Director")

        # Register specialist agents
        _orchestrator.register_agent(ParserAgent(name="Parser"))
        _orchestrator.register_agent(CharacterAgent(name="Character"))
        _orchestrator.register_agent(GeneratorAgent(name="Generator"))
        _orchestrator.register_agent(AssemblerAgent(name="Assembler"))
        _orchestrator.register_agent(ReviewerAgent(name="Reviewer"))

        logger.info("Orchestrator initialized with 5 specialist agents")

    return _orchestrator


@router.post("/pipeline/start")
async def start_pipeline(request: PipelineStartRequest) -> dict[str, Any]:
    """Start the screenplay-to-movie pipeline."""
    orchestrator = get_orchestrator()

    context = ActionContext(
        project_id=UUID(request.project_id),
        dry_run=request.dry_run,
    )

    result = await orchestrator.execute(
        "run_pipeline",
        context,
        screenplay_path=request.screenplay_path or "",
        phases=request.phases,
    )

    return {
        "success": result.success,
        "status": result.status.value,
        "output": result.output,
        "cost_usd": result.cost_usd,
    }


@router.get("/pipeline/status/{project_id}")
async def get_pipeline_status(project_id: str) -> PipelineStatusResponse:
    """Get the current pipeline status."""
    orchestrator = get_orchestrator()

    context = ActionContext(project_id=UUID(project_id))
    result = await orchestrator.execute("get_status", context)

    output = result.output or {}

    return PipelineStatusResponse(
        project_id=output.get("project_id", project_id),
        status=output.get("status", "idle"),
        current_phase=output.get("current_phase", "none"),
        progress_percent=output.get("progress_percent", 0),
        total_cost_usd=output.get("total_cost_usd", 0),
        errors=output.get("errors", []),
    )


@router.post("/pipeline/pause/{project_id}")
async def pause_pipeline(project_id: str) -> dict[str, str]:
    """Pause the running pipeline."""
    orchestrator = get_orchestrator()
    context = ActionContext(project_id=UUID(project_id))
    result = await orchestrator.execute("pause_pipeline", context)
    return {"message": result.output.get("message", "Paused")}


@router.post("/pipeline/resume/{project_id}")
async def resume_pipeline(project_id: str) -> dict[str, str]:
    """Resume a paused pipeline."""
    orchestrator = get_orchestrator()
    context = ActionContext(project_id=UUID(project_id))
    result = await orchestrator.execute("resume_pipeline", context)
    return {"message": result.output.get("message", "Resumed")}


@router.post("/pipeline/cancel/{project_id}")
async def cancel_pipeline(project_id: str) -> dict[str, str]:
    """Cancel the running pipeline."""
    orchestrator = get_orchestrator()
    context = ActionContext(project_id=UUID(project_id))
    result = await orchestrator.execute("cancel_pipeline", context)
    return {"message": result.output.get("message", "Cancelled")}


@router.get("/logs")
async def get_action_logs(
    agent_type: str | None = None,
    limit: int = 50,
) -> list[ActionLogResponse]:
    """Get action logs from all agents."""
    action_logger = AgentActionLogger()

    type_filter = None
    if agent_type:
        type_filter = AgentType(agent_type)

    logs = action_logger.get_logs(agent_type=type_filter, limit=limit)

    return [
        ActionLogResponse(
            id=str(log.id),
            agent_type=log.agent_type.value,
            agent_name=log.agent_name,
            action_name=log.action_name,
            status=log.status.value,
            confidence=log.confidence,
            cost_usd=log.cost_usd,
            started_at=log.started_at.isoformat(),
            completed_at=log.completed_at.isoformat() if log.completed_at else None,
        )
        for log in logs
    ]


@router.get("/logs/cost")
async def get_total_cost() -> dict[str, float]:
    """Get total cost of all logged actions."""
    action_logger = AgentActionLogger()
    return {"total_cost_usd": action_logger.get_total_cost()}


@router.get("/agents")
async def list_agents() -> list[dict[str, Any]]:
    """List all registered agents."""
    orchestrator = get_orchestrator()

    agents = []
    for agent_type, agent in orchestrator._agents.items():
        agents.append({
            "type": agent_type.value,
            "name": agent.name,
            "capabilities": agent.capabilities,
            "requires_approval": agent.requires_approval,
        })

    return agents
