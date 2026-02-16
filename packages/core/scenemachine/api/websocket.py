"""WebSocket manager for real-time updates.

Provides real-time communication for:
- Generation progress updates
- Job status changes
- Queue updates
- System notifications
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """WebSocket event types."""

    # Connection events
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

    # Generation events
    JOB_QUEUED = "job.queued"
    JOB_STARTED = "job.started"
    JOB_PROGRESS = "job.progress"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_CANCELLED = "job.cancelled"

    # Queue events
    QUEUE_UPDATED = "queue.updated"
    QUEUE_CLEARED = "queue.cleared"

    # Project events
    PROJECT_UPDATED = "project.updated"
    SCENE_UPDATED = "scene.updated"
    SHOT_UPDATED = "shot.updated"

    # System events
    SYSTEM_NOTIFICATION = "system.notification"
    PROVIDER_STATUS = "provider.status"

    # Live Studio Mode events
    STUDIO_USER_JOINED = "studio.user.joined"
    STUDIO_USER_LEFT = "studio.user.left"
    STUDIO_CURSOR_MOVE = "studio.cursor.move"
    STUDIO_SELECTION_CHANGE = "studio.selection.change"
    STUDIO_EDIT_START = "studio.edit.start"
    STUDIO_EDIT_END = "studio.edit.end"
    STUDIO_EDIT_CONFLICT = "studio.edit.conflict"
    STUDIO_CHAT_MESSAGE = "studio.chat.message"
    STUDIO_PREVIEW_UPDATE = "studio.preview.update"
    STUDIO_TIMELINE_SYNC = "studio.timeline.sync"

    # AI Co-pilot events
    COPILOT_SUGGESTION = "copilot.suggestion"
    COPILOT_VOICE_COMMAND = "copilot.voice.command"
    COPILOT_RESPONSE = "copilot.response"

    # ActCore events
    BOOKING_STATUS_CHANGE = "booking.status.change"
    PERFORMER_MATCHED = "performer.matched"
    DELIVERY_RECEIVED = "delivery.received"

    # Agentic Crew events
    AGENT_ACTION = "agent.action"
    PIPELINE_STAGE_CHANGED = "pipeline.stage.changed"
    PIPELINE_PROGRESS = "pipeline.progress"
    APPROVAL_REQUIRED = "approval.required"


@dataclass
class WebSocketEvent:
    """WebSocket event payload."""

    type: EventType
    data: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    project_id: Optional[str] = None
    job_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "project_id": self.project_id,
            "job_id": self.job_id,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        # All active connections
        self.active_connections: dict[str, WebSocket] = {}
        # Project-specific subscriptions: project_id -> set of connection_ids
        self.project_subscriptions: dict[str, set[str]] = {}
        # Job-specific subscriptions: job_id -> set of connection_ids
        self.job_subscriptions: dict[str, set[str]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, connection_id: str) -> None:
        """Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            connection_id: Unique identifier for the connection
        """
        await websocket.accept()
        async with self._lock:
            self.active_connections[connection_id] = websocket
        logger.info(f"WebSocket connected: {connection_id}")

        # Send welcome event
        await self.send_personal(
            connection_id,
            WebSocketEvent(
                type=EventType.CONNECTED,
                data={"connection_id": connection_id, "message": "Connected to SceneMachine"},
            ),
        )

    async def disconnect(self, connection_id: str) -> None:
        """Handle WebSocket disconnection.

        Args:
            connection_id: The connection to disconnect
        """
        async with self._lock:
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]

            # Remove from all subscriptions
            for project_id in list(self.project_subscriptions.keys()):
                self.project_subscriptions[project_id].discard(connection_id)
                if not self.project_subscriptions[project_id]:
                    del self.project_subscriptions[project_id]

            for job_id in list(self.job_subscriptions.keys()):
                self.job_subscriptions[job_id].discard(connection_id)
                if not self.job_subscriptions[job_id]:
                    del self.job_subscriptions[job_id]

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def subscribe_to_project(self, connection_id: str, project_id: str) -> None:
        """Subscribe a connection to project updates.

        Args:
            connection_id: The connection ID
            project_id: The project to subscribe to
        """
        async with self._lock:
            if project_id not in self.project_subscriptions:
                self.project_subscriptions[project_id] = set()
            self.project_subscriptions[project_id].add(connection_id)
        logger.debug(f"Connection {connection_id} subscribed to project {project_id}")

    async def subscribe_to_job(self, connection_id: str, job_id: str) -> None:
        """Subscribe a connection to job updates.

        Args:
            connection_id: The connection ID
            job_id: The job to subscribe to
        """
        async with self._lock:
            if job_id not in self.job_subscriptions:
                self.job_subscriptions[job_id] = set()
            self.job_subscriptions[job_id].add(connection_id)
        logger.debug(f"Connection {connection_id} subscribed to job {job_id}")

    async def unsubscribe_from_project(self, connection_id: str, project_id: str) -> None:
        """Unsubscribe a connection from project updates."""
        async with self._lock:
            if project_id in self.project_subscriptions:
                self.project_subscriptions[project_id].discard(connection_id)

    async def unsubscribe_from_job(self, connection_id: str, job_id: str) -> None:
        """Unsubscribe a connection from job updates."""
        async with self._lock:
            if job_id in self.job_subscriptions:
                self.job_subscriptions[job_id].discard(connection_id)

    async def send_personal(self, connection_id: str, event: WebSocketEvent) -> bool:
        """Send event to a specific connection.

        Args:
            connection_id: The target connection
            event: The event to send

        Returns:
            True if sent successfully, False otherwise
        """
        websocket = self.active_connections.get(connection_id)
        if websocket:
            try:
                await websocket.send_text(event.to_json())
                return True
            except Exception as e:
                logger.error(f"Failed to send to {connection_id}: {e}")
                await self.disconnect(connection_id)
        return False

    async def broadcast(self, event: WebSocketEvent) -> int:
        """Broadcast event to all connected clients.

        Args:
            event: The event to broadcast

        Returns:
            Number of clients that received the message
        """
        sent_count = 0
        disconnected = []

        for connection_id, websocket in list(self.active_connections.items()):
            try:
                await websocket.send_text(event.to_json())
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to broadcast to {connection_id}: {e}")
                disconnected.append(connection_id)

        # Clean up disconnected clients
        for connection_id in disconnected:
            await self.disconnect(connection_id)

        return sent_count

    async def broadcast_to_project(self, project_id: str, event: WebSocketEvent) -> int:
        """Broadcast event to all subscribers of a project.

        Args:
            project_id: The project ID
            event: The event to broadcast

        Returns:
            Number of clients that received the message
        """
        event.project_id = project_id
        sent_count = 0
        connection_ids = self.project_subscriptions.get(project_id, set())

        for connection_id in list(connection_ids):
            if await self.send_personal(connection_id, event):
                sent_count += 1

        return sent_count

    async def broadcast_to_job(self, job_id: str, event: WebSocketEvent) -> int:
        """Broadcast event to all subscribers of a job.

        Args:
            job_id: The job ID
            event: The event to broadcast

        Returns:
            Number of clients that received the message
        """
        event.job_id = job_id
        sent_count = 0
        connection_ids = self.job_subscriptions.get(job_id, set())

        for connection_id in list(connection_ids):
            if await self.send_personal(connection_id, event):
                sent_count += 1

        return sent_count

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)

    def get_project_subscriber_count(self, project_id: str) -> int:
        """Get the number of subscribers to a project."""
        return len(self.project_subscriptions.get(project_id, set()))


# Global connection manager instance
manager = ConnectionManager()


# Convenience functions for emitting events
async def emit_job_queued(
    job_id: str,
    shot_id: str,
    project_id: str,
    position: int,
) -> None:
    """Emit job queued event."""
    event = WebSocketEvent(
        type=EventType.JOB_QUEUED,
        data={
            "job_id": job_id,
            "shot_id": shot_id,
            "position": position,
        },
        project_id=project_id,
        job_id=job_id,
    )
    await manager.broadcast_to_project(project_id, event)


async def emit_job_started(
    job_id: str,
    shot_id: str,
    project_id: str,
    provider: str,
) -> None:
    """Emit job started event."""
    event = WebSocketEvent(
        type=EventType.JOB_STARTED,
        data={
            "job_id": job_id,
            "shot_id": shot_id,
            "provider": provider,
        },
        project_id=project_id,
        job_id=job_id,
    )
    await manager.broadcast_to_project(project_id, event)
    await manager.broadcast_to_job(job_id, event)


async def emit_job_progress(
    job_id: str,
    shot_id: str,
    project_id: str,
    progress: float,
    message: Optional[str] = None,
) -> None:
    """Emit job progress event."""
    event = WebSocketEvent(
        type=EventType.JOB_PROGRESS,
        data={
            "job_id": job_id,
            "shot_id": shot_id,
            "progress": progress,
            "message": message,
        },
        project_id=project_id,
        job_id=job_id,
    )
    await manager.broadcast_to_project(project_id, event)
    await manager.broadcast_to_job(job_id, event)


async def emit_job_completed(
    job_id: str,
    shot_id: str,
    project_id: str,
    output_path: str,
    thumbnail_path: Optional[str] = None,
    duration_seconds: Optional[float] = None,
) -> None:
    """Emit job completed event."""
    event = WebSocketEvent(
        type=EventType.JOB_COMPLETED,
        data={
            "job_id": job_id,
            "shot_id": shot_id,
            "output_path": output_path,
            "thumbnail_path": thumbnail_path,
            "duration_seconds": duration_seconds,
        },
        project_id=project_id,
        job_id=job_id,
    )
    await manager.broadcast_to_project(project_id, event)
    await manager.broadcast_to_job(job_id, event)


async def emit_job_failed(
    job_id: str,
    shot_id: str,
    project_id: str,
    error_message: str,
    error_code: Optional[str] = None,
    retry_count: int = 0,
) -> None:
    """Emit job failed event."""
    event = WebSocketEvent(
        type=EventType.JOB_FAILED,
        data={
            "job_id": job_id,
            "shot_id": shot_id,
            "error_message": error_message,
            "error_code": error_code,
            "retry_count": retry_count,
        },
        project_id=project_id,
        job_id=job_id,
    )
    await manager.broadcast_to_project(project_id, event)
    await manager.broadcast_to_job(job_id, event)


async def emit_queue_updated(project_id: str, queue_stats: dict[str, Any]) -> None:
    """Emit queue updated event."""
    event = WebSocketEvent(
        type=EventType.QUEUE_UPDATED,
        data=queue_stats,
        project_id=project_id,
    )
    await manager.broadcast_to_project(project_id, event)


async def emit_system_notification(
    title: str,
    message: str,
    level: str = "info",
    project_id: Optional[str] = None,
) -> None:
    """Emit system notification event."""
    event = WebSocketEvent(
        type=EventType.SYSTEM_NOTIFICATION,
        data={
            "title": title,
            "message": message,
            "level": level,
        },
        project_id=project_id,
    )
    if project_id:
        await manager.broadcast_to_project(project_id, event)
    else:
        await manager.broadcast(event)


async def emit_agent_action(
    agent_type: str,
    agent_name: str,
    action: str,
    status: str,
    project_id: Optional[str] = None,
    confidence: float = 1.0,
    cost_usd: float = 0.0,
    details: Optional[dict] = None,
) -> None:
    """Emit an agent action event for the activity feed."""
    event = WebSocketEvent(
        type=EventType.AGENT_ACTION,
        data={
            "agent_type": agent_type,
            "agent_name": agent_name,
            "action": action,
            "status": status,
            "confidence": confidence,
            "cost_usd": cost_usd,
            "details": details or {},
        },
        project_id=project_id,
    )
    if project_id:
        await manager.broadcast_to_project(project_id, event)
    else:
        await manager.broadcast(event)


async def emit_pipeline_stage(
    project_id: str,
    stage: str,
    progress_percent: float,
    total_cost_usd: float = 0.0,
    message: Optional[str] = None,
) -> None:
    """Emit pipeline stage change event."""
    event = WebSocketEvent(
        type=EventType.PIPELINE_STAGE_CHANGED,
        data={
            "stage": stage,
            "progress_percent": progress_percent,
            "total_cost_usd": total_cost_usd,
            "message": message,
        },
        project_id=project_id,
    )
    await manager.broadcast_to_project(project_id, event)


async def emit_approval_required(
    approval_id: str,
    agent_type: str,
    action_type: str,
    description: str,
    project_id: Optional[str] = None,
) -> None:
    """Emit approval required event for HITL queue."""
    event = WebSocketEvent(
        type=EventType.APPROVAL_REQUIRED,
        data={
            "approval_id": approval_id,
            "agent_type": agent_type,
            "action_type": action_type,
            "description": description,
        },
        project_id=project_id,
    )
    if project_id:
        await manager.broadcast_to_project(project_id, event)
    else:
        await manager.broadcast(event)
