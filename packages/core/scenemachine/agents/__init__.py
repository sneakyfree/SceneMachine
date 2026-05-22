"""SceneMachine Agentic Crew.

Provides autonomous agents for the screenplay-to-movie pipeline:
- OrchestratorAgent: Coordinates the full pipeline
- ParserAgent: Parses screenplays and generates shot lists
- CharacterAgent: Manages character consistency
- GeneratorAgent: Handles video generation
- AssemblerAgent: Assembles clips into scenes/movies
- ReviewerAgent: Quality control and issue flagging
- ExportAgent: Format conversion, compression, and distribution
"""

from scenemachine.agents.assembler_agent import AssemblerAgent
from scenemachine.agents.base import (
    ActionContext,
    ActionLog,
    ActionResult,
    ActionStatus,
    AgentActionLogger,
    AgentType,
    BaseAgent,
    EscalationReason,
)
from scenemachine.agents.character_agent import CharacterAgent
from scenemachine.agents.export_agent import ExportAgent
from scenemachine.agents.generator_agent import GeneratorAgent
from scenemachine.agents.orchestrator import OrchestratorAgent, PipelineState
from scenemachine.agents.parser_agent import ParserAgent
from scenemachine.agents.reviewer_agent import ReviewerAgent

__all__ = [
    # Base classes
    "BaseAgent",
    "AgentType",
    "ActionStatus",
    "ActionContext",
    "ActionResult",
    "ActionLog",
    "AgentActionLogger",
    "EscalationReason",
    # Specialist agents
    "ParserAgent",
    "CharacterAgent",
    "GeneratorAgent",
    "AssemblerAgent",
    "ReviewerAgent",
    "ExportAgent",
    # Orchestrator
    "OrchestratorAgent",
    "PipelineState",
]
