"""Tests for the workflow orchestration framework."""

import pytest
from dataclasses import dataclass
from typing import Any, Dict, List
from uuid import uuid4

from scenemachine.workflows.base import (
    Workflow,
    WorkflowRegistry,
    WorkflowStep,
    WorkflowStatus,
    StepStatus,
    StepResult,
)


# Test workflow implementation
@dataclass
class TestWorkflowContext:
    """Context for test workflow."""
    value: int = 0
    processed: bool = False


class SimpleTestWorkflow(Workflow[TestWorkflowContext]):
    """Simple test workflow for testing."""

    @property
    def workflow_type(self) -> str:
        return "test_simple"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                id="step1",
                name="Step 1",
                description="First step",
                handler="step_one",
            ),
            WorkflowStep(
                id="step2",
                name="Step 2",
                description="Second step",
                handler="step_two",
                dependencies=["step1"],
            ),
            WorkflowStep(
                id="step3",
                name="Step 3",
                description="Third step",
                handler="step_three",
                dependencies=["step2"],
            ),
        ]

    async def step_one(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"step1_done": True, "value": context.get("value", 0) + 1}

    async def step_two(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"step2_done": True, "value": context.get("value", 0) + 10}

    async def step_three(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"step3_done": True, "processed": True}


class FailingWorkflow(Workflow[TestWorkflowContext]):
    """Workflow that fails at step 2."""

    @property
    def workflow_type(self) -> str:
        return "test_failing"

    def define_steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                id="step1",
                name="Step 1",
                description="First step",
                handler="step_one",
            ),
            WorkflowStep(
                id="step2",
                name="Step 2",
                description="Failing step",
                handler="step_fail",
                dependencies=["step1"],
                max_retries=1,
            ),
        ]

    async def step_one(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"step1_done": True}

    async def step_fail(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise ValueError("This step always fails")


class TestWorkflowExecution:
    """Tests for workflow execution."""

    @pytest.mark.asyncio
    async def test_simple_workflow_executes(self) -> None:
        """Test that a simple workflow executes all steps."""
        context = TestWorkflowContext(value=5)
        workflow = SimpleTestWorkflow(context=context)

        state = await workflow.execute()

        assert state.status == WorkflowStatus.COMPLETED
        assert len(state.completed_steps) == 3
        assert all(s.status == StepStatus.COMPLETED for s in state.steps)

    @pytest.mark.asyncio
    async def test_workflow_context_updates(self) -> None:
        """Test that workflow context is updated after each step."""
        context = TestWorkflowContext(value=0)
        workflow = SimpleTestWorkflow(context=context)

        state = await workflow.execute()

        # Context should have been updated by steps
        assert state.context.get("step1_done") is True
        assert state.context.get("step2_done") is True
        assert state.context.get("step3_done") is True
        assert state.context.get("processed") is True

    @pytest.mark.asyncio
    async def test_workflow_progress_tracking(self) -> None:
        """Test that workflow progress is tracked."""
        workflow = SimpleTestWorkflow()
        progress_values = []

        workflow.on_progress(lambda s: progress_values.append(s.progress_percent))

        await workflow.execute()

        assert len(progress_values) > 0
        assert progress_values[-1] == 100.0

    @pytest.mark.asyncio
    async def test_workflow_step_callbacks(self) -> None:
        """Test that step completion callbacks are called."""
        workflow = SimpleTestWorkflow()
        completed_steps = []

        workflow.on_step_complete(lambda s: completed_steps.append(s.id))

        await workflow.execute()

        assert "step1" in completed_steps
        assert "step2" in completed_steps
        assert "step3" in completed_steps

    @pytest.mark.asyncio
    async def test_workflow_can_be_cancelled(self) -> None:
        """Test that a workflow can be cancelled."""
        workflow = SimpleTestWorkflow()

        # Cancel immediately
        workflow.cancel()
        state = await workflow.execute()

        # Should have cancelled status
        assert state.status == WorkflowStatus.CANCELLED


class TestWorkflowFailure:
    """Tests for workflow failure handling."""

    @pytest.mark.asyncio
    async def test_failing_workflow(self) -> None:
        """Test that a failing workflow reports failure."""
        workflow = FailingWorkflow()

        state = await workflow.execute()

        assert state.status == WorkflowStatus.FAILED
        assert state.error is not None
        assert "always fails" in state.error.lower()

    @pytest.mark.asyncio
    async def test_failed_step_retries(self) -> None:
        """Test that failed steps are retried."""
        workflow = FailingWorkflow()

        state = await workflow.execute()

        # Step 2 should have retried
        step2 = state.steps[1]
        assert step2.retries > 0

    @pytest.mark.asyncio
    async def test_completed_steps_on_failure(self) -> None:
        """Test that completed steps are preserved on failure."""
        workflow = FailingWorkflow()

        state = await workflow.execute()

        # Step 1 should be completed even though workflow failed
        step1 = state.steps[0]
        assert step1.status == StepStatus.COMPLETED


class TestWorkflowState:
    """Tests for workflow state management."""

    @pytest.mark.asyncio
    async def test_state_serialization(self) -> None:
        """Test that workflow state can be serialized."""
        workflow = SimpleTestWorkflow()
        state = await workflow.execute()

        state_dict = state.to_dict()

        assert "workflowId" in state_dict
        assert "workflowType" in state_dict
        assert "status" in state_dict
        assert "steps" in state_dict
        assert len(state_dict["steps"]) == 3

    @pytest.mark.asyncio
    async def test_state_duration_tracking(self) -> None:
        """Test that workflow duration is tracked."""
        workflow = SimpleTestWorkflow()
        state = await workflow.execute()

        assert state.duration_seconds is not None
        assert state.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_step_duration_tracking(self) -> None:
        """Test that step duration is tracked."""
        workflow = SimpleTestWorkflow()
        state = await workflow.execute()

        for step in state.steps:
            assert step.duration_seconds is not None
            assert step.duration_seconds >= 0


class TestWorkflowRegistry:
    """Tests for workflow registry."""

    def test_register_workflow(self) -> None:
        """Test registering a workflow."""
        # Register happens via decorator
        workflow_type = WorkflowRegistry.get("test_simple")
        assert workflow_type is not None

    def test_list_workflow_types(self) -> None:
        """Test listing registered workflow types."""
        types = WorkflowRegistry.list_types()
        assert isinstance(types, list)

    def test_get_nonexistent_workflow(self) -> None:
        """Test getting a nonexistent workflow type."""
        workflow_type = WorkflowRegistry.get("nonexistent")
        assert workflow_type is None


class TestWorkflowDependencies:
    """Tests for step dependencies."""

    @pytest.mark.asyncio
    async def test_dependencies_are_respected(self) -> None:
        """Test that step dependencies are respected."""
        workflow = SimpleTestWorkflow()
        step_order = []

        workflow.on_step_complete(lambda s: step_order.append(s.id))

        await workflow.execute()

        # Steps should execute in dependency order
        assert step_order.index("step1") < step_order.index("step2")
        assert step_order.index("step2") < step_order.index("step3")


class TestStepResult:
    """Tests for step result."""

    def test_successful_result(self) -> None:
        """Test creating a successful result."""
        result = StepResult(
            success=True,
            data={"key": "value"},
            duration_seconds=1.5,
        )

        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_failed_result(self) -> None:
        """Test creating a failed result."""
        result = StepResult(
            success=False,
            error="Something went wrong",
            duration_seconds=0.5,
        )

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None
