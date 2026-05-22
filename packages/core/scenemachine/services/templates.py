"""Project templates service for pre-configured project settings."""

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TemplateCategory(StrEnum):
    """Template categories."""

    FILM = "film"
    SHORT = "short"
    COMMERCIAL = "commercial"
    MUSIC_VIDEO = "music_video"
    DOCUMENTARY = "documentary"
    EXPERIMENTAL = "experimental"


@dataclass
class ProjectTemplate:
    """A project template with pre-configured settings."""

    id: str
    name: str
    description: str
    category: TemplateCategory
    thumbnail: str | None = None  # Path or URL to thumbnail

    # Default project settings
    default_resolution: str = "1920x1080"
    default_fps: int = 24
    default_shot_duration: float = 3.0

    # Visual style presets
    visual_style: str = "cinematic"
    color_palette: list[str] = field(default_factory=list)
    lighting_style: str = "natural"

    # Generation settings
    default_provider: str = "local"
    recommended_model: str | None = None

    # Shot planning defaults
    default_shot_types: list[str] = field(default_factory=list)
    pacing: str = "moderate"  # slow, moderate, fast
    avg_shots_per_scene: int = 8

    # Metadata
    tags: list[str] = field(default_factory=list)
    example_projects: list[str] = field(default_factory=list)


