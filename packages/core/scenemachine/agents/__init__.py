"""SceneMachine Agentic Crew.

Provides autonomous agents for the screenplay-to-movie pipeline:
- OrchestratorAgent: Coordinates the full pipeline
- ParserAgent: Parses screenplays and generates shot lists
- CharacterAgent: Manages character consistency
- GeneratorAgent: Handles video generation
- AssemblerAgent: Assembles clips into scenes/movies
- ReviewerAgent: Quality control and issue flagging
"""

from scenemachine.agents.base import (
    BaseAgent,
    AgentType,
    ActionStatus,
    ActionContext,
    ActionResult,
    ActionLog,
    AgentActionLogger,
    EscalationReason,
)
from scenemachine.agents.parser_agent import ParserAgent
from scenemachine.agents.character_agent import CharacterAgent
from scenemachine.agents.generator_agent import GeneratorAgent
from scenemachine.agents.assembler_agent import AssemblerAgent
from scenemachine.agents.reviewer_agent import ReviewerAgent
from scenemachine.agents.orchestrator import OrchestratorAgent, PipelineState

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
    # Orchestrator
    "OrchestratorAgent",
    "PipelineState",
]

