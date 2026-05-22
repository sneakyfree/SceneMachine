"""LLM Service Implementation.

Provides AI-powered analysis and generation using LLM providers.
Supports Anthropic Claude, OpenAI GPT, and mock provider for testing.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from scenemachine.services.llm.prompts import CopilotPrompts, PromptTemplates

logger = logging.getLogger(__name__)


class LLMProvider(StrEnum):
    """Supported LLM providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    MOCK = "mock"


@dataclass
class LLMResponse:
    """Response from LLM service."""

    content: str
    model: str
    provider: LLMProvider
    usage: dict[str, int] = field(default_factory=dict)
    raw_response: Any | None = None

    def parse_json(self) -> dict[str, Any] | None:
        """Parse JSON from response content.

        Handles responses that may have markdown code blocks around JSON.

        Returns:
            Parsed JSON dict or None if parsing fails
        """
        content = self.content.strip()

        # Try to extract JSON from markdown code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            content = json_match.group(1).strip()

        # Try to find JSON object or array
        if not content.startswith(("{", "[")):
            # Look for first { or [ in content
            obj_start = content.find("{")
            arr_start = content.find("[")
            if obj_start >= 0 or arr_start >= 0:
                if obj_start >= 0 and (arr_start < 0 or obj_start < arr_start):
                    content = content[obj_start:]
                else:
                    content = content[arr_start:]

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from LLM response: {e}")
            return None


