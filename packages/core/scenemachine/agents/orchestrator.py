"""
Orchestrator Agent - Pipeline coordination and crew management.

The Orchestrator (Director Agent) coordinates the full screenplay-to-movie
pipeline, delegating to specialist agents and maintaining project state.

Responsibilities:
- Route tasks to appropriate specialist agents
- Maintain project state and progress
- Enforce guardrails across all agents
- Escalate to human for approval gates
"""

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from scenemachine.agents.base import (
    ActionContext,
    ActionResult,
    ActionStatus,
    AgentType,
    BaseAgent,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineState:
    """State of the current pipeline execution."""

    project_id: UUID
    status: str = "idle"  # idle, running, paused, completed, failed
    current_phase: str = "init"
    progress_percent: float = 0.0
    total_shots: int = 0
    completed_shots: int = 0
    failed_shots: int = 0
    total_cost_usd: float = 0.0
    errors: list[str] = field(default_factory=list)
    phase_results: dict[str, Any] = field(default_factory=dict)


class OrchestratorAgent(BaseAgent):
    """
    Director Agent that orchestrates the full screenplay-to-movie pipeline.

    Pipeline phases:
    1. parse: Parse screenplay and extract structure
    2. characters: Setup characters with references and voices
    3. shots: Generate shot list for each scene
    4. generate: Generate video and audio for each shot
    5. review: Quality review of generated content
    6. assemble: Assemble scenes and final movie
    7. export: Export final deliverable

    Autonomous actions:
    - run_pipeline: Execute full pipeline
    - run_phase: Execute single phase
    - get_status: Get pipeline status
    - pause/resume: Control execution

    Requires approval:
    - run_full_pipeline: Human must approve starting full generation
    - override_quality: Skip quality issues
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._state: PipelineState | None = None
        self._agents: dict[AgentType, BaseAgent] = {}
        self._is_paused = False

    @property
    def agent_type(self) -> AgentType:
        return AgentType.ORCHESTRATOR

    @property
    def capabilities(self) -> list[str]:
        return [
            "run_pipeline",
            "run_phase",
            "get_status",
            "pause_pipeline",
            "resume_pipeline",
            "cancel_pipeline",
            "run_full_pipeline",
            "override_quality",
        ]

    @property
    def requires_approval(self) -> list[str]:
        return ["run_full_pipeline", "override_quality"]

    def register_agent(self, agent: BaseAgent) -> None:
        """Register a specialist agent with the orchestrator."""
        self._agents[agent.agent_type] = agent
        logger.info(f"Registered agent: {agent.name} ({agent.agent_type.value})")

    def get_agent(self, agent_type: AgentType) -> BaseAgent | None:
        """Get a registered agent by type."""
        return self._agents.get(agent_type)

    async def _execute_action(
        self,
        action_name: str,
        context: ActionContext,
        **kwargs,
    ) -> ActionResult:
        """Execute orchestrator actions."""
        if action_name == "run_pipeline":
            return await self._run_pipeline(context, **kwargs)
        elif action_name == "run_phase":
            return await self._run_phase(context, **kwargs)
        elif action_name == "get_status":
            return await self._get_status(context, **kwargs)
        elif action_name == "pause_pipeline":
            return await self._pause_pipeline(context)
        elif action_name == "resume_pipeline":
            return await self._resume_pipeline(context)
        elif action_name == "cancel_pipeline":
            return await self._cancel_pipeline(context)
        else:
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=f"Unknown action: {action_name}",
            )

    async def _run_pipeline(
        self,
        context: ActionContext,
        screenplay_path: str,
        phases: list[str] | None = None,
    ) -> ActionResult:
        """Run the full screenplay-to-movie pipeline."""
        all_phases = ["parse", "characters", "shots", "generate", "review", "assemble", "export"]
        phases_to_run = phases or all_phases

        # Initialize state
        self._state = PipelineState(
            project_id=context.project_id,
            status="running",
            current_phase="init",
        )

        phase_results = {}
        total_cost = 0.0

        try:
            for i, phase in enumerate(phases_to_run):
                if self._is_paused:
                    self._state.status = "paused"
                    return ActionResult(
                        action_id=context.session_id,
                        status=ActionStatus.COMPLETED,
                        success=True,
                        output={"status": "paused", "phase": phase},
                    )

                self._state.current_phase = phase
                self._state.progress_percent = (i / len(phases_to_run)) * 100

                logger.info(f"Running phase: {phase} ({i + 1}/{len(phases_to_run)})")

                result = await self._run_phase(
                    context,
                    phase=phase,
                    input_data=phase_results,
                )

                if not result.success:
                    self._state.status = "failed"
                    self._state.errors.append(f"Phase {phase} failed: {result.error_message}")
                    return result

                phase_results[phase] = result.output
                total_cost += result.cost_usd

            # Pipeline complete
            self._state.status = "completed"
            self._state.progress_percent = 100.0
            self._state.total_cost_usd = total_cost
            self._state.phase_results = phase_results

            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.COMPLETED,
                success=True,
                output={
                    "project_id": str(context.project_id),
                    "phases_completed": phases_to_run,
                    "phase_results": phase_results,
                    "total_cost_usd": total_cost,
                },
                cost_usd=total_cost,
                confidence=0.85,
            )

        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            self._state.status = "failed"
            self._state.errors.append(str(e))
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=str(e),
            )

    async def _run_phase(
        self,
        context: ActionContext,
        phase: str,
        input_data: dict[str, Any] | None = None,
    ) -> ActionResult:
        """Run a single pipeline phase."""
        input_data = input_data or {}

        if phase == "parse":
            return await self._phase_parse(context, input_data)
        elif phase == "characters":
            return await self._phase_characters(context, input_data)
        elif phase == "shots":
            return await self._phase_shots(context, input_data)
        elif phase == "generate":
            return await self._phase_generate(context, input_data)
        elif phase == "review":
            return await self._phase_review(context, input_data)
        elif phase == "assemble":
            return await self._phase_assemble(context, input_data)
        elif phase == "export":
            return await self._phase_export(context, input_data)
        else:
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=f"Unknown phase: {phase}",
            )

    async def _phase_parse(
        self,
        context: ActionContext,
        input_data: dict[str, Any],
    ) -> ActionResult:
        """Parse screenplay phase."""
        from scenemachine.agents.parser_agent import ParserAgent

        parser = self._agents.get(AgentType.PARSER) or ParserAgent()

        # Get screenplay path from input or context
        screenplay_path = input_data.get("screenplay_path", "")

        if not screenplay_path:
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.COMPLETED,
                success=True,
                output={"message": "No screenplay to parse (using existing project data)"},
                confidence=0.5,
            )

        result = await parser.execute(
            "parse_screenplay",
            context,
            file_path=screenplay_path,
        )

        return result

    async def _phase_characters(
        self,
        context: ActionContext,
        input_data: dict[str, Any],
    ) -> ActionResult:
        """Character setup phase."""
        from scenemachine.agents.character_agent import CharacterAgent

        character_agent = self._agents.get(AgentType.CHARACTER) or CharacterAgent()

        # Get characters from parse phase
        parsed = input_data.get("parse", {})
        characters = parsed.get("characters", [])

        results = []
        for char in characters[:5]:  # Limit for demo
            # Generate reference
            ref_result = await character_agent.execute(
                "generate_reference",
                context,
                character_name=char.get("name", "Unknown"),
                description=char.get("description", ""),
            )
            results.append(ref_result.output)

        return ActionResult(
            action_id=context.session_id,
            status=ActionStatus.COMPLETED,
            success=True,
            output={"characters": results, "count": len(results)},
            confidence=0.8,
        )

    async def _phase_shots(
        self,
        context: ActionContext,
        input_data: dict[str, Any],
    ) -> ActionResult:
        """Shot list generation phase."""
        from scenemachine.agents.parser_agent import ParserAgent

        parser = self._agents.get(AgentType.PARSER) or ParserAgent()
        parsed = input_data.get("parse", {})
        scenes = parsed.get("scenes", [])

        all_shots = []
        for scene in scenes[:3]:  # Limit for demo
            result = await parser.execute(
                "generate_shot_list",
                context,
                scene=scene,
            )
            if result.success:
                all_shots.extend(result.output.get("shots", []))

        return ActionResult(
            action_id=context.session_id,
            status=ActionStatus.COMPLETED,
            success=True,
            output={"shots": all_shots, "count": len(all_shots)},
            confidence=0.8,
        )

    async def _phase_generate(
        self,
        context: ActionContext,
        input_data: dict[str, Any],
    ) -> ActionResult:
        """Video/audio generation phase."""
        from scenemachine.agents.generator_agent import GeneratorAgent

        generator = self._agents.get(AgentType.GENERATOR) or GeneratorAgent()
        shots = input_data.get("shots", {}).get("shots", [])

        generated = []
        total_cost = 0.0

        for shot in shots[:3]:  # Limit for demo
            result = await generator.execute(
                "generate_video",
                context,
                shot_id=uuid4(),
                prompt=shot.get("prompt", "A cinematic shot"),
            )
            if result.success:
                generated.append(result.output)
                total_cost += result.cost_usd

        return ActionResult(
            action_id=context.session_id,
            status=ActionStatus.COMPLETED,
            success=True,
            output={"generated": generated, "count": len(generated)},
            cost_usd=total_cost,
            confidence=0.8,
        )

    async def _phase_review(
        self,
        context: ActionContext,
        input_data: dict[str, Any],
    ) -> ActionResult:
        """Quality review phase."""
        from scenemachine.agents.reviewer_agent import ReviewerAgent

        reviewer = self._agents.get(AgentType.REVIEWER) or ReviewerAgent()
        generated = input_data.get("generate", {}).get("generated", [])

        reviews = []
        passed = 0
        failed = 0

        for gen in generated:
            video_path = gen.get("video_path", "")
            if video_path:
                result = await reviewer.execute(
                    "review_video",
                    context,
                    video_path=video_path,
                )
                if result.success:
                    reviews.append(result.output)
                    if result.output.get("passed"):
                        passed += 1
                    else:
                        failed += 1

        return ActionResult(
            action_id=context.session_id,
            status=ActionStatus.COMPLETED,
            success=True,
            output={
                "reviews": reviews,
                "passed": passed,
                "failed": failed,
                "pass_rate": passed / (passed + failed) if (passed + failed) > 0 else 0,
            },
            confidence=0.75,
        )

    async def _phase_assemble(
        self,
        context: ActionContext,
        input_data: dict[str, Any],
    ) -> ActionResult:
        """Assembly phase."""
        # Mock implementation - would assemble actual videos
        return ActionResult(
            action_id=context.session_id,
            status=ActionStatus.COMPLETED,
            success=True,
            output={"message": "Assembly complete", "output_path": "movie.mp4"},
            confidence=0.85,
        )

    async def _phase_export(
        self,
        context: ActionContext,
        input_data: dict[str, Any],
    ) -> ActionResult:
        """Export phase."""
        return ActionResult(
            action_id=context.session_id,
            status=ActionStatus.COMPLETED,
            success=True,
            output={"message": "Export complete", "format": "mp4_h264"},
            confidence=0.9,
        )

    async def _get_status(
        self,
        context: ActionContext,
    ) -> ActionResult:
        """Get current pipeline status."""
        if not self._state:
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.COMPLETED,
                success=True,
                output={"status": "idle", "message": "No pipeline running"},
            )

        return ActionResult(
            action_id=context.session_id,
            status=ActionStatus.COMPLETED,
            success=True,
            output={
                "project_id": str(self._state.project_id),
                "status": self._state.status,
                "current_phase": self._state.current_phase,
                "progress_percent": self._state.progress_percent,
                "total_cost_usd": self._state.total_cost_usd,
                "errors": self._state.errors,
            },
        )

    async def _pause_pipeline(self, context: ActionContext) -> ActionResult:
        """Pause the running pipeline."""
        self._is_paused = True
        return ActionResult(
            action_id=context.session_id,
            status=ActionStatus.COMPLETED,
            success=True,
            output={"message": "Pipeline paused"},
        )

    async def _resume_pipeline(self, context: ActionContext) -> ActionResult:
        """Resume a paused pipeline."""
        self._is_paused = False
        return ActionResult(
            action_id=context.session_id,
            status=ActionStatus.COMPLETED,
            success=True,
            output={"message": "Pipeline resumed"},
        )

    async def _cancel_pipeline(self, context: ActionContext) -> ActionResult:
        """Cancel the running pipeline."""
        if self._state:
            self._state.status = "cancelled"
        self._is_paused = False
        return ActionResult(
            action_id=context.session_id,
            status=ActionStatus.COMPLETED,
            success=True,
            output={"message": "Pipeline cancelled"},
        )
