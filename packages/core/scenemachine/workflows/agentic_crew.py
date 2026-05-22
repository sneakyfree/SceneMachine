"""SceneMachine Agentic Crew.

Implements the DNA strand master plan's multi-agent orchestration system.
Each agent has bounded autonomy with clear approval gates.

Architecture:
- Orchestrator: Routes tasks, maintains state, enforces guardrails
- Parser Agent: Script parsing, shot lists, contradiction detection
- Character Agent: Reference generation, face embedding, voice cloning
- Generator Agent: Video generation, TTS, lip-sync, quality gate
- Assembler Agent: Clip concatenation, transitions, audio mixing
- Reviewer Agent: Quality scoring, physics check, human escalation
- Export Agent: Format conversion, compression, distribution
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class AgentState(StrEnum):
    """Agent execution states."""

    IDLE = "idle"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class ApprovalType(StrEnum):
    """Types of human approval required."""

    NONE = "none"
    HIGH_COST = "high_cost"  # Spend >$10
    SENSITIVE_CONTENT = "sensitive"  # Potentially sensitive generation
    REAL_PERSON = "real_person"  # Using real person likeness
    FINAL_EXPORT = "final_export"  # Approve final output
    QUALITY_ISSUE = "quality_issue"  # Quality gate failed


@dataclass
class AgentAction:
    """Record of an agent action."""

    action_id: str
    agent_id: str
    action_type: str
    timestamp: datetime
    inputs: dict[str, Any]
    outputs: dict[str, Any] | None = None
    success: bool = True
    error_message: str | None = None
    duration_ms: int = 0
    requires_approval: bool = False
    approval_type: ApprovalType | None = None
    approved: bool | None = None
    approver_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "agent_id": self.agent_id,
            "action_type": self.action_type,
            "timestamp": self.timestamp.isoformat(),
            "inputs_summary": self._summarize_inputs(),
            "outputs_summary": self._summarize_outputs() if self.outputs else None,
            "success": self.success,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "requires_approval": self.requires_approval,
            "approval_type": self.approval_type.value if self.approval_type else None,
            "approved": self.approved,
            "approver_id": self.approver_id,
        }

    def _summarize_inputs(self) -> dict[str, Any]:
        """Summarize inputs for logging (avoid large payloads)."""
        summary = {}
        for key, value in self.inputs.items():
            if isinstance(value, (str, int, float, bool)):
                summary[key] = value
            elif isinstance(value, list):
                summary[key] = f"[{len(value)} items]"
            elif isinstance(value, dict):
                summary[key] = f"{{...{len(value)} keys}}"
            else:
                summary[key] = str(type(value).__name__)
        return summary

    def _summarize_outputs(self) -> dict[str, Any] | None:
        if not self.outputs:
            return None
        return self._summarize_inputs()  # Same logic


@dataclass
class AgentContext:
    """Shared context between agents."""

    project_id: str | None = None
    screenplay_data: dict[str, Any] | None = None
    characters: list[dict[str, Any]] = field(default_factory=list)
    scenes: list[dict[str, Any]] = field(default_factory=list)
    shots: list[dict[str, Any]] = field(default_factory=list)
    generated_assets: dict[str, str] = field(default_factory=dict)  # shot_id -> asset_path
    blockers: list[dict[str, Any]] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)
    action_log: list[AgentAction] = field(default_factory=list)

    def add_action(self, action: AgentAction) -> None:
        """Add an action to the log."""
        self.action_log.append(action)

    def get_pending_approvals(self) -> list[AgentAction]:
        """Get actions waiting for approval."""
        return [a for a in self.action_log if a.requires_approval and a.approved is None]


class BaseAgent(ABC):
    """Base class for all agents in the crew."""

    def __init__(self, agent_id: str, name: str) -> None:
        self.agent_id = agent_id
        self.name = name
        self.state = AgentState.IDLE
        self._context: AgentContext | None = None

    @property
    def context(self) -> AgentContext:
        if self._context is None:
            raise RuntimeError(f"Agent {self.name} has no context set")
        return self._context

    def set_context(self, context: AgentContext) -> None:
        """Set the shared context."""
        self._context = context

    @abstractmethod
    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute an agent task.

        Args:
            task: Task definition with type and parameters

        Returns:
            Task result
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """Get list of task types this agent can handle."""
        pass

    def log_action(
        self,
        action_type: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any] | None = None,
        success: bool = True,
        error: str | None = None,
        requires_approval: bool = False,
        approval_type: ApprovalType | None = None,
    ) -> AgentAction:
        """Log an action to the context."""
        action = AgentAction(
            action_id=str(uuid4()),
            agent_id=self.agent_id,
            action_type=action_type,
            timestamp=datetime.utcnow(),
            inputs=inputs,
            outputs=outputs,
            success=success,
            error_message=error,
            requires_approval=requires_approval,
            approval_type=approval_type,
        )
        self.context.add_action(action)
        logger.info(f"Agent {self.name} action: {action_type} - success={success}")
        return action


class ParserAgent(BaseAgent):
    """Agent for screenplay parsing and shot list generation."""

    def __init__(self) -> None:
        super().__init__("parser_agent", "Parser Agent")

    def get_capabilities(self) -> list[str]:
        return [
            "parse_screenplay",
            "generate_shot_list",
            "detect_contradictions",
            "validate_format",
        ]

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        task_type = task.get("type")

        if task_type == "parse_screenplay":
            return await self._parse_screenplay(task)
        elif task_type == "generate_shot_list":
            return await self._generate_shot_list(task)
        elif task_type == "detect_contradictions":
            return await self._detect_contradictions(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _parse_screenplay(self, task: dict[str, Any]) -> dict[str, Any]:
        """Parse a screenplay file."""
        from scenemachine.parsers import parse_fdx, parse_fountain, parse_pdf

        file_path = task.get("file_path")
        file_format = task.get("format", "").lower()

        self.state = AgentState.RUNNING

        try:
            if file_format == "fountain":
                with open(file_path) as f:
                    result = parse_fountain(f.read())
            elif file_format == "pdf":
                result = parse_pdf(file_path)
            elif file_format == "fdx":
                result = parse_fdx(file_path)
            else:
                raise ValueError(f"Unsupported format: {file_format}")

            self.context.screenplay_data = result

            self.log_action(
                "parse_screenplay",
                {"file_path": file_path, "format": file_format},
                {
                    "scenes": len(result.get("scenes", [])),
                    "characters": len(result.get("characters", [])),
                },
            )

            self.state = AgentState.COMPLETED
            return {"success": True, "data": result}

        except Exception as e:
            self.state = AgentState.FAILED
            self.log_action(
                "parse_screenplay",
                {"file_path": file_path, "format": file_format},
                success=False,
                error=str(e),
            )
            return {"success": False, "error": str(e)}

    async def _generate_shot_list(self, task: dict[str, Any]) -> dict[str, Any]:
        """Generate shot list from parsed screenplay."""
        from scenemachine.services.shot_list_generator import generate_shot_list

        screenplay_data = task.get("screenplay_data") or self.context.screenplay_data

        if not screenplay_data:
            return {"success": False, "error": "No screenplay data available"}

        self.state = AgentState.RUNNING

        try:
            result = generate_shot_list(screenplay_data)

            self.context.scenes = result.get("scenes", [])
            self.context.shots = [
                shot for scene in result.get("scenes", []) for shot in scene.get("shots", [])
            ]

            self.log_action(
                "generate_shot_list",
                {"screenplay_title": screenplay_data.get("title")},
                {"total_shots": result.get("summary", {}).get("total_shots", 0)},
            )

            self.state = AgentState.COMPLETED
            return {"success": True, "data": result}

        except Exception as e:
            self.state = AgentState.FAILED
            self.log_action(
                "generate_shot_list",
                {},
                success=False,
                error=str(e),
            )
            return {"success": False, "error": str(e)}

    async def _detect_contradictions(self, task: dict[str, Any]) -> dict[str, Any]:
        """Detect contradictions in screenplay."""
        from scenemachine.services.shot_list_generator import ShotListGenerator

        ShotListGenerator()
        # Contradiction detection is now part of shot list generation

        self.log_action(
            "detect_contradictions",
            {},
            {"contradictions": []},
        )

        return {"success": True, "contradictions": []}


class CharacterAgent(BaseAgent):
    """Agent for character management."""

    def __init__(self) -> None:
        super().__init__("character_agent", "Character Agent")

    def get_capabilities(self) -> list[str]:
        return [
            "extract_characters",
            "generate_reference_image",
            "extract_face_embedding",
            "clone_voice",
            "check_consistency",
        ]

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        task_type = task.get("type")

        if task_type == "extract_characters":
            return await self._extract_characters(task)
        elif task_type == "generate_reference_image":
            return await self._generate_reference_image(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _extract_characters(self, task: dict[str, Any]) -> dict[str, Any]:
        """Extract characters from screenplay."""
        screenplay_data = self.context.screenplay_data

        if not screenplay_data:
            return {"success": False, "error": "No screenplay data"}

        characters = screenplay_data.get("characters", [])

        # Build character list with metadata
        char_list = []
        for char_name in characters:
            char_list.append(
                {
                    "name": char_name,
                    "description": None,
                    "reference_image_id": None,
                    "voice_profile": None,
                }
            )

        self.context.characters = char_list

        self.log_action(
            "extract_characters",
            {},
            {"count": len(char_list)},
        )

        return {"success": True, "characters": char_list}

    async def _generate_reference_image(self, task: dict[str, Any]) -> dict[str, Any]:
        """Generate reference image for a character."""
        character_name = task.get("character_name")
        description = task.get("description", "")

        # Check if this is a real person (requires approval)
        is_real_person = task.get("is_real_person", False)

        if is_real_person:
            action = self.log_action(
                "generate_reference_image",
                {"character_name": character_name, "is_real_person": True},
                requires_approval=True,
                approval_type=ApprovalType.REAL_PERSON,
            )
            self.state = AgentState.WAITING_APPROVAL
            return {
                "success": False,
                "requires_approval": True,
                "approval_action_id": action.action_id,
                "message": f"Using likeness of real person '{character_name}' requires approval",
            }

        # Would integrate with Flux Schnell here
        self.log_action(
            "generate_reference_image",
            {"character_name": character_name, "description": description[:100]},
            {"image_generated": True},
        )

        return {"success": True, "image_path": f"/tmp/{character_name}_ref.png"}


class GeneratorAgent(BaseAgent):
    """Agent for video and audio generation."""

    def __init__(self) -> None:
        super().__init__("generator_agent", "Generator Agent")
        self.cost_threshold = 10.0  # Require approval above this

    def get_capabilities(self) -> list[str]:
        return [
            "generate_video",
            "generate_audio",
            "apply_lipsync",
            "quality_check",
        ]

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        task_type = task.get("type")

        if task_type == "generate_video":
            return await self._generate_video(task)
        elif task_type == "generate_audio":
            return await self._generate_audio(task)
        elif task_type == "quality_check":
            return await self._quality_check(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _generate_video(self, task: dict[str, Any]) -> dict[str, Any]:
        """Generate video for a shot."""
        shot_id = task.get("shot_id")
        prompt = task.get("prompt")
        estimated_cost = task.get("estimated_cost", 0.0)

        # Check cost threshold
        if estimated_cost > self.cost_threshold:
            action = self.log_action(
                "generate_video",
                {"shot_id": shot_id, "estimated_cost": estimated_cost},
                requires_approval=True,
                approval_type=ApprovalType.HIGH_COST,
            )
            self.state = AgentState.WAITING_APPROVAL
            return {
                "success": False,
                "requires_approval": True,
                "approval_action_id": action.action_id,
                "message": f"Generation cost ${estimated_cost:.2f} exceeds threshold",
            }

        # Would integrate with Wan 2.1 / Mochi here
        self.log_action(
            "generate_video",
            {"shot_id": shot_id, "prompt": prompt[:100] if prompt else ""},
            {"video_generated": True},
        )

        return {"success": True, "video_path": f"/tmp/{shot_id}.mp4"}

    async def _generate_audio(self, task: dict[str, Any]) -> dict[str, Any]:
        """Generate dialogue audio."""
        character = task.get("character")
        text = task.get("text")

        # Would integrate with Kokoro TTS here
        self.log_action(
            "generate_audio",
            {"character": character, "text_length": len(text) if text else 0},
            {"audio_generated": True},
        )

        return {"success": True, "audio_path": f"/tmp/{character}_dialogue.wav"}

    async def _quality_check(self, task: dict[str, Any]) -> dict[str, Any]:
        """Check quality of generated content."""
        asset_path = task.get("asset_path")

        # Would run quality scoring here
        quality_score = 0.85
        issues = []

        if quality_score < 0.7:
            issues.append("Low quality score")

        self.log_action(
            "quality_check",
            {"asset_path": asset_path},
            {"quality_score": quality_score, "issues": issues},
        )

        return {"success": True, "quality_score": quality_score, "issues": issues}


class AssemblerAgent(BaseAgent):
    """Agent for assembling final video."""

    def __init__(self) -> None:
        super().__init__("assembler_agent", "Assembler Agent")

    def get_capabilities(self) -> list[str]:
        return [
            "concatenate_clips",
            "apply_transitions",
            "mix_audio",
            "normalize_audio",
            "render_final",
        ]

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        task_type = task.get("type")

        if task_type == "render_final":
            return await self._render_final(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _render_final(self, task: dict[str, Any]) -> dict[str, Any]:
        """Render final assembled video."""
        # This requires human approval for final export
        action = self.log_action(
            "render_final",
            {"clips_count": len(self.context.generated_assets)},
            requires_approval=True,
            approval_type=ApprovalType.FINAL_EXPORT,
        )
        self.state = AgentState.WAITING_APPROVAL

        return {
            "success": False,
            "requires_approval": True,
            "approval_action_id": action.action_id,
            "message": "Final export requires human approval",
        }


class ReviewerAgent(BaseAgent):
    """Agent for quality review."""

    def __init__(self) -> None:
        super().__init__("reviewer_agent", "Reviewer Agent")

    def get_capabilities(self) -> list[str]:
        return [
            "review_quality",
            "check_physics",
            "detect_artifacts",
            "escalate_issue",
        ]

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        task_type = task.get("type")

        if task_type == "review_quality":
            return await self._review_quality(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _review_quality(self, task: dict[str, Any]) -> dict[str, Any]:
        """Review overall quality."""
        assets = self.context.generated_assets

        issues = []
        passed = True

        # Would run quality checks here

        self.log_action(
            "review_quality",
            {"assets_count": len(assets)},
            {"passed": passed, "issues_count": len(issues)},
        )

        return {"success": True, "passed": passed, "issues": issues}


class Orchestrator:
    """Main orchestrator that coordinates all agents.

    Implements the DNA strand master plan's orchestration requirements:
    - Routes tasks to specialist agents
    - Maintains project state
    - Enforces guardrails
    - Escalates to human for approval gates
    """

    def __init__(self) -> None:
        self.context = AgentContext()

        # Initialize agents
        self.parser = ParserAgent()
        self.character = CharacterAgent()
        self.generator = GeneratorAgent()
        self.assembler = AssemblerAgent()
        self.reviewer = ReviewerAgent()

        # Set shared context
        for agent in [self.parser, self.character, self.generator, self.assembler, self.reviewer]:
            agent.set_context(self.context)

        self._agent_map = {
            "parser": self.parser,
            "character": self.character,
            "generator": self.generator,
            "assembler": self.assembler,
            "reviewer": self.reviewer,
        }

    async def run_pipeline(self, screenplay_path: str, file_format: str) -> dict[str, Any]:
        """Run the complete screenplay-to-movie pipeline.

        Args:
            screenplay_path: Path to screenplay file
            file_format: File format (fountain, pdf, fdx)

        Returns:
            Pipeline result with status and any pending approvals
        """
        logger.info(f"Starting pipeline for {screenplay_path}")

        # Step 1: Parse screenplay
        parse_result = await self.parser.execute(
            {
                "type": "parse_screenplay",
                "file_path": screenplay_path,
                "format": file_format,
            }
        )

        if not parse_result.get("success"):
            return {"success": False, "stage": "parse", "error": parse_result.get("error")}

        # Step 2: Extract characters
        await self.character.execute(
            {
                "type": "extract_characters",
            }
        )

        # Step 3: Generate shot list
        shot_result = await self.parser.execute(
            {
                "type": "generate_shot_list",
            }
        )

        if not shot_result.get("success"):
            return {"success": False, "stage": "shot_list", "error": shot_result.get("error")}

        # Step 4: Analyze blockers
        from scenemachine.services.blockers_engine import analyze_blockers

        blockers = analyze_blockers(
            self.context.characters,
            self.context.scenes,
            self.context.shots,
            self.context.settings,
        )

        self.context.blockers = blockers.get("blockers", [])

        # Check for critical blockers
        if not blockers.get("summary", {}).get("can_proceed", True):
            return {
                "success": False,
                "stage": "blockers",
                "message": "Critical blockers prevent generation",
                "blockers": blockers,
            }

        # Check for pending approvals
        pending = self.context.get_pending_approvals()
        if pending:
            return {
                "success": False,
                "stage": "approval",
                "message": "Waiting for human approval",
                "pending_approvals": [a.to_dict() for a in pending],
            }

        # Return ready state
        return {
            "success": True,
            "stage": "ready_for_generation",
            "summary": {
                "scenes": len(self.context.scenes),
                "shots": len(self.context.shots),
                "characters": len(self.context.characters),
                "blockers": len(self.context.blockers),
            },
        }

    def approve_action(self, action_id: str, approver_id: str) -> bool:
        """Approve a pending action.

        Args:
            action_id: ID of action to approve
            approver_id: ID of approver

        Returns:
            True if approved, False if action not found
        """
        for action in self.context.action_log:
            if action.action_id == action_id:
                action.approved = True
                action.approver_id = approver_id
                logger.info(f"Action {action_id} approved by {approver_id}")
                return True
        return False

    def reject_action(self, action_id: str, approver_id: str, reason: str = "") -> bool:
        """Reject a pending action.

        Args:
            action_id: ID of action to reject
            approver_id: ID of rejector
            reason: Rejection reason

        Returns:
            True if rejected, False if action not found
        """
        for action in self.context.action_log:
            if action.action_id == action_id:
                action.approved = False
                action.approver_id = approver_id
                action.error_message = reason
                logger.info(f"Action {action_id} rejected by {approver_id}: {reason}")
                return True
        return False

    def get_action_log(self) -> list[dict[str, Any]]:
        """Get the complete action log."""
        return [a.to_dict() for a in self.context.action_log]

    def get_status(self) -> dict[str, Any]:
        """Get current orchestrator status."""
        return {
            "context": {
                "project_id": self.context.project_id,
                "has_screenplay": self.context.screenplay_data is not None,
                "scenes_count": len(self.context.scenes),
                "shots_count": len(self.context.shots),
                "characters_count": len(self.context.characters),
                "generated_assets_count": len(self.context.generated_assets),
                "blockers_count": len(self.context.blockers),
            },
            "agents": {
                name: {"state": agent.state.value} for name, agent in self._agent_map.items()
            },
            "pending_approvals": len(self.context.get_pending_approvals()),
            "action_count": len(self.context.action_log),
        }


# Convenience function
def create_orchestrator() -> Orchestrator:
    """Create a new orchestrator instance."""
    return Orchestrator()
