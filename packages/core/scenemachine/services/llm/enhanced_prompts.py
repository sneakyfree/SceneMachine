"""Enhanced LLM Prompt Templates with Few-Shot Examples.

Provides optimized prompts for screenplay analysis and shot generation
with enhanced few-shot examples, confidence scoring, and prompt caching.
"""

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PromptCategory(StrEnum):
    """Categories of LLM prompts."""

    SHOT_GENERATION = "shot_generation"
    CHARACTER_ANALYSIS = "character_analysis"
    SCENE_BREAKDOWN = "scene_breakdown"
    VISUAL_DESCRIPTION = "visual_description"
    DIALOGUE_EMOTION = "dialogue_emotion"
    QUALITY_REVIEW = "quality_review"


@dataclass
class PromptTemplate:
    """A prompt template with metadata."""

    name: str
    category: PromptCategory
    system_prompt: str
    user_template: str
    few_shot_examples: list[dict[str, str]] = field(default_factory=list)
    expected_output_format: str = "json"
    max_tokens: int = 2000
    temperature: float = 0.7


@dataclass
class ConfidenceScore:
    """Confidence scoring for LLM outputs."""

    overall: float  # 0.0 - 1.0
    completeness: float
    consistency: float
    quality: float
    reasoning: str


# =============================================================================
# Few-Shot Examples
# =============================================================================

SHOT_GENERATION_EXAMPLES = [
    {
        "input": """SCENE: INT. COFFEE SHOP - DAY
JOHN enters, looking nervous. He spots SARAH at a corner table.
JOHN: Hey, thanks for meeting me.
SARAH: (coldly) What do you want, John?""",
        "output": """{
  "shots": [
    {
      "shot_number": 1,
      "type": "wide",
      "description": "Establishing shot of a cozy coffee shop interior. Morning light streams through large windows. JOHN enters through the front door, his body language tense and hesitant.",
      "camera_movement": "static",
      "duration_seconds": 4,
      "characters": ["John"],
      "dialogue": null
    },
    {
      "shot_number": 2,
      "type": "pov",
      "description": "John's POV scanning the room, landing on SARAH sitting alone at a corner table near the window, coffee cup in hand.",
      "camera_movement": "slow pan right",
      "duration_seconds": 3,
      "characters": ["Sarah"],
      "dialogue": null
    },
    {
      "shot_number": 3,
      "type": "medium",
      "description": "John approaches Sarah's table. He stands awkwardly, hands in pockets.",
      "camera_movement": "tracking dolly",
      "duration_seconds": 3,
      "characters": ["John", "Sarah"],
      "dialogue": {"speaker": "John", "text": "Hey, thanks for meeting me.", "emotion": "nervous"}
    },
    {
      "shot_number": 4,
      "type": "close-up",
      "description": "Tight on Sarah's face. Her expression is guarded, lips pressed thin. She doesn't smile.",
      "camera_movement": "static",
      "duration_seconds": 2,
      "characters": ["Sarah"],
      "dialogue": {"speaker": "Sarah", "text": "What do you want, John?", "emotion": "cold"}
    }
  ],
  "confidence": 0.92,
  "notes": "Scene establishes tension between characters through body language and cold dialogue."
}""",
    },
    {
        "input": """SCENE: EXT. ROOFTOP - NIGHT
ALEX stands at the edge, looking at the city lights. MAYA runs up behind them.
MAYA: Alex, wait! Don't do this!""",
        "output": """{
  "shots": [
    {
      "shot_number": 1,
      "type": "extreme_wide",
      "description": "Aerial view of a city skyline at night, lights twinkling. Camera slowly pushes toward one particular rooftop.",
      "camera_movement": "slow push in",
      "duration_seconds": 5,
      "characters": [],
      "dialogue": null
    },
    {
      "shot_number": 2,
      "type": "wide",
      "description": "ALEX silhouetted against the city lights, standing dangerously close to the rooftop edge. Wind whips their hair.",
      "camera_movement": "static",
      "duration_seconds": 4,
      "characters": ["Alex"],
      "dialogue": null
    },
    {
      "shot_number": 3,
      "type": "medium_wide",
      "description": "A rooftop door bursts open. MAYA rushes out, terror on her face. She spots Alex and freezes.",
      "camera_movement": "handheld",
      "duration_seconds": 3,
      "characters": ["Maya"],
      "dialogue": null
    },
    {
      "shot_number": 4,
      "type": "over_shoulder",
      "description": "Over Alex's shoulder, looking back at Maya who has tears streaming down her face.",
      "camera_movement": "slight push",
      "duration_seconds": 3,
      "characters": ["Alex", "Maya"],
      "dialogue": {"speaker": "Maya", "text": "Alex, wait! Don't do this!", "emotion": "desperate"}
    }
  ],
  "confidence": 0.88,
  "notes": "High-stakes emotional scene. Camera work emphasizes isolation and desperation."
}""",
    },
]

