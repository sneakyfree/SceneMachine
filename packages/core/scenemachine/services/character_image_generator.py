"""Character reference image generation service.

Uses Flux Schnell or other image generation models to create
consistent character reference images from descriptions.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ImageProvider(StrEnum):
    """Available image generation providers."""

    FLUX_LOCAL = "flux_local"
    FLUX_FAL = "flux_fal"
    FLUX_REPLICATE = "flux_replicate"
    SDXL = "sdxl"
    MOCK = "mock"


class ImageStyle(StrEnum):
    """Image generation styles."""

    PHOTOREALISTIC = "photorealistic"
    CINEMATIC = "cinematic"
    ANIME = "anime"
    ILLUSTRATED = "illustrated"
    PORTRAIT = "portrait"


@dataclass
class GeneratedImage:
    """Result of image generation."""

    image_id: str
    success: bool
    image_path: str | None = None
    image_url: str | None = None
    image_data: bytes | None = None
    width: int = 1024
    height: int = 1024
    prompt_used: str = ""
    negative_prompt: str = ""
    seed: int | None = None
    generation_time_seconds: float = 0.0
    provider: ImageProvider = ImageProvider.MOCK
    cost_credits: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_id": self.image_id,
            "success": self.success,
            "image_path": self.image_path,
            "image_url": self.image_url,
            "width": self.width,
            "height": self.height,
            "prompt_used": self.prompt_used,
            "negative_prompt": self.negative_prompt,
            "seed": self.seed,
            "generation_time_seconds": self.generation_time_seconds,
            "provider": self.provider.value,
            "cost_credits": self.cost_credits,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class CharacterImageRequest:
    """Request to generate a character reference image."""

    character_name: str
    description: str
    physical_description: dict[str, Any] | None = None
    gender: str | None = None
    age_range: tuple | None = None
    style: ImageStyle = ImageStyle.CINEMATIC
    num_images: int = 4
    width: int = 1024
    height: int = 1024
    seed: int | None = None


class CameraAngle(StrEnum):
    """Camera angles for multi-angle character generation."""

    FRONT = "front"
    THREE_QUARTER_LEFT = "three_quarter_left"
    THREE_QUARTER_RIGHT = "three_quarter_right"
    PROFILE_LEFT = "profile_left"
    PROFILE_RIGHT = "profile_right"
    SLIGHTLY_ABOVE = "slightly_above"
    SLIGHTLY_BELOW = "slightly_below"


# Prompt modifiers for each camera angle
ANGLE_PROMPTS = {
    CameraAngle.FRONT: "facing camera, front view, looking straight ahead",
    CameraAngle.THREE_QUARTER_LEFT: "three-quarter view from left, slightly turned",
    CameraAngle.THREE_QUARTER_RIGHT: "three-quarter view from right, slightly turned",
    CameraAngle.PROFILE_LEFT: "profile view from left side, side profile",
    CameraAngle.PROFILE_RIGHT: "profile view from right side, side profile",
    CameraAngle.SLIGHTLY_ABOVE: "slightly elevated camera angle, looking up at camera",
    CameraAngle.SLIGHTLY_BELOW: "low angle shot, camera slightly below eye level",
}


class CharacterImageGenerator:
    """Service for generating character reference images.

    Implements the DNA strand master plan's requirements:
    - Generate multiple candidate images
    - Consistent prompting for character appearance
    - Support for face-consistent re-generation
    - Preview before commit to avoid credit waste
    """

    # Default quality prompts
    QUALITY_POSITIVE = [
        "masterpiece",
        "best quality",
        "highly detailed",
        "sharp focus",
        "professional lighting",
        "8k uhd",
    ]

    QUALITY_NEGATIVE = [
        "worst quality",
        "low quality",
        "blurry",
        "jpeg artifacts",
        "watermark",
        "text",
        "logo",
        "deformed",
        "distorted",
        "disfigured",
        "bad anatomy",
        "wrong proportions",
        "extra limbs",
        "missing limbs",
        "mutated hands",
        "poorly drawn face",
        "mutation",
        "ugly",
    ]

    # Style presets
    STYLE_PROMPTS = {
        ImageStyle.PHOTOREALISTIC: "photorealistic, realistic, lifelike, natural lighting",
        ImageStyle.CINEMATIC: "cinematic, film still, movie scene, dramatic lighting, depth of field",
        ImageStyle.ANIME: "anime style, detailed anime, vibrant colors",
        ImageStyle.ILLUSTRATED: "digital illustration, concept art, artstation",
        ImageStyle.PORTRAIT: "portrait photography, studio lighting, headshot, professional photo",
    }

    def __init__(
        self,
        default_provider: ImageProvider = ImageProvider.FLUX_FAL,
        output_dir: Path | None = None,
    ) -> None:
        """Initialize the character image generator.

        Args:
            default_provider: Default image generation provider
            output_dir: Directory to save generated images
        """
        self.default_provider = default_provider
        self.output_dir = output_dir or Path("/tmp/scenemachine/character_images")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # API clients (lazy initialized)
        self._fal_client = None
        self._replicate_client = None

    async def generate_character_images(
        self,
        request: CharacterImageRequest,
        provider: ImageProvider | None = None,
    ) -> list[GeneratedImage]:
        """Generate character reference images.

        Args:
            request: Character image generation request
            provider: Override default provider

        Returns:
            List of GeneratedImage results
        """
        provider = provider or self.default_provider

        # Build prompt from character description
        prompt = self._build_character_prompt(request)
        negative_prompt = ", ".join(self.QUALITY_NEGATIVE)

        logger.info(f"Generating {request.num_images} images for {request.character_name}")

        results = []
        for i in range(request.num_images):
            # Use different seeds for variety
            seed = request.seed + i if request.seed else None

            if provider == ImageProvider.FLUX_FAL:
                result = await self._generate_flux_fal(
                    prompt, negative_prompt, request.width, request.height, seed
                )
            elif provider == ImageProvider.FLUX_REPLICATE:
                result = await self._generate_flux_replicate(
                    prompt, negative_prompt, request.width, request.height, seed
                )
            elif provider == ImageProvider.MOCK:
                result = await self._generate_mock(
                    prompt, negative_prompt, request.width, request.height, seed
                )
            else:
                result = await self._generate_mock(
                    prompt, negative_prompt, request.width, request.height, seed
                )

            result.metadata["character_name"] = request.character_name
            result.metadata["variant_index"] = i
            result.prompt_used = prompt
            result.negative_prompt = negative_prompt

            results.append(result)

        return results

    def _build_character_prompt(self, request: CharacterImageRequest) -> str:
        """Build a detailed prompt from character request."""
        parts = []

        # Style prefix
        style_prompt = self.STYLE_PROMPTS.get(request.style, "")
        if style_prompt:
            parts.append(style_prompt)

        # Gender
        if request.gender:
            parts.append(f"{request.gender}")

        # Age description
        if request.age_range:
            avg_age = (request.age_range[0] + request.age_range[1]) / 2
            if avg_age < 13:
                parts.append("child")
            elif avg_age < 20:
                parts.append("teenager")
            elif avg_age < 35:
                parts.append("young adult")
            elif avg_age < 55:
                parts.append("middle-aged adult")
            else:
                parts.append("older adult")

        # Physical description
        if request.physical_description:
            phys = request.physical_description

            if phys.get("hair_color"):
                hair_desc = phys.get("hair_color")
                if phys.get("hair_style"):
                    hair_desc = f"{phys['hair_style']} {hair_desc}"
                parts.append(f"{hair_desc} hair")

            if phys.get("eye_color"):
                parts.append(f"{phys['eye_color']} eyes")

            if phys.get("skin_tone"):
                parts.append(f"{phys['skin_tone']} skin")

            if phys.get("build"):
                parts.append(f"{phys['build']} build")

            if phys.get("distinguishing_features"):
                parts.extend(phys["distinguishing_features"][:3])

        # Main description
        if request.description:
            # Clean and truncate description
            desc = request.description.strip()
            if len(desc) > 200:
                desc = desc[:197] + "..."
            parts.append(desc)

        # Quality modifiers
        parts.extend(self.QUALITY_POSITIVE)

        return ", ".join(filter(None, parts))

    async def _generate_flux_fal(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        seed: int | None,
    ) -> GeneratedImage:
        """Generate image using Flux via fal.ai."""
        image_id = str(uuid4())
        start_time = datetime.utcnow()

        try:
            import fal_client

            result = await fal_client.run_async(
                "fal-ai/flux/schnell",
                arguments={
                    "prompt": prompt,
                    "image_size": {"width": width, "height": height},
                    "num_inference_steps": 4,  # Schnell is fast
                    "seed": seed,
                },
            )

            elapsed = (datetime.utcnow() - start_time).total_seconds()

            # Get image URL from result
            image_url = result.get("images", [{}])[0].get("url")

            if image_url:
                # Download and save locally
                import httpx

                async with httpx.AsyncClient() as client:
                    response = await client.get(image_url)
                    image_data = response.content

                output_path = self.output_dir / f"{image_id}.png"
                output_path.write_bytes(image_data)

                return GeneratedImage(
                    image_id=image_id,
                    success=True,
                    image_path=str(output_path),
                    image_url=image_url,
                    width=width,
                    height=height,
                    seed=result.get("seed"),
                    generation_time_seconds=elapsed,
                    provider=ImageProvider.FLUX_FAL,
                    cost_credits=0.003,  # Approximate cost
                )

            return GeneratedImage(
                image_id=image_id,
                success=False,
                error="No image URL in response",
                provider=ImageProvider.FLUX_FAL,
            )

        except ImportError:
            logger.warning("fal_client not installed, using mock generator")
            return await self._generate_mock(prompt, negative_prompt, width, height, seed)
        except Exception as e:
            logger.exception(f"Flux FAL generation error: {e}")
            return GeneratedImage(
                image_id=image_id,
                success=False,
                error=str(e),
                provider=ImageProvider.FLUX_FAL,
            )

    async def _generate_flux_replicate(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        seed: int | None,
    ) -> GeneratedImage:
        """Generate image using Flux via Replicate."""
        image_id = str(uuid4())
        start_time = datetime.utcnow()

        try:
            import replicate

            output = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: replicate.run(
                    "black-forest-labs/flux-schnell",
                    input={
                        "prompt": prompt,
                        "width": width,
                        "height": height,
                        "num_outputs": 1,
                        "seed": seed,
                    },
                ),
            )

            elapsed = (datetime.utcnow() - start_time).total_seconds()

            if output and len(output) > 0:
                image_url = output[0]

                # Download and save
                import httpx

                async with httpx.AsyncClient() as client:
                    response = await client.get(image_url)
                    image_data = response.content

                output_path = self.output_dir / f"{image_id}.png"
                output_path.write_bytes(image_data)

                return GeneratedImage(
                    image_id=image_id,
                    success=True,
                    image_path=str(output_path),
                    image_url=image_url,
                    width=width,
                    height=height,
                    seed=seed,
                    generation_time_seconds=elapsed,
                    provider=ImageProvider.FLUX_REPLICATE,
                    cost_credits=0.003,
                )

            return GeneratedImage(
                image_id=image_id,
                success=False,
                error="No output from Replicate",
                provider=ImageProvider.FLUX_REPLICATE,
            )

        except ImportError:
            logger.warning("replicate not installed, using mock generator")
            return await self._generate_mock(prompt, negative_prompt, width, height, seed)
        except Exception as e:
            logger.exception(f"Replicate generation error: {e}")
            return GeneratedImage(
                image_id=image_id,
                success=False,
                error=str(e),
                provider=ImageProvider.FLUX_REPLICATE,
            )

    async def _generate_mock(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        seed: int | None,
    ) -> GeneratedImage:
        """Generate a mock placeholder image for testing."""
        image_id = str(uuid4())

        # Create a simple colored placeholder
        try:
            from PIL import (  # noqa: F401 — ImageFont reserved for label rendering when text overlay support is wired
                Image,
                ImageDraw,
                ImageFont,
            )

            # Create gradient background
            img = Image.new("RGB", (width, height), color="#2a2a3e")
            draw = ImageDraw.Draw(img)

            # Add text
            text = f"Character Reference\n{prompt[:50]}..."
            draw.text((width // 4, height // 2), text, fill="#ffffff")

            output_path = self.output_dir / f"{image_id}.png"
            img.save(output_path)

            return GeneratedImage(
                image_id=image_id,
                success=True,
                image_path=str(output_path),
                width=width,
                height=height,
                prompt_used=prompt,
                negative_prompt=negative_prompt,
                seed=seed or 12345,
                generation_time_seconds=0.1,
                provider=ImageProvider.MOCK,
                cost_credits=0.0,
                metadata={"mock": True},
            )

        except ImportError:
            # No PIL, create empty file
            output_path = self.output_dir / f"{image_id}.png"
            output_path.write_bytes(b"")

            return GeneratedImage(
                image_id=image_id,
                success=True,
                image_path=str(output_path),
                width=width,
                height=height,
                provider=ImageProvider.MOCK,
                metadata={"mock": True, "empty": True},
            )

    async def generate_multi_angle_references(
        self,
        request: CharacterImageRequest,
        angles: list[CameraAngle] | None = None,
        provider: ImageProvider | None = None,
    ) -> dict[CameraAngle, GeneratedImage]:
        """Generate character reference images from multiple camera angles.

        This enables better character consistency by providing reference
        images from different viewpoints for IP-Adapter face injection.

        Args:
            request: Character image generation request
            angles: List of camera angles to generate (default: front, 3/4, profile)
            provider: Override default provider

        Returns:
            Dictionary mapping angles to generated images
        """
        if angles is None:
            angles = [
                CameraAngle.FRONT,
                CameraAngle.THREE_QUARTER_LEFT,
                CameraAngle.PROFILE_LEFT,
            ]

        provider = provider or self.default_provider
        results = {}

        # Use same seed for consistency across angles
        base_seed = request.seed or 42

        for i, angle in enumerate(angles):
            # Build angle-specific prompt
            base_prompt = self._build_character_prompt(request)
            angle_modifier = ANGLE_PROMPTS.get(angle, "")
            prompt = f"{angle_modifier}, {base_prompt}"

            negative_prompt = ", ".join(self.QUALITY_NEGATIVE)

            logger.info(f"Generating {angle.value} angle for {request.character_name}")

            if provider == ImageProvider.FLUX_FAL:
                result = await self._generate_flux_fal(
                    prompt, negative_prompt, request.width, request.height, base_seed + i
                )
            elif provider == ImageProvider.FLUX_REPLICATE:
                result = await self._generate_flux_replicate(
                    prompt, negative_prompt, request.width, request.height, base_seed + i
                )
            else:
                result = await self._generate_mock(
                    prompt, negative_prompt, request.width, request.height, base_seed + i
                )

            result.metadata["character_name"] = request.character_name
            result.metadata["camera_angle"] = angle.value
            result.prompt_used = prompt

            results[angle] = result

        return results

    async def apply_style_transfer(
        self,
        content_image_path: str | Path,
        style_reference_path: str | Path,
        strength: float = 0.5,
        preserve_face: bool = True,
    ) -> GeneratedImage:
        """Apply style from reference image while preserving character identity.

        Uses IP-Adapter style for artistic consistency across scenes.

        Args:
            content_image_path: Path to the character image to stylize
            style_reference_path: Path to the style reference image
            strength: Style transfer strength (0-1)
            preserve_face: Whether to preserve facial features

        Returns:
            Stylized GeneratedImage
        """
        image_id = str(uuid4())

        logger.info(f"Applying style transfer with strength {strength}")

        # For now, return a mock - actual implementation would use
        # IP-Adapter Style or ControlNet Reference-Only
        try:
            from PIL import Image

            content_path = Path(content_image_path)
            if not content_path.exists():
                return GeneratedImage(
                    image_id=image_id,
                    success=False,
                    error=f"Content image not found: {content_path}",
                )

            # Load and process images
            img = Image.open(content_path)

            # Apply simple color adjustment as placeholder
            # Real implementation would use diffusion-based style transfer
            output_path = self.output_dir / f"{image_id}_styled.png"
            img.save(output_path)

            return GeneratedImage(
                image_id=image_id,
                success=True,
                image_path=str(output_path),
                width=img.width,
                height=img.height,
                metadata={
                    "style_transfer": True,
                    "strength": strength,
                    "preserve_face": preserve_face,
                },
            )

        except Exception as e:
            logger.error(f"Style transfer failed: {e}")
            return GeneratedImage(
                image_id=image_id,
                success=False,
                error=str(e),
            )

    def enhance_prompt(
        self,
        base_prompt: str,
        enhance_for: str = "consistency",
    ) -> str:
        """Enhance prompt for better generation quality.

        Args:
            base_prompt: Original prompt
            enhance_for: Enhancement type ('consistency', 'detail', 'cinematic')

        Returns:
            Enhanced prompt string
        """
        enhancements = {
            "consistency": [
                "highly consistent character appearance",
                "stable identity markers",
                "recognizable facial features",
            ],
            "detail": [
                "intricate details",
                "fine textures",
                "micro-expressions captured",
                "pore-level detail",
            ],
            "cinematic": [
                "cinematic color grading",
                "film grain",
                "anamorphic bokeh",
                "hollywood lighting setup",
            ],
        }

        additions = enhancements.get(enhance_for, [])
        enhanced = f"{base_prompt}, {', '.join(additions)}"

        return enhanced

    async def regenerate_with_face(
        self,
        prompt: str,
        reference_image_path: str | Path,
        strength: float = 0.65,
        width: int = 1024,
        height: int = 1024,
    ) -> GeneratedImage:
        """Regenerate image while preserving face from reference.

        Uses IP-Adapter or similar face-preservation technique.

        Args:
            prompt: New scene/style prompt
            reference_image_path: Path to reference face image
            strength: How much to preserve the original face (0-1)
            width: Output width
            height: Output height

        Returns:
            GeneratedImage with preserved face
        """
        # This would integrate with IP-Adapter Face ID or similar
        # For now, return mock
        logger.info(f"Regenerating with face from {reference_image_path}")

        return await self._generate_mock(prompt, "", width, height, None)

    def estimate_cost(
        self,
        num_images: int,
        provider: ImageProvider | None = None,
    ) -> dict[str, Any]:
        """Estimate generation cost.

        Args:
            num_images: Number of images to generate
            provider: Provider to use

        Returns:
            Cost estimate with breakdown
        """
        provider = provider or self.default_provider

        # Approximate costs per image
        costs = {
            ImageProvider.FLUX_FAL: 0.003,
            ImageProvider.FLUX_REPLICATE: 0.003,
            ImageProvider.FLUX_LOCAL: 0.0,  # Only compute costs
            ImageProvider.SDXL: 0.002,
            ImageProvider.MOCK: 0.0,
        }

        per_image = costs.get(provider, 0.003)
        total = per_image * num_images

        return {
            "provider": provider.value,
            "num_images": num_images,
            "cost_per_image": per_image,
            "total_cost": total,
            "currency": "USD",
        }


# Singleton instance
_image_generator: CharacterImageGenerator | None = None


def get_character_image_generator() -> CharacterImageGenerator:
    """Get or create the character image generator singleton."""
    global _image_generator
    if _image_generator is None:
        _image_generator = CharacterImageGenerator()
    return _image_generator
