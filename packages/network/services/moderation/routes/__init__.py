"""Moderation service routes."""

from .reports import router as reports_router
from .actions import router as actions_router
from .strikes import router as strikes_router
from .appeals import router as appeals_router
from .flags import router as flags_router

__all__ = [
    "reports_router",
    "actions_router",
    "strikes_router",
    "appeals_router",
    "flags_router",
]