CHARACTER_ANALYSIS_EXAMPLES = [
    {
        "input": """Character: DETECTIVE MARIA SANTOS
Appearances in script:
- First appears at crime scene, barking orders
- Argues with captain about case
- Shows vulnerability in late-night bar scene
- Confronts killer in finale""",
        "output": """{
  "character_profile": {
    "name": "Detective Maria Santos",
    "role": "protagonist",
    "arc_type": "transformation",
    "traits": {
      "dominant": ["determined", "authoritative", "sharp-minded"],
      "hidden": ["vulnerable", "guilt-ridden", "lonely"],
      "evolving": ["learning to trust", "opening up emotionally"]
    },
    "visual_suggestions": {
      "age_range": [35, 45],
      "build": "athletic",
      "style": "practical, slightly disheveled professional wear",
      "distinguishing_features": ["tired eyes", "tension in shoulders"]
    },
    "voice_suggestions": {
      "tone": "authoritative but can soften",
      "pacing": "quick when stressed, slower in vulnerable moments",
      "accent": "subtle regional accent possible"
    }
  },
  "confidence": 0.91
}""",
    },
]

VISUAL_DESCRIPTION_EXAMPLES = [
    {
        "input": "Shot: Sarah enters the abandoned warehouse, flashlight cutting through dust particles",
        "output": """{
  "visual_prompt": "A woman in her 30s with auburn hair enters a vast abandoned industrial warehouse. Her flashlight beam cuts through thick dust particles floating in the air, creating ethereal shafts of light. Rusted machinery looms in shadows. Broken windows let in slivers of moonlight. The atmosphere is tense, cinematic, with dramatic chiaroscuro lighting. Shot in 4K, film grain, anamorphic lens flare.",
  "negative_prompt": "cartoon, anime, bright lighting, clean modern interior, daytime, multiple people",
  "style_keywords": ["noir", "thriller", "atmospheric", "cinematic", "dramatic lighting"],
  "camera_settings": {
    "focal_length": "35mm",
    "aperture": "f/2.0",
    "aspect_ratio": "2.39:1"
  },
  "confidence": 0.94
}""",
    },
]


# =============================================================================
# Enhanced Prompt Templates
# =============================================================================

ENHANCED_SHOT_GENERATION_TEMPLATE = PromptTemplate(
    name="enhanced_shot_generation",
    category=PromptCategory.SHOT_GENERATION,
    system_prompt="""You are an expert cinematographer and film editor analyzing screenplay scenes.

Your task is to break down scenes into individual shots that will be used for AI video generation.

For each shot, provide:
1. Shot type (wide, medium, close-up, extreme_close, pov, over_shoulder, establishing, insert)
2. Detailed visual description for video generation
3. Camera movement (static, pan, tilt, dolly, tracking, handheld, crane)
4. Duration in seconds
5. Characters visible in frame
6. Any dialogue with speaker and emotion

Guidelines:
- Create shots that tell the story visually
- Vary shot types for visual interest
- Consider pacing and rhythm
- Include reaction shots for dialogue scenes
- Add establishing shots for new locations
- Use close-ups for emotional moments

Always output valid JSON with a confidence score (0.0-1.0) indicating your certainty about the breakdown.""",
    user_template="""Break down this scene into individual shots:

{scene_content}

Characters in this scene: {characters}

Output format: JSON with 'shots' array and 'confidence' score.""",
    few_shot_examples=SHOT_GENERATION_EXAMPLES,
    expected_output_format="json",
    max_tokens=3000,
    temperature=0.7,
)

