"""Screenplay service for parsing and managing screenplay documents."""

import logging
from pathlib import Path
from typing import Any, BinaryIO
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models import Character, Project, Scene, Screenplay, ScreenplayFormat
from scenemachine.models.scene import SceneState, SceneType, TimeOfDay
from scenemachine.parsers.fountain import parse_fountain
from scenemachine.parsers.pdf import parse_pdf
from scenemachine.services.storage import get_storage_service

logger = logging.getLogger(__name__)


class ScreenplayService:
    """Service for screenplay parsing and management.

    Handles:
    - File format detection
    - Screenplay parsing (Fountain, PDF, FDX)
    - Character extraction
    - Scene extraction
    - Database persistence
    """

    SUPPORTED_FORMATS = {
        ".fountain": ScreenplayFormat.FOUNTAIN,
        ".spmd": ScreenplayFormat.FOUNTAIN,  # Alternative extension
        ".pdf": ScreenplayFormat.PDF,
        ".fdx": ScreenplayFormat.FDX,
        ".txt": ScreenplayFormat.PLAIN_TEXT,
    }

    def __init__(self, session: AsyncSession) -> None:
        """Initialize screenplay service.

        Args:
            session: Database session
        """
        self.session = session
        self.storage = get_storage_service()

    async def upload_screenplay(
        self,
        project_id: UUID,
        file: BinaryIO,
        filename: str,
    ) -> Screenplay:
        """Upload and store a screenplay file.

        Args:
            project_id: Project UUID
            file: File object
            filename: Original filename

        Returns:
            Created Screenplay record

        Raises:
            ValueError: If format not supported or project not found
        """
        # Verify project exists
        project = await self._get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Check if project already has a screenplay. Use an explicit query
        # rather than ``project.screenplay``: the relationship is lazy by
        # default and async lazy loads raise ``MissingGreenlet`` when the
        # session was opened from an IPC handler (no greenlet context).
        existing_q = await self.session.execute(
            select(Screenplay).where(Screenplay.project_id == project_id)
        )
        if existing_q.scalar_one_or_none() is not None:
            raise ValueError("Project already has a screenplay. Delete it first.")

        # Detect format
        suffix = Path(filename).suffix.lower()
        if suffix not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format: {suffix}. "
                f"Supported: {', '.join(self.SUPPORTED_FORMATS.keys())}"
            )

        screenplay_format = self.SUPPORTED_FORMATS[suffix]

        # Save file
        file_path, file_hash = await self.storage.save_screenplay(project_id, file, filename)

        # Create screenplay record
        screenplay = Screenplay(
            project_id=project_id,
            original_filename=filename,
            original_format=screenplay_format,
            file_hash=file_hash,
            original_file_path=str(file_path),
            is_parsed=False,
        )

        self.session.add(screenplay)
        await self.session.commit()
        await self.session.refresh(screenplay)

        return screenplay

    async def parse_screenplay(self, screenplay_id: UUID) -> Screenplay:
        """Parse an uploaded screenplay.

        Args:
            screenplay_id: Screenplay UUID

        Returns:
            Updated Screenplay with parsed content

        Raises:
            ValueError: If screenplay not found
        """
        screenplay = await self._get_screenplay(screenplay_id)
        if not screenplay:
            raise ValueError(f"Screenplay {screenplay_id} not found")

        # Read file content
        file_path = Path(screenplay.original_file_path)
        if not file_path.exists():
            raise ValueError(f"Screenplay file not found: {file_path}")

        # Parse based on format
        try:
            if screenplay.original_format == ScreenplayFormat.FOUNTAIN:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                parsed = parse_fountain(content)

            elif screenplay.original_format == ScreenplayFormat.PDF:
                parsed = parse_pdf(file_path)

            elif screenplay.original_format == ScreenplayFormat.FDX:
                # FDX parsing (Final Draft XML)
                parsed = await self._parse_fdx(file_path)

            else:
                # Plain text - attempt as Fountain
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                parsed = parse_fountain(content)

            # Store parsed content
            screenplay.parsed_content = parsed
            screenplay.is_parsed = True
            screenplay.parse_errors = None

            # Extract and create characters
            await self._create_characters_from_parsed(screenplay)

            # Extract and create scenes
            await self._create_scenes_from_parsed(screenplay)

            await self.session.commit()
            await self.session.refresh(screenplay)

            logger.info(
                f"Parsed screenplay {screenplay_id}: "
                f"{len(parsed.get('characters', []))} characters, "
                f"{len(parsed.get('scenes', []))} scenes"
            )

        except Exception as e:
            logger.exception(f"Failed to parse screenplay {screenplay_id}: {e}")
            screenplay.is_parsed = False
            screenplay.parse_errors = [str(e)]
            await self.session.commit()
            raise ValueError(f"Failed to parse screenplay: {e}") from e

        return screenplay

    async def _parse_fdx(self, file_path: Path) -> dict[str, Any]:
        """Parse Final Draft XML format.

        Args:
            file_path: Path to FDX file

        Returns:
            Parsed screenplay dictionary
        """
        import xml.etree.ElementTree as ET

        tree = ET.parse(file_path)
        root = tree.getroot()

        elements: list[dict[str, Any]] = []
        characters: set[str] = set()
        scenes: list[dict[str, Any]] = []
        current_scene: dict[str, Any] | None = None
        scene_count = 0

        # Find content element
        content = root.find(".//Content")
        if content is None:
            return {"elements": [], "characters": [], "scenes": [], "metadata": {}}

        for paragraph in content.findall(".//Paragraph"):
            para_type = paragraph.get("Type", "Action")
            text_elem = paragraph.find("Text")
            text = text_elem.text if text_elem is not None else ""

            if not text:
                continue

            element_type = self._fdx_type_to_element(para_type)

            elements.append(
                {
                    "type": element_type,
                    "text": text,
                    "line_number": len(elements) + 1,
                }
            )

            if element_type == "scene_heading":
                if current_scene:
                    scenes.append(current_scene)

                scene_count += 1
                scene_info = self._parse_scene_heading_text(text)
                current_scene = {
                    "number": str(scene_count),
                    "sequence": scene_count,
                    "type": scene_info.get("type", ""),
                    "location": scene_info.get("location", ""),
                    "time_of_day": scene_info.get("time_of_day", ""),
                    "heading": text,
                    "line_number": len(elements),
                    "elements": [],
                    "characters": [],
                    "dialogue_count": 0,
                    "action_lines": [],
                }

            elif element_type == "character":
                char_name = text.split("(")[0].strip()
                characters.add(char_name)
                if current_scene and char_name not in current_scene["characters"]:
                    current_scene["characters"].append(char_name)

            elif element_type == "dialogue" and current_scene:
                current_scene["dialogue_count"] += 1

            elif element_type == "action" and current_scene:
                current_scene["action_lines"].append(text)

        if current_scene:
            scenes.append(current_scene)

        return {
            "elements": elements,
            "characters": sorted(characters),
            "scenes": scenes,
            "metadata": {
                "element_count": len(elements),
                "scene_count": len(scenes),
                "character_count": len(characters),
            },
        }

    def _fdx_type_to_element(self, fdx_type: str) -> str:
        """Convert FDX paragraph type to element type."""
        mapping = {
            "Scene Heading": "scene_heading",
            "Action": "action",
            "Character": "character",
            "Dialogue": "dialogue",
            "Parenthetical": "parenthetical",
            "Transition": "transition",
            "Shot": "action",
            "General": "action",
        }
        return mapping.get(fdx_type, "action")

    def _parse_scene_heading_text(self, text: str) -> dict[str, str]:
        """Parse scene heading text into components."""
        import re

        result = {"type": "", "location": "", "time_of_day": ""}

        match = re.match(
            r"^\s*(INT\.?|EXT\.?|INT\.?/EXT\.?|I/E\.?)\s*\.?\s*",
            text,
            re.IGNORECASE,
        )

        if match:
            result["type"] = match.group(1).upper().rstrip(".")
            rest = text[match.end() :].strip()

            if " - " in rest:
                parts = rest.rsplit(" - ", 1)
                result["location"] = parts[0].strip()
                result["time_of_day"] = parts[1].strip() if len(parts) > 1 else ""
            else:
                result["location"] = rest

        return result

    async def _create_characters_from_parsed(self, screenplay: Screenplay) -> None:
        """Create Character records from parsed screenplay."""
        if not screenplay.parsed_content:
            return

        character_names = screenplay.parsed_content.get("characters", [])
        elements = screenplay.parsed_content.get("elements", [])

        # Count dialogue per character
        dialogue_counts: dict[str, int] = {}
        current_character: str | None = None

        for elem in elements:
            if elem.get("type") == "character":
                current_character = elem.get("name") or elem.get("text", "").split("(")[0].strip()
            elif elem.get("type") == "dialogue" and current_character:
                dialogue_counts[current_character] = dialogue_counts.get(current_character, 0) + 1

        # Count scenes per character
        scene_counts: dict[str, int] = {}
        for scene in screenplay.parsed_content.get("scenes", []):
            for char in scene.get("characters", []):
                scene_counts[char] = scene_counts.get(char, 0) + 1

        # Create character records
        for name in character_names:
            character = Character(
                project_id=screenplay.project_id,
                name=name,
                screenplay_name=name,
                scene_count=scene_counts.get(name, 0),
                dialogue_count=dialogue_counts.get(name, 0),
            )
            self.session.add(character)

    async def _create_scenes_from_parsed(self, screenplay: Screenplay) -> None:
        """Create Scene records from parsed screenplay."""
        if not screenplay.parsed_content:
            return

        scenes_data = screenplay.parsed_content.get("scenes", [])

        for scene_data in scenes_data:
            # Map scene type
            scene_type_str = scene_data.get("type", "").upper()
            if "INT" in scene_type_str and "EXT" in scene_type_str:
                scene_type = SceneType.INTERIOR_EXTERIOR
            elif "EXT" in scene_type_str:
                scene_type = SceneType.EXTERIOR
            else:
                scene_type = SceneType.INTERIOR

            # Map time of day
            time_str = scene_data.get("time_of_day", "").upper()
            time_mapping = {
                "DAY": TimeOfDay.DAY,
                "NIGHT": TimeOfDay.NIGHT,
                "DAWN": TimeOfDay.DAWN,
                "DUSK": TimeOfDay.DUSK,
                "MORNING": TimeOfDay.MORNING,
                "AFTERNOON": TimeOfDay.AFTERNOON,
                "EVENING": TimeOfDay.EVENING,
                "CONTINUOUS": TimeOfDay.CONTINUOUS,
                "LATER": TimeOfDay.LATER,
                "SAME": TimeOfDay.SAME,
            }
            time_of_day = time_mapping.get(time_str, TimeOfDay.DAY)

            # Build raw content from elements
            raw_content = scene_data.get("heading", "") + "\n\n"
            for elem in scene_data.get("elements", []):
                raw_content += elem.get("text", "") + "\n"

            scene = Scene(
                project_id=screenplay.project_id,
                scene_number=scene_data.get("number", ""),
                sequence_number=scene_data.get("sequence", 0),
                scene_type=scene_type,
                location=scene_data.get("location", ""),
                time_of_day=time_of_day,
                raw_content=raw_content.strip(),
                action_lines=scene_data.get("action_lines", []),
                character_ids=[],  # Will be populated later with actual UUIDs
                state=SceneState.PARSED,
            )
            self.session.add(scene)

    async def delete_screenplay(self, screenplay_id: UUID) -> bool:
        """Delete a screenplay and its parsed data.

        Args:
            screenplay_id: Screenplay UUID

        Returns:
            True if deleted
        """
        screenplay = await self._get_screenplay(screenplay_id)
        if not screenplay:
            return False

        # Delete associated characters and scenes
        # (handled by cascade, but explicit for clarity)
        await self.session.delete(screenplay)
        await self.session.commit()

        return True

    async def _get_project(self, project_id: UUID) -> Project | None:
        """Get project by ID."""
        stmt = select(Project).where(Project.id == project_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_screenplay(self, screenplay_id: UUID) -> Screenplay | None:
        """Get screenplay by ID."""
        stmt = select(Screenplay).where(Screenplay.id == screenplay_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


async def get_screenplay_service(session: AsyncSession) -> ScreenplayService:
    """Factory function for ScreenplayService."""
    return ScreenplayService(session)