@runtime_checkable
class LLMBackend(Protocol):
    """Protocol for LLM backend implementations."""

    async def complete(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate a completion from the LLM."""
        ...


class AnthropicBackend:
    """Anthropic Claude backend."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self._client = None

    async def _get_client(self):
        """Get or create the Anthropic client."""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise RuntimeError(
                    "anthropic package not installed. Install with: pip install anthropic"
                )
        return self._client

    async def complete(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate a completion using Claude."""
        client = await self._get_client()

        # Convert messages to Anthropic format
        anthropic_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                # System messages go in the system parameter
                continue
            anthropic_messages.append({"role": role, "content": msg["content"]})

        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system or PromptTemplates.SYSTEM_CONTEXT,
                messages=anthropic_messages,
            )

            content = ""
            if response.content:
                content = response.content[0].text

            return LLMResponse(
                content=content,
                model=self.model,
                provider=LLMProvider.ANTHROPIC,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                raw_response=response,
            )
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


class OpenAIBackend:
    """OpenAI GPT backend."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self._client = None

    async def _get_client(self):
        """Get or create the OpenAI client."""
        if self._client is None:
            try:
                import openai

                self._client = openai.AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("openai package not installed. Install with: pip install openai")
        return self._client

    async def complete(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate a completion using GPT."""
        client = await self._get_client()

        # Build messages with system prompt
        openai_messages = []
        if system:
            openai_messages.append({"role": "system", "content": system})
        else:
            openai_messages.append({"role": "system", "content": PromptTemplates.SYSTEM_CONTEXT})

        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                continue  # Already added system message
            openai_messages.append({"role": role, "content": msg["content"]})

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            content = ""
            if response.choices:
                content = response.choices[0].message.content or ""

            return LLMResponse(
                content=content,
                model=self.model,
                provider=LLMProvider.OPENAI,
                usage={
                    "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "output_tokens": response.usage.completion_tokens if response.usage else 0,
                },
                raw_response=response,
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class MockBackend:
    """Mock backend for testing."""

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.responses = responses or {}
        self.call_history: list[dict[str, Any]] = []

    async def complete(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Return mock response."""
        self.call_history.append(
            {
                "messages": messages,
                "system": system,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )

        # Get last user message for response lookup
        last_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break

        # Check for custom response
        for key, response in self.responses.items():
            if key.lower() in last_message.lower():
                return LLMResponse(
                    content=response,
                    model="mock-model",
                    provider=LLMProvider.MOCK,
                    usage={"input_tokens": 100, "output_tokens": 50},
                )

        # Default mock response
        return LLMResponse(
            content=self._generate_mock_response(last_message),
            model="mock-model",
            provider=LLMProvider.MOCK,
            usage={"input_tokens": 100, "output_tokens": 50},
        )

    def _generate_mock_response(self, message: str) -> str:
        """Generate appropriate mock response based on message content."""
        message_lower = message.lower()

        if "analyze" in message_lower or "analysis" in message_lower:
            return json.dumps(
                {
                    "overallScore": 0.82,
                    "pacing": {
                        "score": 0.78,
                        "feedback": "Good rhythm with room for tightening in Act 2.",
                        "suggestions": ["Consider trimming Scene 4 exposition"],
                    },
                    "characterDevelopment": {
                        "score": 0.85,
                        "feedback": "Strong character arcs, particularly the protagonist.",
                        "suggestions": ["Deepen antagonist motivation"],
                    },
                    "visualStorytelling": {
                        "score": 0.80,
                        "feedback": "Effective use of visual metaphors.",
                        "suggestions": ["Add more establishing shots"],
                    },
                    "dialogue": {
                        "score": 0.83,
                        "feedback": "Natural dialogue that reveals character.",
                        "suggestions": ["Vary sentence length in tense scenes"],
                    },
                    "suggestions": [
                        {
                            "id": "sug_001",
                            "type": "pacing",
                            "title": "Tighten Act 2",
                            "description": "The middle section could benefit from faster pacing.",
                            "confidence": 0.85,
                        }
                    ],
                }
            )

        if "suggest" in message_lower and "scene" in message_lower:
            return json.dumps(
                [
                    {
                        "id": "scene_sug_001",
                        "type": "scene",
                        "title": "Scene Flow Improvement",
                        "description": "Consider reordering the beats for better tension buildup.",
                        "confidence": 0.82,
                    },
                    {
                        "id": "scene_sug_002",
                        "type": "visual",
                        "title": "Lighting Enhancement",
                        "description": "This scene would benefit from more contrast lighting.",
                        "confidence": 0.78,
                    },
                ]
            )

        if "suggest" in message_lower and "shot" in message_lower:
            return json.dumps(
                [
                    {
                        "id": "shot_sug_001",
                        "type": "shot",
                        "title": "Camera Movement",
                        "description": "A slow push-in could enhance emotional impact.",
                        "confidence": 0.85,
                    }
                ]
            )

        if "enhance" in message_lower or "prompt" in message_lower:
            return "A cinematic wide shot captures the protagonist silhouetted against the amber sunset, their shadow stretching across cracked earth. The camera slowly dollies forward as dust particles catch the golden hour light, creating an atmosphere of solitude and determination. Shot in anamorphic lens with subtle lens flare."

        if "shot breakdown" in message_lower or "breakdown" in message_lower:
            return json.dumps(
                {
                    "estimated_duration_seconds": 45,
                    "shots": [
                        {
                            "sequence": 1,
                            "shot_type": "ESTABLISHING",
                            "camera_movement": "STATIC",
                            "description": "Wide establishing shot of the location",
                            "duration_seconds": 4,
                            "generation_prompt": "A wide cinematic establishing shot of the scene location.",
                            "notes": "Set the tone and geography",
                        },
                        {
                            "sequence": 2,
                            "shot_type": "MEDIUM",
                            "camera_movement": "DOLLY",
                            "description": "Medium shot introducing the character",
                            "duration_seconds": 6,
                            "generation_prompt": "Medium shot, character enters frame, slight dolly movement.",
                            "notes": "Character introduction",
                        },
                    ],
                }
            )

        # Default chat response
        return json.dumps(
            {
                "message": "I've analyzed the context and have some insights. The scene structure is solid, but consider adding more visual variety to maintain viewer engagement.",
                "suggestions": [
                    {
                        "id": "chat_sug_001",
                        "type": "pacing",
                        "title": "Pacing Adjustment",
                        "description": "Add a beat before the character's response for dramatic effect.",
                        "confidence": 0.78,
                    }
                ],
            }
        )


class LLMService:
    """LLM Service for AI-powered features.

    Supports multiple providers with automatic fallback.
    """

    def __init__(
        self,
        primary_provider: LLMProvider = LLMProvider.MOCK,
        fallback_provider: LLMProvider | None = None,
        anthropic_api_key: str | None = None,
        openai_api_key: str | None = None,
        anthropic_model: str = "claude-sonnet-4-20250514",
        openai_model: str = "gpt-4o",
    ) -> None:
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider
        self._backends: dict[LLMProvider, LLMBackend] = {}

        # Initialize backends based on available API keys
        if anthropic_api_key:
            self._backends[LLMProvider.ANTHROPIC] = AnthropicBackend(
                api_key=anthropic_api_key,
                model=anthropic_model,
            )

        if openai_api_key:
            self._backends[LLMProvider.OPENAI] = OpenAIBackend(
                api_key=openai_api_key,
                model=openai_model,
            )

        # Always have mock backend available
        self._backends[LLMProvider.MOCK] = MockBackend()

    def _get_backend(self, provider: LLMProvider) -> LLMBackend:
        """Get backend for provider."""
        backend = self._backends.get(provider)
        if backend is None:
            if provider == LLMProvider.MOCK:
                self._backends[LLMProvider.MOCK] = MockBackend()
                return self._backends[LLMProvider.MOCK]
            raise ValueError(f"Provider {provider} not configured")
        return backend

    async def _complete_with_fallback(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Complete with automatic fallback on failure."""
        try:
            backend = self._get_backend(self.primary_provider)
            return await backend.complete(
                messages=messages,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as primary_error:
            logger.warning(f"Primary provider {self.primary_provider} failed: {primary_error}")

            if self.fallback_provider:
                try:
                    backend = self._get_backend(self.fallback_provider)
                    return await backend.complete(
                        messages=messages,
                        system=system,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                except Exception as fallback_error:
                    logger.error(
                        f"Fallback provider {self.fallback_provider} failed: {fallback_error}"
                    )
                    raise fallback_error

            raise primary_error

    async def chat(
        self,
        message: str,
        project_context: dict[str, Any],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Handle chat interaction with the co-pilot.

        Args:
            message: User's message
            project_context: Current project context
            conversation_history: Previous messages

        Returns:
            Chat response with message and suggestions
        """
        prompt = CopilotPrompts.chat_prompt(
            message=message,
            project_context=project_context,
            conversation_history=conversation_history,
        )

        messages = [{"role": "user", "content": prompt}]

        response = await self._complete_with_fallback(
            messages=messages,
            max_tokens=2048,
            temperature=0.7,
        )

        # Try to parse structured response
        parsed = response.parse_json()
        if parsed and isinstance(parsed, dict):
            return {
                "message": parsed.get("message", response.content),
                "suggestions": parsed.get("suggestions", []),
                "relatedScenes": parsed.get("relatedScenes", []),
                "relatedShots": parsed.get("relatedShots", []),
            }

        # Return plain text response
        return {
            "message": response.content,
            "suggestions": [],
            "relatedScenes": [],
            "relatedShots": [],
        }

    async def analyze_project(
        self,
        project_context: dict[str, Any],
        scenes: list[dict[str, Any]],
        characters: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze a project comprehensively.

        Args:
            project_context: Project metadata
            scenes: List of scenes
            characters: List of characters

        Returns:
            Analysis results with scores and suggestions
        """
        from datetime import datetime

        prompt = CopilotPrompts.analyze_project_prompt(
            project_context=project_context,
            scenes=scenes,
            characters=characters,
        )

        messages = [{"role": "user", "content": prompt}]

        response = await self._complete_with_fallback(
            messages=messages,
            max_tokens=4096,
            temperature=0.5,  # Lower temperature for more consistent analysis
        )

        parsed = response.parse_json()
        if parsed and isinstance(parsed, dict):
            return {
                "projectId": project_context.get("id", ""),
                "overallScore": parsed.get("overallScore", 0.75),
                "pacing": parsed.get("pacing", {}),
                "characterDevelopment": parsed.get("characterDevelopment", {}),
                "visualStorytelling": parsed.get("visualStorytelling", {}),
                "dialogue": parsed.get("dialogue", {}),
                "suggestions": parsed.get("suggestions", []),
                "generatedAt": datetime.utcnow().isoformat(),
            }

        # Fallback with default structure
        return {
            "projectId": project_context.get("id", ""),
            "overallScore": 0.75,
            "pacing": {"score": 0.75, "feedback": response.content, "suggestions": []},
            "characterDevelopment": {"score": 0.75, "feedback": "", "suggestions": []},
            "visualStorytelling": {"score": 0.75, "feedback": "", "suggestions": []},
            "dialogue": {"score": 0.75, "feedback": "", "suggestions": []},
            "suggestions": [],
            "generatedAt": datetime.utcnow().isoformat(),
        }

    async def suggest_scene(
        self,
        scene: dict[str, Any],
        characters: list[dict[str, Any]],
        adjacent_scenes: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Get suggestions for a specific scene.

        Args:
            scene: Scene data
            characters: Characters in the scene
            adjacent_scenes: Previous and next scenes

        Returns:
            List of suggestions
        """
        prompt = CopilotPrompts.suggest_scene_prompt(
            scene=scene,
            characters=characters,
            adjacent_scenes=adjacent_scenes,
        )

        messages = [{"role": "user", "content": prompt}]

        response = await self._complete_with_fallback(
            messages=messages,
            max_tokens=2048,
            temperature=0.7,
        )

        parsed = response.parse_json()
        if parsed and isinstance(parsed, list):
            return parsed

        # Return empty list on parse failure
        return []

    async def suggest_shot(
        self,
        shot: dict[str, Any],
        scene_context: dict[str, Any],
        adjacent_shots: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Get suggestions for a specific shot.

        Args:
            shot: Shot data
            scene_context: Parent scene information
            adjacent_shots: Previous and next shots

        Returns:
            List of suggestions
        """
        prompt = CopilotPrompts.suggest_shot_prompt(
            shot=shot,
            scene_context=scene_context,
            adjacent_shots=adjacent_shots,
        )

        messages = [{"role": "user", "content": prompt}]

        response = await self._complete_with_fallback(
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )

        parsed = response.parse_json()
        if parsed and isinstance(parsed, list):
            return parsed

        return []

    async def enhance_prompt(
        self,
        original_prompt: str,
        shot_context: dict[str, Any],
        style_preferences: dict[str, Any] | None = None,
    ) -> str:
        """Enhance a video generation prompt.

        Args:
            original_prompt: The original prompt
            shot_context: Shot and scene context
            style_preferences: User style preferences

        Returns:
            Enhanced prompt string
        """
        prompt = CopilotPrompts.enhance_prompt_prompt(
            original_prompt=original_prompt,
            shot_context=shot_context,
            style_preferences=style_preferences,
        )

        messages = [{"role": "user", "content": prompt}]

        response = await self._complete_with_fallback(
            messages=messages,
            max_tokens=512,
            temperature=0.8,  # Higher temperature for creativity
        )

        # Return plain text response
        return response.content.strip()

    async def generate_shot_breakdown(
        self,
        scene: dict[str, Any],
        characters: list[dict[str, Any]],
        visual_style: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a shot breakdown for a scene.

        Args:
            scene: Scene data
            characters: Characters in the scene
            visual_style: Visual style preferences

        Returns:
            Shot breakdown with shots list
        """
        prompt = CopilotPrompts.generate_shot_breakdown_prompt(
            scene=scene,
            characters=characters,
            visual_style=visual_style,
        )

        messages = [{"role": "user", "content": prompt}]

        response = await self._complete_with_fallback(
            messages=messages,
            max_tokens=4096,
            temperature=0.6,
        )

        parsed = response.parse_json()
        if parsed and isinstance(parsed, dict):
            return parsed

        # Return minimal structure on parse failure
        return {"estimated_duration_seconds": 0, "shots": []}


# Global instance
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """Get the global LLM service instance.

    Returns:
        Configured LLMService instance
    """
    global _llm_service

    if _llm_service is None:
        import os

        # Try to get API keys from environment
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")

        # Determine primary provider based on available keys
        if anthropic_key:
            primary = LLMProvider.ANTHROPIC
            fallback = LLMProvider.OPENAI if openai_key else LLMProvider.MOCK
        elif openai_key:
            primary = LLMProvider.OPENAI
            fallback = LLMProvider.MOCK
        else:
            # Default to mock for development
            primary = LLMProvider.MOCK
            fallback = None
            logger.warning(
                "No LLM API keys configured. Using mock provider. "
                "Set ANTHROPIC_API_KEY or OPENAI_API_KEY for real LLM features."
            )

        _llm_service = LLMService(
            primary_provider=primary,
            fallback_provider=fallback,
            anthropic_api_key=anthropic_key,
            openai_api_key=openai_key,
        )

    return _llm_service


def reset_llm_service() -> None:
    """Reset the global LLM service instance.

    Useful for testing or reconfiguring.
    """
    global _llm_service
    _llm_service = None