ENHANCED_CHARACTER_ANALYSIS_TEMPLATE = PromptTemplate(
    name="enhanced_character_analysis",
    category=PromptCategory.CHARACTER_ANALYSIS,
    system_prompt="""You are an expert script analyst specializing in character development.

Analyze characters from screenplay content to extract:
1. Role and importance (protagonist, antagonist, supporting, etc.)
2. Character arc type (transformation, steadfast, corruption, redemption)
3. Personality traits (dominant, hidden, evolving)
4. Visual appearance suggestions for AI generation
5. Voice characteristics for TTS

Be specific and consistent. Focus on what can be visually represented.""",
    user_template="""Analyze this character based on their appearances in the screenplay:

{character_info}

Provide a detailed character profile for visual consistency in AI generation.""",
    few_shot_examples=CHARACTER_ANALYSIS_EXAMPLES,
    expected_output_format="json",
    max_tokens=2000,
    temperature=0.6,
)

ENHANCED_VISUAL_DESCRIPTION_TEMPLATE = PromptTemplate(
    name="enhanced_visual_description",
    category=PromptCategory.VISUAL_DESCRIPTION,
    system_prompt="""You are an expert prompt engineer for AI video generation systems.

Transform shot descriptions into detailed visual prompts optimized for AI video generation.

Include:
1. Detailed visual description with specific details
2. Lighting and atmosphere
3. Camera specs (focal length, aperture, aspect ratio)
4. Style keywords for the visual aesthetic
5. Negative prompt to avoid unwanted elements

Focus on cinematic quality and consistency.""",
    user_template="""Create an AI video generation prompt for this shot:

Shot description: {shot_description}
Scene context: {scene_context}
Character appearances: {character_appearances}
Visual style: {visual_style}""",
    few_shot_examples=VISUAL_DESCRIPTION_EXAMPLES,
    expected_output_format="json",
    max_tokens=1500,
    temperature=0.8,
)


# =============================================================================
# Prompt Cache
# =============================================================================


class PromptCache:
    """Cache for prompt results to avoid redundant LLM calls."""

    def __init__(self, max_size: int = 1000) -> None:
        self.max_size = max_size
        self._cache: dict[str, dict[str, Any]] = {}
        self._access_order: list[str] = []

    def _compute_key(self, template_name: str, inputs: dict[str, Any]) -> str:
        """Compute cache key from template and inputs."""
        content = f"{template_name}:{json.dumps(inputs, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def get(self, template_name: str, inputs: dict[str, Any]) -> dict[str, Any] | None:
        """Get cached result if available."""
        key = self._compute_key(template_name, inputs)
        if key in self._cache:
            # Update access order for LRU
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        return None

    def set(self, template_name: str, inputs: dict[str, Any], result: dict[str, Any]) -> None:
        """Cache a result."""
        key = self._compute_key(template_name, inputs)

        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size:
            oldest_key = self._access_order.pop(0)
            del self._cache[oldest_key]

        self._cache[key] = result
        self._access_order.append(key)

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._access_order.clear()

    @property
    def size(self) -> int:
        """Current cache size."""
        return len(self._cache)


# =============================================================================
# Confidence Scoring
# =============================================================================


