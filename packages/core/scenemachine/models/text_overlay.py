"""Text overlay model for titles, lower thirds, and captions.

Supports styling, positioning, and animation of text on video.
"""

from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin, JSONType


class TextOverlayType(str, Enum):
    """Types of text overlays."""

    TITLE = "title"
    SUBTITLE = "subtitle"
    LOWER_THIRD = "lower_third"
    CAPTION = "caption"
    CUSTOM = "custom"


class TextPosition(str, Enum):
    """Preset positions for text overlays."""

    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    CENTER_LEFT = "center_left"
    CENTER = "center"
    CENTER_RIGHT = "center_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"
    CUSTOM = "custom"


class TextAnimation(str, Enum):
    """Animation types for text overlays."""

    NONE = "none"
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    FADE_IN_OUT = "fade_in_out"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    TYPEWRITER = "typewriter"
    SCALE_IN = "scale_in"
    BLUR_IN = "blur_in"


class TextOverlay(Base, UUIDMixin, TimestampMixin):
    """A text overlay on a shot or scene.

    Supports styling, positioning, and animation.
    """

    __tablename__ = "text_overlays"

    # Parent relationships (one of these should be set)
    shot_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("shots.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    scene_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    project_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Overlay type
    overlay_type: Mapped[TextOverlayType] = mapped_column(
        SAEnum(TextOverlayType, name="text_overlay_type"),
        default=TextOverlayType.CUSTOM,
        nullable=False,
    )

    # Content
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Position
    position: Mapped[TextPosition] = mapped_column(
        SAEnum(TextPosition, name="text_position"),
        default=TextPosition.CENTER,
        nullable=False,
    )
    custom_x: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100 percentage
    custom_y: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100 percentage

    # Style (stored as JSON for flexibility)
    style: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True, default=dict)
    # Expected style fields:
    # - fontFamily: str
    # - fontSize: int
    # - fontWeight: 'normal' | 'bold'
    # - fontStyle: 'normal' | 'italic'
    # - textDecoration: 'none' | 'underline'
    # - color: str (hex)
    # - backgroundColor: str (hex)
    # - backgroundOpacity: float (0-1)
    # - textAlign: 'left' | 'center' | 'right'
    # - letterSpacing: int
    # - lineHeight: float
    # - textShadow: bool
    # - textShadowColor: str (hex)
    # - textShadowBlur: int

    # Animation settings
    animation_in: Mapped[TextAnimation] = mapped_column(
        SAEnum(TextAnimation, name="text_animation"),
        default=TextAnimation.FADE_IN,
        nullable=False,
    )
    animation_out: Mapped[TextAnimation] = mapped_column(
        SAEnum(TextAnimation, name="text_animation"),
        default=TextAnimation.FADE_OUT,
        nullable=False,
    )
    animation_in_duration_ms: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    animation_out_duration_ms: Mapped[int] = mapped_column(Integer, default=500, nullable=False)

    # Timing
    start_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=5000, nullable=False)

    # Display settings
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    z_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    @property
    def start_time_seconds(self) -> float:
        """Start time in seconds."""
        return self.start_time_ms / 1000.0

    @property
    def duration_seconds(self) -> float:
        """Duration in seconds."""
        return self.duration_ms / 1000.0

    @property
    def end_time_ms(self) -> int:
        """End time in milliseconds."""
        return self.start_time_ms + self.duration_ms

    @property
    def end_time_seconds(self) -> float:
        """End time in seconds."""
        return self.end_time_ms / 1000.0

    @property
    def font_family(self) -> str:
        """Get font family from style."""
        return (self.style or {}).get("fontFamily", "Arial")

    @property
    def font_size(self) -> int:
        """Get font size from style."""
        return (self.style or {}).get("fontSize", 48)

    @property
    def font_color(self) -> str:
        """Get font color from style."""
        return (self.style or {}).get("color", "#FFFFFF")

    @property
    def background_color(self) -> str:
        """Get background color from style."""
        return (self.style or {}).get("backgroundColor", "#000000")

    @property
    def background_opacity(self) -> float:
        """Get background opacity from style."""
        return (self.style or {}).get("backgroundOpacity", 0.0)

    def get_position_coords(self, video_width: int, video_height: int) -> tuple[int, int]:
        """Calculate pixel coordinates for the overlay position.

        Args:
            video_width: Video width in pixels
            video_height: Video height in pixels

        Returns:
            Tuple of (x, y) pixel coordinates
        """
        padding_x = int(video_width * 0.05)
        padding_y = int(video_height * 0.05)

        position_map = {
            TextPosition.TOP_LEFT: (padding_x, padding_y),
            TextPosition.TOP_CENTER: (video_width // 2, padding_y),
            TextPosition.TOP_RIGHT: (video_width - padding_x, padding_y),
            TextPosition.CENTER_LEFT: (padding_x, video_height // 2),
            TextPosition.CENTER: (video_width // 2, video_height // 2),
            TextPosition.CENTER_RIGHT: (video_width - padding_x, video_height // 2),
            TextPosition.BOTTOM_LEFT: (padding_x, video_height - int(video_height * 0.1)),
            TextPosition.BOTTOM_CENTER: (video_width // 2, video_height - int(video_height * 0.1)),
            TextPosition.BOTTOM_RIGHT: (video_width - padding_x, video_height - int(video_height * 0.1)),
            TextPosition.CUSTOM: (
                int((self.custom_x or 50) / 100 * video_width),
                int((self.custom_y or 50) / 100 * video_height),
            ),
        }

        return position_map.get(self.position, (video_width // 2, video_height // 2))

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "type": self.overlay_type.value,
            "text": self.text,
            "position": self.position.value,
            "customX": self.custom_x,
            "customY": self.custom_y,
            "style": self.style or {},
            "animation": {
                "in": self.animation_in.value,
                "out": self.animation_out.value,
                "inDuration": self.animation_in_duration_ms,
                "outDuration": self.animation_out_duration_ms,
            },
            "timing": {
                "startTime": self.start_time_ms,
                "duration": self.duration_ms,
            },
            "isVisible": self.is_visible,
            "zIndex": self.z_index,
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"<TextOverlay(id={self.id}, type={self.overlay_type.value}, text='{self.text[:20]}...')>"


# Default style configurations for presets
DEFAULT_STYLES = {
    TextOverlayType.TITLE: {
        "fontFamily": "Arial",
        "fontSize": 72,
        "fontWeight": "bold",
        "fontStyle": "normal",
        "textDecoration": "none",
        "color": "#FFFFFF",
        "backgroundColor": "#000000",
        "backgroundOpacity": 0,
        "textAlign": "center",
        "letterSpacing": 0,
        "lineHeight": 1.2,
        "textShadow": True,
        "textShadowColor": "#000000",
        "textShadowBlur": 4,
    },
    TextOverlayType.SUBTITLE: {
        "fontFamily": "Arial",
        "fontSize": 36,
        "fontWeight": "normal",
        "fontStyle": "normal",
        "textDecoration": "none",
        "color": "#FFFFFF",
        "backgroundColor": "#000000",
        "backgroundOpacity": 0,
        "textAlign": "center",
        "letterSpacing": 0,
        "lineHeight": 1.2,
        "textShadow": True,
        "textShadowColor": "#000000",
        "textShadowBlur": 4,
    },
    TextOverlayType.LOWER_THIRD: {
        "fontFamily": "Arial",
        "fontSize": 24,
        "fontWeight": "bold",
        "fontStyle": "normal",
        "textDecoration": "none",
        "color": "#FFFFFF",
        "backgroundColor": "#000000",
        "backgroundOpacity": 0.7,
        "textAlign": "left",
        "letterSpacing": 0,
        "lineHeight": 1.2,
        "textShadow": False,
        "textShadowColor": "#000000",
        "textShadowBlur": 0,
    },
    TextOverlayType.CAPTION: {
        "fontFamily": "Arial",
        "fontSize": 20,
        "fontWeight": "normal",
        "fontStyle": "normal",
        "textDecoration": "none",
        "color": "#FFFFFF",
        "backgroundColor": "#000000",
        "backgroundOpacity": 0.5,
        "textAlign": "center",
        "letterSpacing": 0,
        "lineHeight": 1.2,
        "textShadow": False,
        "textShadowColor": "#000000",
        "textShadowBlur": 0,
    },
    TextOverlayType.CUSTOM: {
        "fontFamily": "Arial",
        "fontSize": 48,
        "fontWeight": "bold",
        "fontStyle": "normal",
        "textDecoration": "none",
        "color": "#FFFFFF",
        "backgroundColor": "#000000",
        "backgroundOpacity": 0,
        "textAlign": "center",
        "letterSpacing": 0,
        "lineHeight": 1.2,
        "textShadow": True,
        "textShadowColor": "#000000",
        "textShadowBlur": 4,
    },
}
