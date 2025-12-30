"""Workflow definitions and state management."""

from scenemachine.workflows.base import (
    StepResult,
    StepStatus,
    Workflow,
    WorkflowRegistry,
    WorkflowState,
    WorkflowStatus,
    WorkflowStep,
)
from scenemachine.workflows.export import (
    ExportWorkflow,
    ExportWorkflowContext,
    QuickExportContext,
    QuickExportWorkflow,
)
from scenemachine.workflows.generation import (
    BatchRegenerationContext,
    BatchRegenerationWorkflow,
    GenerationWorkflowContext,
    VideoGenerationWorkflow,
)
from scenemachine.workflows.screenplay import (
    ScreenplayProcessingWorkflow,
    ScreenplayWorkflowContext,
)

__all__ = [
    # Base
    "Workflow",
    "WorkflowStep",
    "WorkflowState",
    "WorkflowStatus",
    "StepStatus",
    "StepResult",
    "WorkflowRegistry",
    # Screenplay
    "ScreenplayProcessingWorkflow",
    "ScreenplayWorkflowContext",
    # Generation
    "VideoGenerationWorkflow",
    "GenerationWorkflowContext",
    "BatchRegenerationWorkflow",
    "BatchRegenerationContext",
    # Export
    "ExportWorkflow",
    "ExportWorkflowContext",
    "QuickExportWorkflow",
    "QuickExportContext",
]
