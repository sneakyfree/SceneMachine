"""Events service routes."""

from .corecast import router as corecast_router
from .badges import router as badges_router
from .performers_association import router as performers_association_router

__all__ = [
    "corecast_router",
    "badges_router",
    "performers_association_router",
]
