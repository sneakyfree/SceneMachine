"""LLM Prompt Templates.

Contains prompt templates for various AI-powered features in SceneMachine.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class PromptTemplates:
    """Common prompt templates."""

    SYSTEM_CONTEXT = """You are Steven, an expert AI assistant for SceneMachine, a screenplay-to-movie generation platform. You have deep knowledge of:
- Screenwriting and screenplay format
- Film production and cinematography
- Visual storytelling and scene composition
- Character development and dialogue
- Pacing and narrative structure
- Shot types and camera movements

Provide helpful, specific, and actionable feedback. Be constructive and supportive while offering professional insights."""

    ANALYSIS_FORMAT = """Provide your analysis in a structured JSON format with the following fields:
- summary: Brief overall assessment
- score: Numerical score from 0.0 to 1.0
- strengths: List of positive aspects
- improvements: List of suggested improvements
- details: Additional detailed analysis"""


class CopilotPrompts:
    """Prompts for the AI Co-pilot (Steven) feature."""

    @staticmethod
    def chat_prompt(
        message: str,
        project_context: dict[str, Any],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate prompt for chat interaction.

        Args:
            message: User's message
            project_context: Current project information
            conversation_history: Previous messages in conversation

        Returns:
            Formatted prompt string
        """
        context_parts = []

        if project_context.get("project_name"):
            context_parts.append(f"Project: {project_context['project_name']}")

        if project_context.get("screenplay_title"):
            context_parts.append(f"Screenplay: {project_context['screenplay_title']}")

        if project_context.get("current_scene"):
            scene = project_context["current_scene"]
            context_parts.append(
                f"Current Scene: {scene.get('heading', 'Unknown')} - {scene.get('description', '')}"
            )

        if project_context.get("current_shot"):
            shot = project_context["current_shot"]
            context_parts.append(
                f"Current Shot: {shot.get('type', 'Unknown')} - {shot.get('description', '')}"
            )

        context_str = "\n".join(context_parts) if context_parts else "No specific context"

        history_str = ""
        if conversation_history:
            history_str = "\n\nConversation History:\n"
            for entry in conversation_history[-5:]:  # Last 5 messages
                role = entry.get("role", "user")
                content = entry.get("content", "")
                history_str += f"{role.capitalize()}: {content}\n"

        return f"""Project Context:
{context_str}
{history_str}
User Message: {message}

Provide a helpful, specific response. If appropriate, include:
1. Direct answer to their question
2. Specific suggestions with concrete examples
3. References to relevant scenes or shots if applicable

Format suggestions as JSON objects with: id, type, title, description, confidence (0.0-1.0)"""

    @staticmethod
    def analyze_project_prompt(
        project_context: dict[str, Any],
        scenes: list[dict[str, Any]],
        characters: list[dict[str, Any]],
    ) -> str:
        """Generate prompt for full project analysis.

        Args:
            project_context: Project metadata
            scenes: List of scenes in the project
            characters: List of characters

        Returns:
            Formatted prompt string
        """
        scenes_summary = "\n".join(
            f"- Scene {s.get('sequence', i+1)}: {s.get('heading', 'Unknown')}"
            for i, s in enumerate(scenes[:20])  # Limit to 20 scenes
        )

        characters_summary = "\n".join(
            f"- {c.get('name', 'Unknown')}: {c.get('description', 'No description')[:100]}"
            for c in characters[:10]  # Limit to 10 characters
        )

        return f"""Analyze this screenplay project comprehensively:

Project: {project_context.get('name', 'Untitled')}
Genre: {project_context.get('genre', 'Unknown')}
Total Scenes: {len(scenes)}

Scenes:
{scenes_summary}

Characters:
{characters_summary}

Provide analysis in JSON format with these sections:
{{
    "overallScore": 0.0-1.0,
    "pacing": {{
        "score": 0.0-1.0,
        "feedback": "string",
        "suggestions": ["string"]
    }},
    "characterDevelopment": {{
        "score": 0.0-1.0,
        "feedback": "string",
        "suggestions": ["string"]
    }},
    "visualStorytelling": {{
        "score": 0.0-1.0,
        "feedback": "string",
        "suggestions": ["string"]
    }},
    "dialogue": {{
        "score": 0.0-1.0,
        "feedback": "string",
        "suggestions": ["string"]
    }},
    "suggestions": [
        {{
            "id": "string",
            "type": "scene|shot|character|dialogue|pacing|visual",
            "title": "string",
            "description": "string",
            "confidence": 0.0-1.0
        }}
    ]
}}"""

    @staticmethod
    def suggest_scene_prompt(
        scene: dict[str, Any],
        characters: list[dict[str, Any]],
        adjacent_scenes: dict[str, Any] | None = None,
    ) -> str:
        """Generate prompt for scene-specific suggestions.

        Args:
            scene: Scene data
            characters: Characters in the scene
            adjacent_scenes: Previous and next scenes for context

        Returns:
            Formatted prompt string
        """
        chars_in_scene = ", ".join(c.get("name", "Unknown") for c in characters)

        context = ""
        if adjacent_scenes:
            if adjacent_scenes.get("previous"):
                context += f"Previous Scene: {adjacent_scenes['previous'].get('heading', 'Unknown')}\n"
            if adjacent_scenes.get("next"):
                context += f"Next Scene: {adjacent_scenes['next'].get('heading', 'Unknown')}\n"

        return f"""Analyze this scene and provide specific improvement suggestions:

Scene: {scene.get('heading', 'Unknown')}
Description: {scene.get('description', 'No description')}
Mood: {scene.get('mood', 'Unknown')}
Characters Present: {chars_in_scene}

{context}

Shots in Scene:
{chr(10).join(f"- Shot {i+1}: {s.get('description', '')[:100]}" for i, s in enumerate(scene.get('shots', [])[:10]))}

Provide 2-4 suggestions in JSON format:
[
    {{
        "id": "unique_id",
        "type": "scene|visual|pacing|dialogue",
        "title": "Brief title",
        "description": "Detailed suggestion",
        "confidence": 0.0-1.0
    }}
]"""

    @staticmethod
    def suggest_shot_prompt(
        shot: dict[str, Any],
        scene_context: dict[str, Any],
        adjacent_shots: dict[str, Any] | None = None,
    ) -> str:
        """Generate prompt for shot-specific suggestions.

        Args:
            shot: Shot data
            scene_context: Parent scene information
            adjacent_shots: Previous and next shots for context

        Returns:
            Formatted prompt string
        """
        context = ""
        if adjacent_shots:
            if adjacent_shots.get("previous"):
                context += f"Previous Shot: {adjacent_shots['previous'].get('description', 'Unknown')[:100]}\n"
            if adjacent_shots.get("next"):
                context += f"Next Shot: {adjacent_shots['next'].get('description', 'Unknown')[:100]}\n"

        return f"""Analyze this shot and provide improvement suggestions:

Scene: {scene_context.get('heading', 'Unknown')}
Scene Mood: {scene_context.get('mood', 'Unknown')}

Shot Details:
- Type: {shot.get('shot_type', 'Unknown')}
- Camera Movement: {shot.get('camera_movement', 'None')}
- Description: {shot.get('description', 'No description')}
- Prompt: {shot.get('generation_prompt', 'No prompt')[:200]}

{context}

Provide 1-2 suggestions in JSON format:
[
    {{
        "id": "unique_id",
        "type": "shot|camera|composition",
        "title": "Brief title",
        "description": "Detailed suggestion for improving this shot",
        "confidence": 0.0-1.0
    }}
]"""

    @staticmethod
    def enhance_prompt_prompt(
        original_prompt: str,
        shot_context: dict[str, Any],
        style_preferences: dict[str, Any] | None = None,
    ) -> str:
        """Generate prompt for enhancing a video generation prompt.

        Args:
            original_prompt: The original generation prompt
            shot_context: Shot and scene context
            style_preferences: User's style preferences

        Returns:
            Formatted prompt string
        """
        style_str = ""
        if style_preferences:
            style_str = f"""
Style Preferences:
- Aspect Ratio: {style_preferences.get('aspect_ratio', '16:9')}
- Color Palette: {style_preferences.get('color_palette', 'natural')}
- Lighting: {style_preferences.get('lighting', 'cinematic')}"""

        return f"""Enhance this video generation prompt for better results:

Original Prompt: {original_prompt}

Shot Context:
- Type: {shot_context.get('shot_type', 'Unknown')}
- Camera: {shot_context.get('camera_movement', 'Static')}
- Scene Mood: {shot_context.get('mood', 'neutral')}
{style_str}

Provide an enhanced prompt that:
1. Maintains the original intent
2. Adds cinematic quality descriptors
3. Includes appropriate camera movement language
4. Specifies lighting and atmosphere
5. Keeps it under 200 words

Return only the enhanced prompt text, no JSON or formatting."""

    @staticmethod
    def generate_shot_breakdown_prompt(
        scene: dict[str, Any],
        characters: list[dict[str, Any]],
        visual_style: dict[str, Any] | None = None,
    ) -> str:
        """Generate prompt for creating shot breakdown from scene.

        Args:
            scene: Scene data
            characters: Characters in the scene
            visual_style: Overall visual style preferences

        Returns:
            Formatted prompt string
        """
        chars_str = ", ".join(c.get("name", "Unknown") for c in characters)

        style_str = ""
        if visual_style:
            style_str = f"""
Visual Style:
- Look: {visual_style.get('overall_look', 'cinematic')}
- Lighting: {visual_style.get('lighting_style', 'natural')}
- Camera Style: {visual_style.get('camera_movement', 'dynamic')}"""

        return f"""Create a shot breakdown for this scene:

Scene: {scene.get('heading', 'Unknown')}
Description: {scene.get('description', 'No description')}
Mood: {scene.get('mood', 'Unknown')}
Characters: {chars_str}
{style_str}

Action/Dialogue:
{scene.get('content', 'No content available')[:1000]}

Generate a shot breakdown in JSON format:
{{
    "estimated_duration_seconds": number,
    "shots": [
        {{
            "sequence": number,
            "shot_type": "WIDE|MEDIUM|CLOSE_UP|EXTREME_CLOSE_UP|OVER_THE_SHOULDER|POV|ESTABLISHING|TWO_SHOT",
            "camera_movement": "STATIC|PAN|TILT|DOLLY|TRACKING|CRANE|HANDHELD|STEADICAM",
            "description": "Brief description of the shot content",
            "duration_seconds": number,
            "generation_prompt": "Detailed prompt for video generation",
            "notes": "Optional production notes"
        }}
    ]
}}

Include 3-8 shots that effectively cover the scene's content."""