# Built-in templates
BUILTIN_TEMPLATES: list[ProjectTemplate] = [
    ProjectTemplate(
        id="cinematic-drama",
        name="Cinematic Drama",
        description="Classic Hollywood style with dramatic lighting and emotional depth. Perfect for character-driven stories.",
        category=TemplateCategory.FILM,
        default_resolution="1920x1080",
        default_fps=24,
        default_shot_duration=4.0,
        visual_style="cinematic",
        color_palette=["#1a1a2e", "#16213e", "#0f3460", "#e94560"],
        lighting_style="dramatic",
        default_shot_types=["wide", "medium", "close_up", "over_the_shoulder"],
        pacing="moderate",
        avg_shots_per_scene=10,
        tags=["drama", "emotional", "character-driven", "cinematic"],
    ),
    ProjectTemplate(
        id="action-thriller",
        name="Action Thriller",
        description="Fast-paced action with dynamic camera work and high energy. Great for chase scenes and confrontations.",
        category=TemplateCategory.FILM,
        default_resolution="1920x1080",
        default_fps=24,
        default_shot_duration=2.0,
        visual_style="action",
        color_palette=["#0d0d0d", "#1a1a1a", "#ff4500", "#ffd700"],
        lighting_style="high_contrast",
        default_shot_types=["wide", "medium", "close_up", "pov", "tracking"],
        pacing="fast",
        avg_shots_per_scene=15,
        tags=["action", "thriller", "fast-paced", "dynamic"],
    ),
    ProjectTemplate(
        id="romantic-comedy",
        name="Romantic Comedy",
        description="Light, warm aesthetic with bright colors and natural lighting. Ideal for rom-coms and feel-good stories.",
        category=TemplateCategory.FILM,
        default_resolution="1920x1080",
        default_fps=24,
        default_shot_duration=3.5,
        visual_style="romantic",
        color_palette=["#fef5ed", "#f8e1d4", "#e8b4b8", "#967aa1"],
        lighting_style="soft",
        default_shot_types=["two_shot", "medium", "close_up", "over_the_shoulder"],
        pacing="moderate",
        avg_shots_per_scene=8,
        tags=["romantic", "comedy", "light", "warm"],
    ),
    ProjectTemplate(
        id="sci-fi-futuristic",
        name="Sci-Fi / Futuristic",
        description="Sleek, high-tech aesthetic with cool tones and dramatic lighting. Perfect for science fiction narratives.",
        category=TemplateCategory.FILM,
        default_resolution="1920x1080",
        default_fps=24,
        default_shot_duration=3.0,
        visual_style="sci-fi",
        color_palette=["#0a0a1a", "#1a1a3a", "#00d4ff", "#7b2cbf"],
        lighting_style="neon",
        default_shot_types=["establishing", "wide", "medium", "close_up", "insert"],
        pacing="moderate",
        avg_shots_per_scene=12,
        tags=["sci-fi", "futuristic", "tech", "cyberpunk"],
    ),
    ProjectTemplate(
        id="horror-suspense",
        name="Horror / Suspense",
        description="Dark, atmospheric with tension-building shots and unsettling compositions. Built for scares.",
        category=TemplateCategory.FILM,
        default_resolution="1920x1080",
        default_fps=24,
        default_shot_duration=4.5,
        visual_style="horror",
        color_palette=["#0d0d0d", "#1a0a0a", "#3d0c0c", "#8b0000"],
        lighting_style="low_key",
        default_shot_types=["wide", "medium_close_up", "extreme_close_up", "pov"],
        pacing="slow",
        avg_shots_per_scene=7,
        tags=["horror", "suspense", "dark", "atmospheric"],
    ),
    ProjectTemplate(
        id="indie-film",
        name="Indie / Art House",
        description="Naturalistic, understated visuals with contemplative pacing. Great for artistic narratives.",
        category=TemplateCategory.FILM,
        default_resolution="1920x1080",
        default_fps=24,
        default_shot_duration=5.0,
        visual_style="indie",
        color_palette=["#2c2c2c", "#4a4a4a", "#8a8a8a", "#d4d4d4"],
        lighting_style="natural",
        default_shot_types=["wide", "medium_wide", "medium", "close_up"],
        pacing="slow",
        avg_shots_per_scene=6,
        tags=["indie", "artistic", "contemplative", "naturalistic"],
    ),
    ProjectTemplate(
        id="documentary-style",
        name="Documentary",
        description="Authentic, observational style with handheld aesthetics. Perfect for true stories.",
        category=TemplateCategory.DOCUMENTARY,
        default_resolution="1920x1080",
        default_fps=24,
        default_shot_duration=4.0,
        visual_style="documentary",
        color_palette=["#1a1a1a", "#3a3a3a", "#6a6a6a", "#ffffff"],
        lighting_style="available_light",
        default_shot_types=["interview", "b_roll", "establishing", "medium"],
        pacing="moderate",
        avg_shots_per_scene=10,
        tags=["documentary", "authentic", "observational", "real"],
    ),
    ProjectTemplate(
        id="music-video-standard",
        name="Music Video",
        description="Dynamic, visually striking with fast cuts and creative compositions. Built for performance pieces.",
        category=TemplateCategory.MUSIC_VIDEO,
        default_resolution="1920x1080",
        default_fps=24,
        default_shot_duration=1.5,
        visual_style="music_video",
        color_palette=["#000000", "#ff00ff", "#00ffff", "#ffff00"],
        lighting_style="creative",
        default_shot_types=["performance", "close_up", "wide", "tracking", "insert"],
        pacing="fast",
        avg_shots_per_scene=20,
        tags=["music", "performance", "dynamic", "creative"],
    ),
    ProjectTemplate(
        id="commercial-product",
        name="Commercial / Product",
        description="Clean, polished aesthetic for product showcases and advertisements. Professional quality.",
        category=TemplateCategory.COMMERCIAL,
        default_resolution="1920x1080",
        default_fps=30,
        default_shot_duration=2.5,
        visual_style="commercial",
        color_palette=["#ffffff", "#f0f0f0", "#0066cc", "#ff6600"],
        lighting_style="studio",
        default_shot_types=["product_shot", "lifestyle", "close_up", "wide"],
        pacing="moderate",
        avg_shots_per_scene=8,
        tags=["commercial", "product", "advertising", "clean"],
    ),
    ProjectTemplate(
        id="short-film",
        name="Short Film",
        description="Versatile template for short-form storytelling with balanced pacing and composition.",
        category=TemplateCategory.SHORT,
        default_resolution="1920x1080",
        default_fps=24,
        default_shot_duration=3.0,
        visual_style="cinematic",
        color_palette=["#1a1a1a", "#2a2a3a", "#4a4a5a", "#ffffff"],
        lighting_style="natural",
        default_shot_types=["establishing", "wide", "medium", "close_up", "two_shot"],
        pacing="moderate",
        avg_shots_per_scene=8,
        tags=["short", "versatile", "storytelling", "balanced"],
    ),
    ProjectTemplate(
        id="anime-style",
        name="Anime / Animation",
        description="Stylized aesthetic inspired by Japanese animation with bold colors and dynamic compositions.",
        category=TemplateCategory.FILM,
        default_resolution="1920x1080",
        default_fps=24,
        default_shot_duration=2.5,
        visual_style="anime",
        color_palette=["#1a1a2e", "#ff6b6b", "#4ecdc4", "#ffe66d"],
        lighting_style="stylized",
        default_shot_types=["establishing", "medium", "close_up", "extreme_close_up", "action"],
        pacing="fast",
        avg_shots_per_scene=12,
        tags=["anime", "animation", "stylized", "bold"],
    ),
    ProjectTemplate(
        id="noir-detective",
        name="Film Noir",
        description="Classic noir aesthetic with high contrast, shadows, and moody atmosphere. Perfect for detective stories.",
        category=TemplateCategory.FILM,
        default_resolution="1920x1080",
        default_fps=24,
        default_shot_duration=4.0,
        visual_style="noir",
        color_palette=["#000000", "#1a1a1a", "#4a4a4a", "#d4d4d4"],
        lighting_style="chiaroscuro",
        default_shot_types=["wide", "medium", "close_up", "silhouette", "dutch_angle"],
        pacing="slow",
        avg_shots_per_scene=8,
        tags=["noir", "detective", "shadows", "classic"],
    ),
]