def compute_confidence_score(
    output: dict[str, Any],
    expected_fields: list[str],
    min_items: int = 1,
) -> ConfidenceScore:
    """Compute confidence score for LLM output.

    Args:
        output: The LLM output to evaluate
        expected_fields: Fields that should be present
        min_items: Minimum items expected in arrays

    Returns:
        ConfidenceScore with detailed breakdown
    """
    completeness_issues = []
    consistency_issues = []
    quality_issues = []

    # Check field completeness
    fields_present = sum(1 for f in expected_fields if f in output)
    fields_present / len(expected_fields) if expected_fields else 1.0

    for field_name in expected_fields:
        if field_name not in output:
            completeness_issues.append(f"Missing field: {field_name}")

    # Check array sizes
    for key, value in output.items():
        if isinstance(value, list) and len(value) < min_items:
            completeness_issues.append(f"Too few items in {key}: {len(value)}")

    # Check for common quality issues
    output_str = json.dumps(output)

    if "TODO" in output_str or "PLACEHOLDER" in output_str:
        quality_issues.append("Contains placeholder text")

    if len(output_str) < 100:
        quality_issues.append("Output seems too short")

    # Compute scores
    completeness_score = max(0.0, 1.0 - len(completeness_issues) * 0.2)
    consistency_score = max(0.0, 1.0 - len(consistency_issues) * 0.2)
    quality_score = max(0.0, 1.0 - len(quality_issues) * 0.2)

    overall = (completeness_score + consistency_score + quality_score) / 3

    issues = completeness_issues + consistency_issues + quality_issues
    reasoning = "; ".join(issues) if issues else "All checks passed"

    return ConfidenceScore(
        overall=round(overall, 3),
        completeness=round(completeness_score, 3),
        consistency=round(consistency_score, 3),
        quality=round(quality_score, 3),
        reasoning=reasoning,
    )


# =============================================================================
# Template Registry
# =============================================================================


class EnhancedPromptRegistry:
    """Registry of enhanced prompt templates."""

    _templates: dict[str, PromptTemplate] = {
        "shot_generation": ENHANCED_SHOT_GENERATION_TEMPLATE,
        "character_analysis": ENHANCED_CHARACTER_ANALYSIS_TEMPLATE,
        "visual_description": ENHANCED_VISUAL_DESCRIPTION_TEMPLATE,
    }

    _cache = PromptCache()

    @classmethod
    def get_template(cls, name: str) -> PromptTemplate | None:
        """Get a template by name."""
        return cls._templates.get(name)

    @classmethod
    def register_template(cls, template: PromptTemplate) -> None:
        """Register a custom template."""
        cls._templates[template.name] = template

    @classmethod
    def list_templates(cls) -> list[str]:
        """List all registered template names."""
        return list(cls._templates.keys())

    @classmethod
    def build_prompt(
        cls,
        template_name: str,
        inputs: dict[str, Any],
        include_examples: bool = True,
    ) -> dict[str, str] | None:
        """Build a complete prompt from template.

        Args:
            template_name: Name of the template
            inputs: Variables to fill in the template
            include_examples: Whether to include few-shot examples

        Returns:
            Dict with 'system' and 'user' prompts, or None if template not found
        """
        template = cls.get_template(template_name)
        if not template:
            return None

        # Build system prompt with examples
        system_prompt = template.system_prompt

        if include_examples and template.few_shot_examples:
            examples_text = "\n\n--- EXAMPLES ---\n"
            for i, example in enumerate(template.few_shot_examples, 1):
                examples_text += (
                    f"\nExample {i}:\nInput:\n{example['input']}\n\nOutput:\n{example['output']}\n"
                )
            examples_text += "\n--- END EXAMPLES ---\n"
            system_prompt += examples_text

        # Build user prompt
        user_prompt = template.user_template.format(**inputs)

        return {
            "system": system_prompt,
            "user": user_prompt,
            "max_tokens": template.max_tokens,
            "temperature": template.temperature,
        }

    @classmethod
    def get_cache(cls) -> PromptCache:
        """Get the prompt cache."""
        return cls._cache
