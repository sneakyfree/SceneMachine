"""Screenplay processing workflow."""

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from scenemachine.workflows.base import (
    Workflow,
    WorkflowRegistry,
    WorkflowStep,
)

logger = logging.getLogger(__name__)


@dataclass
class ScreenplayWorkflowContext:
    """Context for screenplay processing workflow."""

    project_id: UUID
    screenplay_id: UUID | None = None
    file_path: str | None = None
    raw_content: str | None = None
    parsed_content: dict | None = None
    movie_plan: dict | None = None
    characters: list[dict] = None
    scenes: list[dict] = None

    def __post_init__(self):
        if self.characters is None:
            self.characters = []
        if self.scenes is None:
            self.scenes = []


@WorkflowRegistry.register
class ScreenplayProcessingWorkflow(Workflow[ScreenplayWorkflowContext]):
    """Workflow for processing a screenplay from upload to plan generation."""

    @property
    def workflow_type(self) -> str:
        return "screenplay_processing"

    def define_steps(self) -> list[WorkflowStep]:
        return [
            WorkflowStep(
                id="validate",
                name="Validate Screenplay",
                description="Validate screenplay file format and content",
                handler="step_validate",
            ),
            WorkflowStep(
                id="parse",
                name="Parse Screenplay",
                description="Parse screenplay into structured format",
                handler="step_parse",
                dependencies=["validate"],
            ),
            WorkflowStep(
                id="extract_characters",
                name="Extract Characters",
                description="Extract character information from screenplay",
                handler="step_extract_characters",
                dependencies=["parse"],
            ),
            WorkflowStep(
                id="extract_scenes",
                name="Extract Scenes",
                description="Extract scene breakdown from screenplay",
                handler="step_extract_scenes",
                dependencies=["parse"],
            ),
            WorkflowStep(
                id="analyze_structure",
                name="Analyze Structure",
                description="Analyze screenplay structure and pacing",
                handler="step_analyze_structure",
                dependencies=["extract_characters", "extract_scenes"],
            ),
            WorkflowStep(
                id="generate_plan",
                name="Generate Movie Plan",
                description="Generate high-level movie plan",
                handler="step_generate_plan",
                dependencies=["analyze_structure"],
            ),
        ]

    async def step_validate(self, context: dict[str, Any]) -> dict[str, Any]:
        """Validate the screenplay file."""
        logger.info("Validating screenplay...")

        file_path = context.get("file_path")
        raw_content = context.get("raw_content")

        if not file_path and not raw_content:
            raise ValueError("No screenplay file or content provided")

        # If file path provided, read content
        if file_path and not raw_content:
            with open(file_path, encoding="utf-8") as f:
                raw_content = f.read()

        if not raw_content or len(raw_content.strip()) < 100:
            raise ValueError("Screenplay content is too short or empty")

        return {"raw_content": raw_content, "validated": True}

    async def step_parse(self, context: dict[str, Any]) -> dict[str, Any]:
        """Parse screenplay into structured format."""
        logger.info("Parsing screenplay...")

        raw_content = context.get("raw_content", "")

        # Basic parsing structure (would use fountain parser in production)
        parsed = {
            "format": "fountain",
            "title": self._extract_title(raw_content),
            "author": self._extract_author(raw_content),
            "elements": self._parse_elements(raw_content),
        }

        return {"parsed_content": parsed}

    async def step_extract_characters(self, context: dict[str, Any]) -> dict[str, Any]:
        """Extract characters from parsed screenplay."""
        logger.info("Extracting characters...")

        parsed = context.get("parsed_content", {})
        elements = parsed.get("elements", [])

        characters = {}
        for element in elements:
            if element.get("type") == "character":
                name = element.get("text", "").strip().upper()
                if name and name not in characters:
                    characters[name] = {
                        "name": name,
                        "dialogue_count": 0,
                        "scene_appearances": [],
                    }
                if name in characters:
                    characters[name]["dialogue_count"] += 1

        return {"characters": list(characters.values())}

    async def step_extract_scenes(self, context: dict[str, Any]) -> dict[str, Any]:
        """Extract scenes from parsed screenplay."""
        logger.info("Extracting scenes...")

        parsed = context.get("parsed_content", {})
        elements = parsed.get("elements", [])

        scenes = []
        current_scene = None
        scene_num = 0

        for element in elements:
            if element.get("type") == "scene_heading":
                if current_scene:
                    scenes.append(current_scene)

                scene_num += 1
                heading = element.get("text", "")
                current_scene = {
                    "scene_number": str(scene_num),
                    "heading": heading,
                    "scene_type": self._parse_scene_type(heading),
                    "location": self._parse_location(heading),
                    "time_of_day": self._parse_time_of_day(heading),
                    "action": [],
                    "dialogue": [],
                }

            elif current_scene:
                if element.get("type") == "action":
                    current_scene["action"].append(element.get("text", ""))
                elif element.get("type") == "dialogue":
                    current_scene["dialogue"].append(element.get("text", ""))

        if current_scene:
            scenes.append(current_scene)

        return {"scenes": scenes}

    async def step_analyze_structure(self, context: dict[str, Any]) -> dict[str, Any]:
        """Analyze screenplay structure."""
        logger.info("Analyzing structure...")

        scenes = context.get("scenes", [])
        characters = context.get("characters", [])

        analysis = {
            "total_scenes": len(scenes),
            "total_characters": len(characters),
            "estimated_runtime_minutes": len(scenes) * 2,  # Rough estimate
            "act_structure": self._identify_acts(scenes),
            "pacing_notes": self._analyze_pacing(scenes),
        }

        return {"structure_analysis": analysis}

    async def step_generate_plan(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate movie plan."""
        logger.info("Generating movie plan...")

        parsed = context.get("parsed_content", {})
        scenes = context.get("scenes", [])
        characters = context.get("characters", [])
        analysis = context.get("structure_analysis", {})

        movie_plan = {
            "title": parsed.get("title", "Untitled"),
            "author": parsed.get("author"),
            "logline": self._generate_logline(scenes),
            "genre": self._detect_genre(scenes),
            "tone": self._detect_tone(scenes),
            "visual_style": {
                "recommended_style": "cinematic",
                "color_palette": "neutral",
                "aspect_ratio": "2.39:1",
            },
            "character_summary": [
                {
                    "name": c["name"],
                    "importance": "major" if c["dialogue_count"] > 10 else "minor",
                    "dialogue_count": c["dialogue_count"],
                }
                for c in characters
            ],
            "scene_breakdown": [
                {
                    "scene_number": s["scene_number"],
                    "location": s["location"],
                    "time_of_day": s["time_of_day"],
                    "estimated_shots": max(3, len(s.get("action", [])) + 2),
                }
                for s in scenes
            ],
            "total_scenes": analysis.get("total_scenes", 0),
            "estimated_runtime": analysis.get("estimated_runtime_minutes", 0),
        }

        return {"movie_plan": movie_plan}

    # Helper methods

    def _extract_title(self, content: str) -> str:
        """Extract title from screenplay."""
        lines = content.split("\n")
        for line in lines[:20]:
            if line.strip().startswith("Title:"):
                return line.replace("Title:", "").strip()
        return "Untitled"

    def _extract_author(self, content: str) -> str | None:
        """Extract author from screenplay."""
        lines = content.split("\n")
        for line in lines[:20]:
            lower = line.lower().strip()
            if lower.startswith("by ") or lower.startswith("written by"):
                return line.split(" ", 1)[-1].strip()
        return None

    def _parse_elements(self, content: str) -> list[dict]:
        """Parse screenplay into elements."""
        elements = []
        lines = content.split("\n")

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Scene heading (INT./EXT.)
            if stripped.startswith(("INT.", "EXT.", "INT/EXT", "I/E")):
                elements.append({"type": "scene_heading", "text": stripped})
            # Character name (all caps before dialogue)
            elif stripped.isupper() and len(stripped) < 50 and not stripped.startswith(("INT", "EXT")):
                elements.append({"type": "character", "text": stripped})
            # Parenthetical
            elif stripped.startswith("(") and stripped.endswith(")"):
                elements.append({"type": "parenthetical", "text": stripped})
            # Everything else is action or dialogue
            else:
                elements.append({"type": "action", "text": stripped})

        return elements

    def _parse_scene_type(self, heading: str) -> str:
        """Parse scene type from heading."""
        upper = heading.upper()
        if upper.startswith("INT"):
            return "interior"
        elif upper.startswith("EXT"):
            return "exterior"
        return "unknown"

    def _parse_location(self, heading: str) -> str:
        """Parse location from scene heading."""
        parts = heading.split("-")
        if len(parts) >= 2:
            return parts[0].replace("INT.", "").replace("EXT.", "").strip()
        return heading

    def _parse_time_of_day(self, heading: str) -> str:
        """Parse time of day from scene heading."""
        upper = heading.upper()
        if "DAY" in upper:
            return "day"
        elif "NIGHT" in upper:
            return "night"
        elif "DAWN" in upper:
            return "dawn"
        elif "DUSK" in upper:
            return "dusk"
        return "day"

    def _identify_acts(self, scenes: list[dict]) -> dict:
        """Identify act structure."""
        total = len(scenes)
        return {
            "act1_end": int(total * 0.25),
            "act2_midpoint": int(total * 0.5),
            "act2_end": int(total * 0.75),
            "act3_start": int(total * 0.75),
        }

    def _analyze_pacing(self, scenes: list[dict]) -> list[str]:
        """Analyze pacing."""
        notes = []
        if len(scenes) > 100:
            notes.append("Long screenplay - consider tightening")
        if len(scenes) < 20:
            notes.append("Short screenplay - may need expansion")
        return notes

    def _generate_logline(self, scenes: list[dict]) -> str:
        """Generate a placeholder logline."""
        return "A compelling story unfolds across multiple locations and characters."

    def _detect_genre(self, scenes: list[dict]) -> str:
        """Detect genre from scenes."""
        return "drama"

    def _detect_tone(self, scenes: list[dict]) -> str:
        """Detect tone from scenes."""
        return "dramatic"
