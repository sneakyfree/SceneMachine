"""Base workflow classes and utilities."""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Generic, TypeVar
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class StepStatus(StrEnum):
    """Status of a workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class WorkflowStatus(StrEnum):
    """Status of the overall workflow."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StepResult:
    """Result of executing a workflow step."""

    success: bool
    data: Any | None = None
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass
class WorkflowStep:
    """Definition of a single workflow step."""

    id: str
    name: str
    description: str
    handler: str  # Name of the method to call
    status: StepStatus = StepStatus.PENDING
    result: StepResult | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retries: int = 0
    max_retries: int = 3
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float | None:
        """Calculate step duration."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class WorkflowState:
    """State of a workflow execution."""

    workflow_id: UUID
    workflow_type: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step_index: int = 0
    steps: list[WorkflowStep] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress_percent: float = 0.0

    @property
    def current_step(self) -> WorkflowStep | None:
        """Get the current step."""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    @property
    def completed_steps(self) -> list[WorkflowStep]:
        """Get completed steps."""
        return [s for s in self.steps if s.status == StepStatus.COMPLETED]

    @property
    def duration_seconds(self) -> float | None:
        """Calculate workflow duration."""
        if self.started_at:
            end_time = self.completed_at or datetime.now(UTC)
            return (end_time - self.started_at).total_seconds()
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "workflowId": str(self.workflow_id),
            "workflowType": self.workflow_type,
            "status": self.status.value,
            "currentStepIndex": self.current_step_index,
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "status": s.status.value,
                    "result": {
                        "success": s.result.success,
                        "error": s.result.error,
                        "durationSeconds": s.result.duration_seconds,
                    }
                    if s.result
                    else None,
                    "startedAt": s.started_at.isoformat() if s.started_at else None,
                    "completedAt": s.completed_at.isoformat() if s.completed_at else None,
                    "retries": s.retries,
                }
                for s in self.steps
            ],
            "error": self.error,
            "progressPercent": self.progress_percent,
            "createdAt": self.created_at.isoformat(),
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "durationSeconds": self.duration_seconds,
        }


# Type variable for workflow context
T = TypeVar("T")


class Workflow(ABC, Generic[T]):
    """Base class for workflow definitions."""

    def __init__(
        self,
        workflow_id: UUID | None = None,
        context: T | None = None,
    ) -> None:
        self.workflow_id = workflow_id or uuid4()
        self._context = context
        self._state: WorkflowState | None = None
        self._on_progress: Callable[[WorkflowState], None] | None = None
        self._on_step_complete: Callable[[WorkflowStep], None] | None = None
        self._cancelled = False

    @property
    @abstractmethod
    def workflow_type(self) -> str:
        """Return the workflow type identifier."""
        pass

    @abstractmethod
    def define_steps(self) -> list[WorkflowStep]:
        """Define the workflow steps."""
        pass

    @property
    def state(self) -> WorkflowState | None:
        """Get current workflow state."""
        return self._state

    @property
    def context(self) -> T | None:
        """Get workflow context."""
        return self._context

    def on_progress(self, callback: Callable[[WorkflowState], None]) -> "Workflow":
        """Set progress callback."""
        self._on_progress = callback
        return self

    def on_step_complete(self, callback: Callable[[WorkflowStep], None]) -> "Workflow":
        """Set step completion callback."""
        self._on_step_complete = callback
        return self

    def cancel(self) -> None:
        """Cancel the workflow."""
        self._cancelled = True
        if self._state:
            self._state.status = WorkflowStatus.CANCELLED

    def _update_progress(self) -> None:
        """Update progress percentage."""
        if not self._state:
            return

        total = len(self._state.steps)
        if total == 0:
            self._state.progress_percent = 0
            return

        completed = sum(
            1
            for s in self._state.steps
            if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
        )
        self._state.progress_percent = (completed / total) * 100

        if self._on_progress:
            self._on_progress(self._state)

    async def _execute_step(self, step: WorkflowStep) -> StepResult:
        """Execute a single workflow step."""
        handler = getattr(self, step.handler, None)
        if not handler:
            return StepResult(
                success=False,
                error=f"Handler '{step.handler}' not found",
            )

        start_time = datetime.now(UTC)
        step.started_at = start_time
        step.status = StepStatus.RUNNING
        self._update_progress()

        try:
            # Execute handler (supports both sync and async)
            if asyncio.iscoroutinefunction(handler):
                result_data = await handler(self._state.context if self._state else {})
            else:
                result_data = handler(self._state.context if self._state else {})

            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()

            return StepResult(
                success=True,
                data=result_data,
                duration_seconds=duration,
            )

        except Exception as e:
            logger.exception(f"Step '{step.name}' failed: {e}")
            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()

            return StepResult(
                success=False,
                error=str(e),
                duration_seconds=duration,
            )

    def _check_dependencies(self, step: WorkflowStep) -> bool:
        """Check if step dependencies are satisfied."""
        if not self._state:
            return False

        for dep_id in step.dependencies:
            dep_step = next((s for s in self._state.steps if s.id == dep_id), None)
            if not dep_step or dep_step.status != StepStatus.COMPLETED:
                return False

        return True

    async def execute(self) -> WorkflowState:
        """Execute the workflow."""
        # Initialize state
        self._state = WorkflowState(
            workflow_id=self.workflow_id,
            workflow_type=self.workflow_type,
            steps=self.define_steps(),
            context=self._context.__dict__ if self._context else {},
        )
        self._state.status = WorkflowStatus.RUNNING
        self._state.started_at = datetime.now(UTC)
        self._update_progress()

        logger.info(f"Starting workflow {self.workflow_type} ({self.workflow_id})")

        try:
            for i, step in enumerate(self._state.steps):
                if self._cancelled:
                    step.status = StepStatus.CANCELLED
                    break

                self._state.current_step_index = i

                # Check dependencies
                if not self._check_dependencies(step):
                    step.status = StepStatus.SKIPPED
                    logger.warning(f"Skipping step '{step.name}' - dependencies not met")
                    continue

                # Execute with retries
                while step.retries <= step.max_retries:
                    result = await self._execute_step(step)
                    step.result = result
                    step.completed_at = datetime.now(UTC)

                    if result.success:
                        step.status = StepStatus.COMPLETED
                        # Merge result data into context
                        if result.data and isinstance(result.data, dict):
                            self._state.context.update(result.data)
                        break

                    step.retries += 1
                    if step.retries <= step.max_retries:
                        logger.warning(
                            f"Retrying step '{step.name}' ({step.retries}/{step.max_retries})"
                        )
                        await asyncio.sleep(1)  # Brief delay before retry

                if step.status != StepStatus.COMPLETED:
                    step.status = StepStatus.FAILED
                    self._state.status = WorkflowStatus.FAILED
                    self._state.error = step.result.error if step.result else "Unknown error"
                    break

                self._update_progress()

                if self._on_step_complete:
                    self._on_step_complete(step)

            # Final status
            if self._state.status == WorkflowStatus.RUNNING:
                self._state.status = WorkflowStatus.COMPLETED

        except Exception as e:
            logger.exception(f"Workflow failed: {e}")
            self._state.status = WorkflowStatus.FAILED
            self._state.error = str(e)

        finally:
            self._state.completed_at = datetime.now(UTC)
            self._update_progress()

        logger.info(
            f"Workflow {self.workflow_type} completed with status: {self._state.status.value}"
        )

        return self._state

    async def resume(self, state: WorkflowState) -> WorkflowState:
        """Resume a paused or failed workflow."""
        self._state = state
        self._state.status = WorkflowStatus.RUNNING

        # Find first non-completed step
        start_index = 0
        for i, step in enumerate(self._state.steps):
            if step.status not in (StepStatus.COMPLETED, StepStatus.SKIPPED):
                start_index = i
                break

        logger.info(f"Resuming workflow from step {start_index}")

        # Continue execution from that point
        for i in range(start_index, len(self._state.steps)):
            step = self._state.steps[i]
            if self._cancelled:
                step.status = StepStatus.CANCELLED
                break

            self._state.current_step_index = i

            result = await self._execute_step(step)
            step.result = result
            step.completed_at = datetime.now(UTC)

            if result.success:
                step.status = StepStatus.COMPLETED
                if result.data and isinstance(result.data, dict):
                    self._state.context.update(result.data)
            else:
                step.status = StepStatus.FAILED
                self._state.status = WorkflowStatus.FAILED
                self._state.error = result.error
                break

            self._update_progress()

        if self._state.status == WorkflowStatus.RUNNING:
            self._state.status = WorkflowStatus.COMPLETED

        self._state.completed_at = datetime.now(UTC)
        return self._state


class WorkflowRegistry:
    """Registry for workflow types."""

    _workflows: dict[str, type] = {}

    @classmethod
    def register(cls, workflow_class: type) -> type:
        """Register a workflow class."""
        instance = workflow_class()
        cls._workflows[instance.workflow_type] = workflow_class
        return workflow_class

    @classmethod
    def get(cls, workflow_type: str) -> type | None:
        """Get a workflow class by type."""
        return cls._workflows.get(workflow_type)

    @classmethod
    def list_types(cls) -> list[str]:
        """List all registered workflow types."""
        return list(cls._workflows.keys())
