"""
SceneMachine Agentic Crew - Base Agent Framework

This module provides the foundational Agent class for the SceneMachine
agentic architecture. Agents are bounded autonomous workers that can:
- Execute tasks within defined guardrails
- Log all actions for audit purposes
- Escalate to humans when confidence is low
- Communicate through a shared message bus

Design principles (from DNA Strand Master Plan):
- No hallucination: Cannot invent content not in source
- Uncertainty triggers REFER: Confidence <0.6 escalates to human
- Source-label everything: Every action has provenance
- Immutable audit trail: All actions logged
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Types of agents in the SceneMachine crew."""
    ORCHESTRATOR = "orchestrator"
    PARSER = "parser"
    CHARACTER = "character"
    GENERATOR = "generator"
    ASSEMBLER = "assembler"
    REVIEWER = "reviewer"
    EXPORT = "export"


class ActionStatus(Enum):
    """Status of an agent action."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"  # Requires human approval
    CANCELLED = "cancelled"


class EscalationReason(Enum):
    """Reasons for escalating to human."""
    LOW_CONFIDENCE = "low_confidence"
    BUDGET_EXCEEDED = "budget_exceeded"
    SENSITIVE_CONTENT = "sensitive_content"
    REAL_PERSON_LIKENESS = "real_person_likeness"
    EXPLICIT_REQUEST = "explicit_request"
    AMBIGUOUS_INPUT = "ambiguous_input"
    ERROR_RECOVERY = "error_recovery"


@dataclass
class ActionContext:
    """Context passed to agent actions."""
    project_id: UUID
    user_id: Optional[UUID] = None
    session_id: UUID = field(default_factory=uuid4)
    budget_remaining_usd: float = 100.0
    dry_run: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    """Result of an agent action."""
    action_id: UUID
    status: ActionStatus
    success: bool
    output: Any = None
    error_message: Optional[str] = None
    confidence: float = 1.0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    escalation_reason: Optional[EscalationReason] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionLog:
    """Immutable log entry for an agent action."""
    id: UUID
    agent_type: AgentType
    agent_name: str
    action_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: ActionStatus = ActionStatus.PENDING
    input_summary: str = ""
    output_summary: str = ""
    confidence: float = 1.0
    cost_usd: float = 0.0
    error_message: Optional[str] = None
    escalation_reason: Optional[EscalationReason] = None
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "agent_type": self.agent_type.value,
            "agent_name": self.agent_name,
            "action_name": self.action_name,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "confidence": self.confidence,
            "cost_usd": self.cost_usd,
            "error_message": self.error_message,
            "escalation_reason": self.escalation_reason.value if self.escalation_reason else None,
            "provenance": self.provenance,
        }


class AgentActionLogger:
    """
    Centralized action logging for audit trail.
    
    All agent actions are logged here for:
    - Audit compliance
    - Debugging
    - Cost tracking
    - Reproducibility
    """
    
    _instance = None
    _logs: List[ActionLog] = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._logs = []
        return cls._instance
    
    def log_action(self, log_entry: ActionLog) -> None:
        """Add an action log entry."""
        self._logs.append(log_entry)
        logger.info(
            f"[{log_entry.agent_type.value}] {log_entry.action_name}: "
            f"{log_entry.status.value} (confidence={log_entry.confidence:.2f})"
        )
    
    def get_logs(
        self,
        agent_type: Optional[AgentType] = None,
        limit: int = 100,
    ) -> List[ActionLog]:
        """Get action logs, optionally filtered by agent type."""
        logs = self._logs
        if agent_type:
            logs = [l for l in logs if l.agent_type == agent_type]
        return logs[-limit:]
    
    def get_total_cost(self) -> float:
        """Get total cost of all logged actions."""
        return sum(log.cost_usd for log in self._logs)
    
    def clear(self) -> None:
        """Clear all logs (for testing only)."""
        self._logs = []


# Type for approval callbacks
ApprovalCallback = Callable[[str, Dict[str, Any]], bool]


class BaseAgent(ABC):
    """
    Abstract base class for all SceneMachine agents.
    
    Provides:
    - Guardrails enforcement
    - Action logging
    - Human escalation
    - Confidence-based decision making
    """
    
    # Class-level configuration
    CONFIDENCE_THRESHOLD = 0.6  # Below this, escalate to human
    MAX_RETRIES = 3
    
    def __init__(
        self,
        name: Optional[str] = None,
        approval_callback: Optional[ApprovalCallback] = None,
    ):
        self.id = uuid4()
        self.name = name or f"{self.agent_type.value}_{str(self.id)[:8]}"
        self._logger = AgentActionLogger()
        self._approval_callback = approval_callback
        self._is_running = False
    
    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        """Return list of capabilities this agent provides."""
        pass
    
    @property
    def can_act_autonomously(self) -> List[str]:
        """
        Actions that can be performed without human approval.
        Override in subclasses to restrict autonomy.
        """
        return self.capabilities
    
    @property
    def requires_approval(self) -> List[str]:
        """
        Actions that always require human approval.
        Override in subclasses to add approval gates.
        """
        return []
    
    async def execute(
        self,
        action_name: str,
        context: ActionContext,
        **kwargs,
    ) -> ActionResult:
        """
        Execute an action with full guardrails.
        
        This is the main entry point for all agent actions.
        """
        action_id = uuid4()
        start_time = datetime.now(timezone.utc)
        
        # Create log entry
        log_entry = ActionLog(
            id=action_id,
            agent_type=self.agent_type,
            agent_name=self.name,
            action_name=action_name,
            started_at=start_time,
            status=ActionStatus.RUNNING,
            input_summary=self._summarize_input(action_name, kwargs),
            provenance={"context": str(context.session_id)},
        )
        self._logger.log_action(log_entry)
        
        try:
            # Check if action requires approval
            if action_name in self.requires_approval:
                approved = await self._request_approval(
                    action_name,
                    EscalationReason.EXPLICIT_REQUEST,
                    kwargs,
                )
                if not approved:
                    log_entry.status = ActionStatus.ESCALATED
                    log_entry.escalation_reason = EscalationReason.EXPLICIT_REQUEST
                    return ActionResult(
                        action_id=action_id,
                        status=ActionStatus.ESCALATED,
                        success=False,
                        escalation_reason=EscalationReason.EXPLICIT_REQUEST,
                    )
            
            # Check budget
            if context.budget_remaining_usd <= 0:
                approved = await self._request_approval(
                    action_name,
                    EscalationReason.BUDGET_EXCEEDED,
                    {"budget_remaining": context.budget_remaining_usd},
                )
                if not approved:
                    log_entry.status = ActionStatus.ESCALATED
                    log_entry.escalation_reason = EscalationReason.BUDGET_EXCEEDED
                    return ActionResult(
                        action_id=action_id,
                        status=ActionStatus.ESCALATED,
                        success=False,
                        escalation_reason=EscalationReason.BUDGET_EXCEEDED,
                    )
            
            # Execute the actual action
            self._is_running = True
            result = await self._execute_action(action_name, context, **kwargs)
            
            # Check confidence threshold
            if result.confidence < self.CONFIDENCE_THRESHOLD:
                approved = await self._request_approval(
                    action_name,
                    EscalationReason.LOW_CONFIDENCE,
                    {"confidence": result.confidence, "output": result.output},
                )
                if not approved:
                    result.status = ActionStatus.ESCALATED
                    result.escalation_reason = EscalationReason.LOW_CONFIDENCE
            
            # Update log entry
            log_entry.completed_at = datetime.now(timezone.utc)
            log_entry.status = result.status
            log_entry.confidence = result.confidence
            log_entry.cost_usd = result.cost_usd
            log_entry.output_summary = self._summarize_output(result.output)
            
            return result
            
        except Exception as e:
            logger.exception(f"Agent {self.name} failed on {action_name}: {e}")
            log_entry.completed_at = datetime.now(timezone.utc)
            log_entry.status = ActionStatus.FAILED
            log_entry.error_message = str(e)
            
            return ActionResult(
                action_id=action_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=str(e),
            )
        finally:
            self._is_running = False
    
    @abstractmethod
    async def _execute_action(
        self,
        action_name: str,
        context: ActionContext,
        **kwargs,
    ) -> ActionResult:
        """
        Execute the actual action logic.
        
        Subclasses implement this to define their behavior.
        """
        pass
    
    async def _request_approval(
        self,
        action_name: str,
        reason: EscalationReason,
        details: Dict[str, Any],
    ) -> bool:
        """
        Request human approval for an action.
        
        Returns True if approved, False if rejected.
        """
        logger.warning(
            f"[{self.name}] Requesting approval for '{action_name}': {reason.value}"
        )
        
        if self._approval_callback:
            return self._approval_callback(
                f"{self.name}:{action_name}",
                {"reason": reason.value, **details},
            )
        
        # Default: auto-approve in dry run, reject otherwise
        return False
    
    def _summarize_input(self, action_name: str, kwargs: Dict[str, Any]) -> str:
        """Create a brief summary of action input for logging."""
        parts = [action_name]
        for k, v in list(kwargs.items())[:3]:  # First 3 params
            v_str = str(v)[:50] + "..." if len(str(v)) > 50 else str(v)
            parts.append(f"{k}={v_str}")
        return ", ".join(parts)
    
    def _summarize_output(self, output: Any) -> str:
        """Create a brief summary of action output for logging."""
        if output is None:
            return "None"
        output_str = str(output)
        return output_str[:100] + "..." if len(output_str) > 100 else output_str
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, type={self.agent_type.value})>"
