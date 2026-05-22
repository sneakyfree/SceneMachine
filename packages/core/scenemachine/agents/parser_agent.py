"""
Parser Agent - Screenplay parsing and shot list generation.

Responsibilities:
- Parse screenplay files (Fountain, FDX, PDF)
- Extract characters, scenes, and dialogue
- Generate shot lists with prompts
- Detect contradictions in character descriptions
"""

import logging
from typing import Any

from scenemachine.agents.base import (
    ActionContext,
    ActionResult,
    ActionStatus,
    AgentType,
    BaseAgent,
)

logger = logging.getLogger(__name__)


class ParserAgent(BaseAgent):
    """
    Agent responsible for parsing screenplays and generating shot lists.

    Autonomous actions:
    - parse_screenplay: Parse uploaded screenplay files
    - extract_characters: Extract character list from parsed script
    - generate_shot_list: Create shot breakdown for scenes

    Requires approval:
    - resolve_contradiction: When character descriptions conflict
    """

    @property
    def agent_type(self) -> AgentType:
        return AgentType.PARSER

    @property
    def capabilities(self) -> list[str]:
        return [
            "parse_screenplay",
            "extract_characters",
            "generate_shot_list",
            "detect_contradictions",
            "resolve_contradiction",
        ]

    @property
    def requires_approval(self) -> list[str]:
        return ["resolve_contradiction"]

    async def _execute_action(
        self,
        action_name: str,
        context: ActionContext,
        **kwargs,
    ) -> ActionResult:
        """Execute parser actions."""
        if action_name == "parse_screenplay":
            return await self._parse_screenplay(context, **kwargs)
        elif action_name == "extract_characters":
            return await self._extract_characters(context, **kwargs)
        elif action_name == "generate_shot_list":
            return await self._generate_shot_list(context, **kwargs)
        elif action_name == "detect_contradictions":
            return await self._detect_contradictions(context, **kwargs)
        else:
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=f"Unknown action: {action_name}",
            )

    async def _parse_screenplay(
        self,
        context: ActionContext,
        file_path: str,
        file_type: str = "auto",
    ) -> ActionResult:
        """Parse a screenplay file and extract structure."""
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=f"File not found: {file_path}",
            )

        # Auto-detect file type
        if file_type == "auto":
            suffix = path.suffix.lower()
            if suffix == ".fountain":
                file_type = "fountain"
            elif suffix == ".fdx":
                file_type = "fdx"
            elif suffix == ".pdf":
                file_type = "pdf"
            else:
                file_type = "txt"

        try:
            # Use appropriate parser
            if file_type == "fountain":
                from scenemachine.parsers.fountain import FountainParser
                parser = FountainParser()
                result = parser.parse(path.read_text())
            elif file_type == "fdx":
                from scenemachine.parsers.fdx import FDXParser
                parser = FDXParser()
                result = parser.parse(path.read_text())
            elif file_type == "pdf":
                from scenemachine.parsers.pdf import PDFParser
                parser = PDFParser()
                result = await parser.parse(file_path)
            else:
                # Plain text fallback
                result = {
                    "title": path.stem,
                    "raw_text": path.read_text(),
                    "scenes": [],
                    "characters": [],
                }

            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.COMPLETED,
                success=True,
                output=result,
                confidence=0.9 if result.get("scenes") else 0.5,
            )

        except Exception as e:
            logger.exception(f"Failed to parse screenplay: {e}")
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=str(e),
            )

    async def _extract_characters(
        self,
        context: ActionContext,
        parsed_screenplay: dict[str, Any],
    ) -> ActionResult:
        """Extract character information from parsed screenplay."""
        characters = []

        # Extract from parsed data
        if "characters" in parsed_screenplay:
            for char in parsed_screenplay["characters"]:
                characters.append({
                    "name": char.get("name", "Unknown"),
                    "description": char.get("description", ""),
                    "dialogue_count": char.get("dialogue_count", 0),
                    "first_appearance": char.get("first_scene", None),
                })

        # Also scan scenes for character mentions
        seen_names = {c["name"].upper() for c in characters}
        for scene in parsed_screenplay.get("scenes", []):
            for element in scene.get("elements", []):
                if element.get("type") == "character":
                    name = element.get("name", "").strip().upper()
                    if name and name not in seen_names:
                        characters.append({
                            "name": name,
                            "description": "",
                            "dialogue_count": 1,
                            "first_appearance": scene.get("scene_number"),
                        })
                        seen_names.add(name)

        return ActionResult(
            action_id=context.session_id,
            status=ActionStatus.COMPLETED,
            success=True,
            output={"characters": characters, "count": len(characters)},
            confidence=0.85,
        )

    async def _generate_shot_list(
        self,
        context: ActionContext,
        scene: dict[str, Any],
        style: str = "cinematic",
    ) -> ActionResult:
        """Generate shot breakdown for a scene."""
        from scenemachine.services.shot_list_generator import ShotListGenerator

        try:
            generator = ShotListGenerator()
            shots = await generator.generate_for_scene(
                scene_content=scene.get("raw_content", ""),
                scene_location=scene.get("location", ""),
                scene_type=scene.get("scene_type", "INT"),
                time_of_day=scene.get("time_of_day", "DAY"),
                style=style,
            )

            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.COMPLETED,
                success=True,
                output={"shots": shots, "count": len(shots)},
                confidence=0.8,
            )
        except Exception as e:
            logger.exception(f"Shot list generation failed: {e}")
            return ActionResult(
                action_id=context.session_id,
                status=ActionStatus.FAILED,
                success=False,
                error_message=str(e),
                confidence=0.0,
            )

    async def _detect_contradictions(
        self,
        context: ActionContext,
        characters: list[dict[str, Any]],
    ) -> ActionResult:
        """Detect contradictions in character descriptions."""
        contradictions = []

        # Group descriptions by character
        char_descriptions: dict[str, list[str]] = {}
        for char in characters:
            name = char.get("name", "").upper()
            desc = char.get("description", "")
            if name and desc:
                if name not in char_descriptions:
                    char_descriptions[name] = []
                char_descriptions[name].append(desc)

        # Simple heuristic: flag if descriptions differ significantly
        for name, descriptions in char_descriptions.items():
            if len(descriptions) > 1:
                # Check for obvious contradictions
                for i, d1 in enumerate(descriptions):
                    for d2 in descriptions[i+1:]:
                        # Simple keyword check (would use LLM in production)
                        d1_lower = d1.lower()
                        d2_lower = d2.lower()

                        # Height contradictions
                        if ("tall" in d1_lower and "short" in d2_lower) or \
                           ("short" in d1_lower and "tall" in d2_lower):
                            contradictions.append({
                                "character": name,
                                "type": "physical",
                                "description1": d1,
                                "description2": d2,
                                "issue": "Height contradiction",
                            })

                        # Hair color contradictions
                        hair_colors = ["blonde", "brunette", "redhead", "black", "gray"]
                        for color1 in hair_colors:
                            for color2 in hair_colors:
                                if color1 != color2:
                                    if color1 in d1_lower and color2 in d2_lower:
                                        contradictions.append({
                                            "character": name,
                                            "type": "physical",
                                            "description1": d1,
                                            "description2": d2,
                                            "issue": f"Hair color contradiction ({color1} vs {color2})",
                                        })

        return ActionResult(
            action_id=context.session_id,
            status=ActionStatus.COMPLETED,
            success=True,
            output={
                "contradictions": contradictions,
                "count": len(contradictions),
                "has_issues": len(contradictions) > 0,
            },
            confidence=0.7,  # Heuristic-based, not highly confident
        )