class TemplatesService:
    """Service for managing project templates."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session
        self._templates = {t.id: t for t in BUILTIN_TEMPLATES}

    async def get_all_templates(
        self,
        category: TemplateCategory | None = None,
    ) -> list[ProjectTemplate]:
        """Get all available templates.

        Args:
            category: Optional category filter
        """
        templates = list(self._templates.values())

        if category:
            templates = [t for t in templates if t.category == category]

        return templates

    async def get_template(self, template_id: str) -> ProjectTemplate | None:
        """Get a template by ID.

        Args:
            template_id: Template identifier
        """
        return self._templates.get(template_id)

    async def get_template_categories(self) -> list[dict[str, Any]]:
        """Get available template categories with counts."""
        categories = {}
        for template in self._templates.values():
            cat = template.category.value
            if cat not in categories:
                categories[cat] = {
                    "id": cat,
                    "name": template.category.name.replace("_", " ").title(),
                    "count": 0,
                }
            categories[cat]["count"] += 1

        return list(categories.values())

    async def search_templates(
        self,
        query: str,
        limit: int = 10,
    ) -> list[ProjectTemplate]:
        """Search templates by name, description, or tags.

        Args:
            query: Search query
            limit: Max results to return
        """
        query_lower = query.lower()
        results = []

        for template in self._templates.values():
            score = 0

            # Check name
            if query_lower in template.name.lower():
                score += 10

            # Check description
            if query_lower in template.description.lower():
                score += 5

            # Check tags
            for tag in template.tags:
                if query_lower in tag.lower():
                    score += 3

            if score > 0:
                results.append((score, template))

        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)

        return [t for _, t in results[:limit]]

    def get_template_project_settings(
        self,
        template: ProjectTemplate,
    ) -> dict[str, Any]:
        """Convert template to project settings dict.

        Args:
            template: Template to convert
        """
        return {
            "template_id": template.id,
            "visual_style": template.visual_style,
            "color_palette": template.color_palette,
            "lighting_style": template.lighting_style,
            "default_resolution": template.default_resolution,
            "default_fps": template.default_fps,
            "default_shot_duration": template.default_shot_duration,
            "default_provider": template.default_provider,
            "default_shot_types": template.default_shot_types,
            "pacing": template.pacing,
            "avg_shots_per_scene": template.avg_shots_per_scene,
        }

    async def get_featured_templates(self, limit: int = 6) -> list[ProjectTemplate]:
        """Get featured/recommended templates.

        Args:
            limit: Max templates to return
        """
        # Return a mix of different categories
        featured_ids = [
            "cinematic-drama",
            "action-thriller",
            "short-film",
            "music-video-standard",
            "documentary-style",
            "sci-fi-futuristic",
        ]

        return [self._templates[tid] for tid in featured_ids[:limit] if tid in self._templates]
