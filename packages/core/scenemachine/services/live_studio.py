"""Live Studio Mode - Real-time collaborative editing service.

Provides multi-user collaboration for projects with:
- Real-time cursor tracking
- Edit locking with 30s expiry
- Operational transformation for scripts
- Timeline synchronization
- Chat and presence
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class EditLockType(StrEnum):
    """Types of edit locks."""

    SCRIPT_SECTION = "script_section"
    TIMELINE_CLIP = "timeline_clip"
    SHOT = "shot"
    SCENE = "scene"
    CHARACTER = "character"


@dataclass
class StudioUser:
    """Represents a user in a live studio session."""

    user_id: str
    display_name: str
    avatar_url: str | None = None
    color: str = "#3B82F6"  # User color for cursors/selections
    cursor_position: dict[str, Any] | None = None
    selection: dict[str, Any] | None = None
    joined_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "color": self.color,
            "cursor_position": self.cursor_position,
            "selection": self.selection,
            "joined_at": self.joined_at.isoformat(),
            "is_active": self.is_active,
        }


@dataclass
class EditLock:
    """Represents a lock on an editable element."""

    lock_id: str
    lock_type: EditLockType
    resource_id: str
    user_id: str
    acquired_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(seconds=30))

    def is_expired(self) -> bool:
        """Check if lock has expired."""
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "lock_id": self.lock_id,
            "lock_type": self.lock_type.value,
            "resource_id": self.resource_id,
            "user_id": self.user_id,
            "acquired_at": self.acquired_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_expired": self.is_expired(),
        }


@dataclass
class ChatMessage:
    """Chat message in a studio session."""

    message_id: str
    user_id: str
    user_name: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    message_type: str = "text"  # text, system, notification

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "message_type": self.message_type,
        }


@dataclass
class StudioSession:
    """Represents an active studio collaboration session."""

    session_id: str
    project_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    users: dict[str, StudioUser] = field(default_factory=dict)
    edit_locks: dict[str, EditLock] = field(default_factory=dict)
    chat_history: list[ChatMessage] = field(default_factory=list)
    timeline_state: dict[str, Any] | None = None
    preview_state: dict[str, Any] | None = None

    def get_active_users(self) -> list[StudioUser]:
        """Get list of active users."""
        return [u for u in self.users.values() if u.is_active]

    def get_user_count(self) -> int:
        """Get count of active users."""
        return len(self.get_active_users())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "project_id": self.project_id,
            "created_at": self.created_at.isoformat(),
            "user_count": self.get_user_count(),
            "users": [u.to_dict() for u in self.get_active_users()],
            "active_locks": [l.to_dict() for l in self.edit_locks.values() if not l.is_expired()],
        }


class LiveStudioService:
    """Service for managing live studio collaboration sessions.

    Features:
    - Multi-user presence tracking
    - Edit locking with automatic expiry
    - Real-time cursor synchronization
    - Chat functionality
    - Timeline state synchronization
    """

    _instance: Optional["LiveStudioService"] = None

    # Colors for user cursors (cycle through these)
    USER_COLORS = [
        "#3B82F6",  # Blue
        "#10B981",  # Green
        "#F59E0B",  # Amber
        "#EF4444",  # Red
        "#8B5CF6",  # Purple
        "#EC4899",  # Pink
        "#06B6D4",  # Cyan
        "#F97316",  # Orange
    ]

    # Lock expiry duration
    LOCK_DURATION = timedelta(seconds=30)

    # Inactivity timeout
    INACTIVITY_TIMEOUT = timedelta(minutes=5)

    def __init__(self) -> None:
        self._sessions: dict[str, StudioSession] = {}  # project_id -> session
        self._user_sessions: dict[str, str] = {}  # user_id -> project_id
        self._color_assignments: dict[str, int] = {}  # project_id -> next_color_index
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> "LiveStudioService":
        """Get singleton service instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_next_color(self, project_id: str) -> str:
        """Get next color for a user in a project."""
        if project_id not in self._color_assignments:
            self._color_assignments[project_id] = 0

        color_index = self._color_assignments[project_id]
        self._color_assignments[project_id] = (color_index + 1) % len(self.USER_COLORS)
        return self.USER_COLORS[color_index]

    async def join_session(
        self,
        project_id: str,
        user_id: str,
        display_name: str,
        avatar_url: str | None = None,
    ) -> StudioSession:
        """Join or create a studio session for a project.

        Args:
            project_id: The project to join
            user_id: Unique user identifier
            display_name: User's display name
            avatar_url: Optional avatar URL

        Returns:
            The StudioSession object
        """
        async with self._lock:
            # Create session if doesn't exist
            if project_id not in self._sessions:
                self._sessions[project_id] = StudioSession(
                    session_id=str(uuid4()),
                    project_id=project_id,
                )

            session = self._sessions[project_id]

            # Check if user already in session
            if user_id in session.users:
                user = session.users[user_id]
                user.is_active = True
                user.last_activity = datetime.utcnow()
            else:
                # Add new user
                user = StudioUser(
                    user_id=user_id,
                    display_name=display_name,
                    avatar_url=avatar_url,
                    color=self._get_next_color(project_id),
                )
                session.users[user_id] = user

            # Track user's active session
            self._user_sessions[user_id] = project_id

            # Add system message
            session.chat_history.append(
                ChatMessage(
                    message_id=str(uuid4()),
                    user_id="system",
                    user_name="System",
                    content=f"{display_name} joined the session",
                    message_type="system",
                )
            )

            logger.info(f"User {user_id} joined studio session for project {project_id}")
            return session

    async def leave_session(self, project_id: str, user_id: str) -> StudioSession | None:
        """Leave a studio session.

        Args:
            project_id: The project to leave
            user_id: User leaving

        Returns:
            Updated session or None if session doesn't exist
        """
        async with self._lock:
            session = self._sessions.get(project_id)
            if not session:
                return None

            if user_id in session.users:
                user = session.users[user_id]
                user.is_active = False

                # Release any locks held by this user
                locks_to_remove = [
                    lock_id
                    for lock_id, lock in session.edit_locks.items()
                    if lock.user_id == user_id
                ]
                for lock_id in locks_to_remove:
                    del session.edit_locks[lock_id]

                # Add system message
                session.chat_history.append(
                    ChatMessage(
                        message_id=str(uuid4()),
                        user_id="system",
                        user_name="System",
                        content=f"{user.display_name} left the session",
                        message_type="system",
                    )
                )

            # Clean up user session tracking
            if user_id in self._user_sessions:
                del self._user_sessions[user_id]

            logger.info(f"User {user_id} left studio session for project {project_id}")
            return session

    async def update_cursor(
        self,
        project_id: str,
        user_id: str,
        cursor_position: dict[str, Any],
    ) -> bool:
        """Update a user's cursor position.

        Args:
            project_id: The project
            user_id: The user
            cursor_position: Cursor position data (x, y, element, etc.)

        Returns:
            True if updated successfully
        """
        session = self._sessions.get(project_id)
        if not session or user_id not in session.users:
            return False

        user = session.users[user_id]
        user.cursor_position = cursor_position
        user.last_activity = datetime.utcnow()
        return True

    async def update_selection(
        self,
        project_id: str,
        user_id: str,
        selection: dict[str, Any],
    ) -> bool:
        """Update a user's selection.

        Args:
            project_id: The project
            user_id: The user
            selection: Selection data (elements, range, etc.)

        Returns:
            True if updated successfully
        """
        session = self._sessions.get(project_id)
        if not session or user_id not in session.users:
            return False

        user = session.users[user_id]
        user.selection = selection
        user.last_activity = datetime.utcnow()
        return True

    async def acquire_lock(
        self,
        project_id: str,
        user_id: str,
        lock_type: EditLockType,
        resource_id: str,
    ) -> EditLock | None:
        """Acquire an edit lock on a resource.

        Args:
            project_id: The project
            user_id: User requesting lock
            lock_type: Type of lock
            resource_id: ID of the resource to lock

        Returns:
            EditLock if acquired, None if resource is already locked
        """
        async with self._lock:
            session = self._sessions.get(project_id)
            if not session:
                return None

            # Clean expired locks first
            self._clean_expired_locks(session)

            # Check if resource is already locked
            lock_key = f"{lock_type.value}:{resource_id}"
            existing_lock = session.edit_locks.get(lock_key)

            if existing_lock and existing_lock.user_id != user_id:
                logger.debug(f"Lock conflict: {lock_key} held by {existing_lock.user_id}")
                return None

            # Create or refresh lock
            new_lock = EditLock(
                lock_id=str(uuid4()),
                lock_type=lock_type,
                resource_id=resource_id,
                user_id=user_id,
                acquired_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + self.LOCK_DURATION,
            )

            session.edit_locks[lock_key] = new_lock
            logger.debug(f"Lock acquired: {lock_key} by {user_id}")
            return new_lock

    async def release_lock(
        self,
        project_id: str,
        user_id: str,
        lock_type: EditLockType,
        resource_id: str,
    ) -> bool:
        """Release an edit lock.

        Args:
            project_id: The project
            user_id: User releasing lock
            lock_type: Type of lock
            resource_id: ID of the resource

        Returns:
            True if released, False if not found or not owned
        """
        async with self._lock:
            session = self._sessions.get(project_id)
            if not session:
                return False

            lock_key = f"{lock_type.value}:{resource_id}"
            existing_lock = session.edit_locks.get(lock_key)

            if not existing_lock:
                return False

            if existing_lock.user_id != user_id:
                return False

            del session.edit_locks[lock_key]
            logger.debug(f"Lock released: {lock_key}")
            return True

    async def refresh_lock(
        self,
        project_id: str,
        user_id: str,
        lock_type: EditLockType,
        resource_id: str,
    ) -> EditLock | None:
        """Refresh an existing lock to extend its expiry.

        Args:
            project_id: The project
            user_id: User owning lock
            lock_type: Type of lock
            resource_id: ID of the resource

        Returns:
            Updated lock or None if not found/not owned
        """
        async with self._lock:
            session = self._sessions.get(project_id)
            if not session:
                return None

            lock_key = f"{lock_type.value}:{resource_id}"
            existing_lock = session.edit_locks.get(lock_key)

            if not existing_lock or existing_lock.user_id != user_id:
                return None

            existing_lock.expires_at = datetime.utcnow() + self.LOCK_DURATION
            return existing_lock

    def _clean_expired_locks(self, session: StudioSession) -> int:
        """Remove expired locks from a session.

        Returns:
            Number of locks removed
        """
        expired = [lock_key for lock_key, lock in session.edit_locks.items() if lock.is_expired()]

        for lock_key in expired:
            del session.edit_locks[lock_key]

        return len(expired)

    async def send_chat_message(
        self,
        project_id: str,
        user_id: str,
        content: str,
    ) -> ChatMessage | None:
        """Send a chat message in a session.

        Args:
            project_id: The project
            user_id: Sender
            content: Message content

        Returns:
            ChatMessage if sent, None if session not found
        """
        session = self._sessions.get(project_id)
        if not session or user_id not in session.users:
            return None

        user = session.users[user_id]
        message = ChatMessage(
            message_id=str(uuid4()),
            user_id=user_id,
            user_name=user.display_name,
            content=content,
            message_type="text",
        )

        session.chat_history.append(message)

        # Limit chat history to last 100 messages
        if len(session.chat_history) > 100:
            session.chat_history = session.chat_history[-100:]

        return message

    async def update_timeline_state(
        self,
        project_id: str,
        user_id: str,
        timeline_state: dict[str, Any],
    ) -> bool:
        """Update shared timeline state.

        Args:
            project_id: The project
            user_id: User making update
            timeline_state: New timeline state

        Returns:
            True if updated
        """
        session = self._sessions.get(project_id)
        if not session:
            return False

        session.timeline_state = {
            **timeline_state,
            "updated_by": user_id,
            "updated_at": datetime.utcnow().isoformat(),
        }
        return True

    async def update_preview_state(
        self,
        project_id: str,
        preview_state: dict[str, Any],
    ) -> bool:
        """Update shared preview state.

        Args:
            project_id: The project
            preview_state: New preview state

        Returns:
            True if updated
        """
        session = self._sessions.get(project_id)
        if not session:
            return False

        session.preview_state = {
            **preview_state,
            "updated_at": datetime.utcnow().isoformat(),
        }
        return True

    def get_session(self, project_id: str) -> StudioSession | None:
        """Get a studio session by project ID."""
        return self._sessions.get(project_id)

    def get_active_sessions(self) -> list[StudioSession]:
        """Get all active sessions."""
        return [s for s in self._sessions.values() if s.get_user_count() > 0]

    def get_user_session(self, user_id: str) -> StudioSession | None:
        """Get the session a user is currently in."""
        project_id = self._user_sessions.get(user_id)
        if project_id:
            return self._sessions.get(project_id)
        return None

    async def cleanup_inactive_users(self) -> int:
        """Mark inactive users as inactive and release their locks.

        Should be called periodically (e.g., every minute).

        Returns:
            Number of users marked inactive
        """
        async with self._lock:
            inactive_count = 0
            cutoff = datetime.utcnow() - self.INACTIVITY_TIMEOUT

            for session in self._sessions.values():
                for user in session.users.values():
                    if user.is_active and user.last_activity < cutoff:
                        user.is_active = False
                        inactive_count += 1

                        # Release their locks
                        locks_to_remove = [
                            lock_key
                            for lock_key, lock in session.edit_locks.items()
                            if lock.user_id == user.user_id
                        ]
                        for lock_key in locks_to_remove:
                            del session.edit_locks[lock_key]

            return inactive_count


def get_live_studio_service() -> LiveStudioService:
    """Get the global live studio service instance."""
    return LiveStudioService.get_instance()
