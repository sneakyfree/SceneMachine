"""Fountain screenplay format parser.

Implements the Fountain markup specification for screenwriting.
See: https://fountain.io/syntax

Fountain is a plain text markup language for screenwriting that allows
writers to focus on content while maintaining proper screenplay formatting.
"""

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ElementType(StrEnum):
    """Types of screenplay elements."""

    TITLE_PAGE = "title_page"
    SCENE_HEADING = "scene_heading"
    ACTION = "action"
    CHARACTER = "character"
    DIALOGUE = "dialogue"
    PARENTHETICAL = "parenthetical"
    TRANSITION = "transition"
    CENTERED = "centered"
    SECTION = "section"
    SYNOPSIS = "synopsis"
    NOTE = "note"
    BONEYARD = "boneyard"
    PAGE_BREAK = "page_break"
    LINE_BREAK = "line_break"
    DUAL_DIALOGUE = "dual_dialogue"


@dataclass
class TitlePage:
    """Parsed title page information."""

    title: str | None = None
    credit: str | None = None
    author: str | None = None
    source: str | None = None
    draft_date: str | None = None
    contact: str | None = None
    copyright: str | None = None
    notes: str | None = None
    revision: str | None = None
    custom: dict[str, str] = field(default_factory=dict)


@dataclass
class SceneHeading:
    """Parsed scene heading information."""

    raw_text: str
    scene_type: str  # INT, EXT, INT./EXT., I/E, etc.
    location: str
    time_of_day: str
    scene_number: str | None = None


@dataclass
class Element:
    """A single screenplay element."""

    type: ElementType
    text: str
    raw_text: str
    line_number: int
    # Additional metadata based on element type
    scene_heading: SceneHeading | None = None
    character_name: str | None = None
    character_extension: str | None = None  # (V.O.), (O.S.), etc.
    is_dual_dialogue: bool = False
    section_depth: int = 0
    scene_number: str | None = None


@dataclass
class ParsedScreenplay:
    """Complete parsed screenplay."""

    title_page: TitlePage
    elements: list[Element]
    characters: list[str]
    scenes: list[dict[str, Any]]
    metadata: dict[str, Any]


class FountainParser:
    """Parser for Fountain screenplay format.

    Implements the full Fountain specification including:
    - Title page parsing
    - Scene headings with INT./EXT. detection
    - Character names and dialogue
    - Parentheticals
    - Transitions
    - Action lines
    - Centered text
    - Section headings
    - Notes and comments
    - Dual dialogue
    - Emphasis (bold, italic, underline)
    """

    # Scene heading patterns
    SCENE_HEADING_PREFIXES = (
        "INT",
        "EXT",
        "EST",
        "INT./EXT",
        "INT/EXT",
        "I/E",
        "INT./EXT.",
        "INT/EXT.",
    )

    # Transition patterns (end with TO:)
    TRANSITION_PATTERN = re.compile(r"^[A-Z\s]+TO:$")

    # Character name pattern (all caps, may have extension)
    CHARACTER_PATTERN = re.compile(
        r"^([A-Z][A-Z0-9\s\-\'\.]+?)(\s*\([^)]+\))?(\s*\^)?$"
    )

    # Parenthetical pattern
    PARENTHETICAL_PATTERN = re.compile(r"^\([^)]+\)$")

    # Scene number pattern #number#
    SCENE_NUMBER_PATTERN = re.compile(r"#([^#]+)#\s*$")

    # Centered text pattern
    CENTERED_PATTERN = re.compile(r"^>\s*(.+?)\s*<$")

    # Section heading pattern
    SECTION_PATTERN = re.compile(r"^(#{1,6})\s*(.+)$")

    # Synopsis pattern
    SYNOPSIS_PATTERN = re.compile(r"^=\s*(.+)$")

    # Note pattern
    NOTE_PATTERN = re.compile(r"\[\[(.+?)\]\]", re.DOTALL)

    # Boneyard (commented out) pattern
    BONEYARD_PATTERN = re.compile(r"/\*.*?\*/", re.DOTALL)

    # Forced element patterns
    FORCED_SCENE_HEADING = re.compile(r"^\.")
    FORCED_ACTION = re.compile(r"^!")
    FORCED_CHARACTER = re.compile(r"^@")
    FORCED_TRANSITION = re.compile(r"^>(?!.*<$)")
    FORCED_LYRICS = re.compile(r"^~")

    # Emphasis patterns
    BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")
    ITALIC_PATTERN = re.compile(r"\*(.+?)\*")
    UNDERLINE_PATTERN = re.compile(r"_(.+?)_")
    BOLD_ITALIC_PATTERN = re.compile(r"\*\*\*(.+?)\*\*\*")

    def __init__(self) -> None:
        """Initialize the parser."""
        self._line_number = 0
        self._lines: list[str] = []
        self._elements: list[Element] = []
        self._characters: set[str] = set()
        self._current_index = 0

    def parse(self, content: str) -> ParsedScreenplay:
        """Parse a Fountain screenplay.

        Args:
            content: Raw Fountain text content

        Returns:
            ParsedScreenplay with all extracted elements
        """
        # Reset state
        self._elements = []
        self._characters = set()
        self._line_number = 0

        # Remove boneyard sections (/* */)
        content = self.BONEYARD_PATTERN.sub("", content)

        # Extract and remove notes (store for later)
        notes: list[tuple[int, str]] = []
        for match in self.NOTE_PATTERN.finditer(content):
            notes.append((match.start(), match.group(1)))
        content = self.NOTE_PATTERN.sub("", content)

        # Normalize line endings
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        # Split into lines
        self._lines = content.split("\n")
        self._current_index = 0

        # Parse title page if present
        title_page = self._parse_title_page()

        # Parse body elements
        self._parse_body()

        # Extract scenes from elements
        scenes = self._extract_scenes()

        # Build metadata
        metadata = {
            "line_count": len(self._lines),
            "element_count": len(self._elements),
            "scene_count": len(scenes),
            "character_count": len(self._characters),
            "has_title_page": title_page.title is not None,
        }

        return ParsedScreenplay(
            title_page=title_page,
            elements=self._elements,
            characters=sorted(self._characters),
            scenes=scenes,
            metadata=metadata,
        )

    def _parse_title_page(self) -> TitlePage:
        """Parse the title page if present.

        Title page elements are key: value pairs at the start of the document,
        ended by a blank line.
        """
        title_page = TitlePage()

        if not self._lines:
            return title_page

        # Check if first line looks like a title page entry
        first_line = self._lines[0].strip()
        if ":" not in first_line:
            return title_page

        # Parse title page entries
        current_key: str | None = None
        current_value: list[str] = []

        while self._current_index < len(self._lines):
            line = self._lines[self._current_index]

            # Blank line ends title page
            if not line.strip():
                # Save last entry
                if current_key:
                    self._set_title_page_value(
                        title_page, current_key, "\n".join(current_value)
                    )
                self._current_index += 1
                break

            # Check for new key: value pair
            if ":" in line and not line.startswith(" ") and not line.startswith("\t"):
                # Save previous entry
                if current_key:
                    self._set_title_page_value(
                        title_page, current_key, "\n".join(current_value)
                    )

                # Parse new entry
                key, _, value = line.partition(":")
                current_key = key.strip().lower()
                current_value = [value.strip()] if value.strip() else []
            else:
                # Continuation of previous value
                if current_key:
                    current_value.append(line.strip())

            self._current_index += 1

        return title_page

    def _set_title_page_value(
        self, title_page: TitlePage, key: str, value: str
    ) -> None:
        """Set a title page value based on key."""
        key_mapping = {
            "title": "title",
            "credit": "credit",
            "author": "author",
            "authors": "author",
            "by": "author",
            "source": "source",
            "draft date": "draft_date",
            "date": "draft_date",
            "contact": "contact",
            "copyright": "copyright",
            "notes": "notes",
            "revision": "revision",
        }

        if key in key_mapping:
            setattr(title_page, key_mapping[key], value)
        else:
            title_page.custom[key] = value

    def _parse_body(self) -> None:
        """Parse the main body of the screenplay."""
        while self._current_index < len(self._lines):
            self._line_number = self._current_index + 1
            line = self._lines[self._current_index]

            # Skip empty lines (but track them for blank line detection)
            if not line.strip():
                self._current_index += 1
                continue

            # Parse the element
            element = self._parse_element(line)
            if element:
                self._elements.append(element)

            self._current_index += 1

    def _parse_element(self, line: str) -> Element | None:
        """Parse a single line into an element."""
        stripped = line.strip()

        # Page break (=== or more)
        if re.match(r"^={3,}$", stripped):
            return Element(
                type=ElementType.PAGE_BREAK,
                text="",
                raw_text=line,
                line_number=self._line_number,
            )

        # Centered text (>text<)
        centered_match = self.CENTERED_PATTERN.match(stripped)
        if centered_match:
            return Element(
                type=ElementType.CENTERED,
                text=self._clean_emphasis(centered_match.group(1)),
                raw_text=line,
                line_number=self._line_number,
            )

        # Section heading (# ## ### etc.)
        section_match = self.SECTION_PATTERN.match(stripped)
        if section_match:
            return Element(
                type=ElementType.SECTION,
                text=section_match.group(2),
                raw_text=line,
                line_number=self._line_number,
                section_depth=len(section_match.group(1)),
            )

        # Synopsis (= text)
        synopsis_match = self.SYNOPSIS_PATTERN.match(stripped)
        if synopsis_match:
            return Element(
                type=ElementType.SYNOPSIS,
                text=synopsis_match.group(1),
                raw_text=line,
                line_number=self._line_number,
            )

        # Forced scene heading (.SCENE)
        if self.FORCED_SCENE_HEADING.match(stripped):
            return self._parse_scene_heading(stripped[1:], line, forced=True)

        # Forced action (!action)
        if self.FORCED_ACTION.match(stripped):
            return Element(
                type=ElementType.ACTION,
                text=self._clean_emphasis(stripped[1:]),
                raw_text=line,
                line_number=self._line_number,
            )

        # Forced character (@CHARACTER)
        if self.FORCED_CHARACTER.match(stripped):
            return self._parse_character(stripped[1:], line, forced=True)

        # Forced transition (>TRANSITION)
        if self.FORCED_TRANSITION.match(stripped):
            return Element(
                type=ElementType.TRANSITION,
                text=stripped[1:].strip(),
                raw_text=line,
                line_number=self._line_number,
            )

        # Scene heading (INT./EXT. etc.)
        if self._is_scene_heading(stripped):
            return self._parse_scene_heading(stripped, line)

        # Transition (ends with TO:)
        if self.TRANSITION_PATTERN.match(stripped):
            return Element(
                type=ElementType.TRANSITION,
                text=stripped,
                raw_text=line,
                line_number=self._line_number,
            )

        # Parenthetical
        if self.PARENTHETICAL_PATTERN.match(stripped):
            return Element(
                type=ElementType.PARENTHETICAL,
                text=stripped[1:-1],  # Remove ( )
                raw_text=line,
                line_number=self._line_number,
            )

        # Character (must check context - preceded by blank line)
        if self._is_character_line(stripped):
            return self._parse_character(stripped, line)

        # Default to action
        return Element(
            type=ElementType.ACTION,
            text=self._clean_emphasis(stripped),
            raw_text=line,
            line_number=self._line_number,
        )

    def _is_scene_heading(self, line: str) -> bool:
        """Check if line is a scene heading."""
        upper = line.upper()
        for prefix in self.SCENE_HEADING_PREFIXES:
            if upper.startswith(prefix):
                # Must be followed by space or period
                rest = upper[len(prefix) :]
                if rest and (rest[0] in " ."):
                    return True
        return False

    def _parse_scene_heading(
        self, text: str, raw_line: str, forced: bool = False
    ) -> Element:
        """Parse a scene heading into its components."""
        # Extract scene number if present
        scene_number = None
        scene_num_match = self.SCENE_NUMBER_PATTERN.search(text)
        if scene_num_match:
            scene_number = scene_num_match.group(1)
            text = self.SCENE_NUMBER_PATTERN.sub("", text).strip()

        # Parse scene type, location, and time
        scene_type = ""
        location = ""
        time_of_day = ""

        upper = text.upper()
        for prefix in self.SCENE_HEADING_PREFIXES:
            if upper.startswith(prefix):
                scene_type = prefix
                rest = text[len(prefix) :].strip()
                if rest.startswith("."):
                    rest = rest[1:].strip()

                # Split by dash for time of day
                if " - " in rest:
                    parts = rest.rsplit(" - ", 1)
                    location = parts[0].strip()
                    time_of_day = parts[1].strip() if len(parts) > 1 else ""
                else:
                    location = rest
                break

        scene_heading = SceneHeading(
            raw_text=text,
            scene_type=scene_type,
            location=location,
            time_of_day=time_of_day,
            scene_number=scene_number,
        )

        return Element(
            type=ElementType.SCENE_HEADING,
            text=text,
            raw_text=raw_line,
            line_number=self._line_number,
            scene_heading=scene_heading,
            scene_number=scene_number,
        )

    def _is_character_line(self, line: str) -> bool:
        """Check if line is a character name.

        Character names must:
        - Be preceded by a blank line
        - Be all uppercase (with some exceptions)
        - Not be a scene heading or transition
        """
        # Must be preceded by blank line
        if self._current_index > 0:
            prev_line = self._lines[self._current_index - 1].strip()
            if prev_line:
                return False

        # Check pattern
        match = self.CHARACTER_PATTERN.match(line)
        if not match:
            return False

        name = match.group(1).strip()

        # Exclude common non-character uppercase lines
        excluded = {"FADE IN:", "FADE OUT:", "CUT TO:", "THE END", "CONTINUED"}
        if name in excluded:
            return False

        # Must have dialogue following
        if self._current_index + 1 < len(self._lines):
            next_line = self._lines[self._current_index + 1].strip()
            # Next line should be dialogue or parenthetical
            if next_line and not self._is_scene_heading(next_line):
                return True

        return False

    def _parse_character(
        self, text: str, raw_line: str, forced: bool = False
    ) -> Element:
        """Parse a character element."""
        match = self.CHARACTER_PATTERN.match(text)

        name = text
        extension = None
        is_dual = False

        if match:
            name = match.group(1).strip()
            if match.group(2):
                extension = match.group(2).strip()[1:-1]  # Remove ( )
            if match.group(3):
                is_dual = True

        # Track character
        self._characters.add(name)

        # Look ahead for dialogue
        element = Element(
            type=ElementType.CHARACTER,
            text=name,
            raw_text=raw_line,
            line_number=self._line_number,
            character_name=name,
            character_extension=extension,
            is_dual_dialogue=is_dual,
        )

        # Parse following dialogue
        self._parse_dialogue(name)

        return element

    def _parse_dialogue(self, character_name: str) -> None:
        """Parse dialogue following a character name."""
        while self._current_index + 1 < len(self._lines):
            self._current_index += 1
            self._line_number = self._current_index + 1
            line = self._lines[self._current_index]
            stripped = line.strip()

            # Empty line ends dialogue
            if not stripped:
                self._current_index -= 1
                break

            # Parenthetical
            if self.PARENTHETICAL_PATTERN.match(stripped):
                self._elements.append(
                    Element(
                        type=ElementType.PARENTHETICAL,
                        text=stripped[1:-1],
                        raw_text=line,
                        line_number=self._line_number,
                    )
                )
            # Check if new character or scene heading
            elif self._is_scene_heading(stripped) or self._is_character_line(stripped):
                self._current_index -= 1
                break
            else:
                # Regular dialogue
                self._elements.append(
                    Element(
                        type=ElementType.DIALOGUE,
                        text=self._clean_emphasis(stripped),
                        raw_text=line,
                        line_number=self._line_number,
                    )
                )

    def _clean_emphasis(self, text: str) -> str:
        """Remove emphasis markers but preserve the text."""
        # Order matters - handle bold italic first
        text = self.BOLD_ITALIC_PATTERN.sub(r"\1", text)
        text = self.BOLD_PATTERN.sub(r"\1", text)
        text = self.ITALIC_PATTERN.sub(r"\1", text)
        text = self.UNDERLINE_PATTERN.sub(r"\1", text)
        return text

    def _extract_scenes(self) -> list[dict[str, Any]]:
        """Extract scene information from parsed elements."""
        scenes: list[dict[str, Any]] = []
        current_scene: dict[str, Any] | None = None
        scene_number = 0

        for element in self._elements:
            if element.type == ElementType.SCENE_HEADING:
                # Save previous scene
                if current_scene:
                    scenes.append(current_scene)

                scene_number += 1
                heading = element.scene_heading

                current_scene = {
                    "number": heading.scene_number or str(scene_number),
                    "sequence": scene_number,
                    "type": heading.scene_type if heading else "",
                    "location": heading.location if heading else "",
                    "time_of_day": heading.time_of_day if heading else "",
                    "heading": element.text,
                    "line_number": element.line_number,
                    "elements": [],
                    "characters": set(),
                    "dialogue_count": 0,
                    "action_lines": [],
                }
            elif current_scene:
                current_scene["elements"].append(
                    {
                        "type": element.type.value,
                        "text": element.text,
                        "line_number": element.line_number,
                    }
                )

                if element.type == ElementType.CHARACTER:
                    current_scene["characters"].add(element.character_name)
                elif element.type == ElementType.DIALOGUE:
                    current_scene["dialogue_count"] += 1
                elif element.type == ElementType.ACTION:
                    current_scene["action_lines"].append(element.text)

        # Don't forget the last scene
        if current_scene:
            scenes.append(current_scene)

        # Convert character sets to lists for JSON serialization
        for scene in scenes:
            scene["characters"] = sorted(scene["characters"])

        return scenes


def parse_fountain(content: str) -> dict[str, Any]:
    """Convenience function to parse Fountain content.

    Args:
        content: Raw Fountain text

    Returns:
        Dictionary with parsed screenplay data
    """
    parser = FountainParser()
    result = parser.parse(content)

    return {
        "title_page": {
            "title": result.title_page.title,
            "author": result.title_page.author,
            "credit": result.title_page.credit,
            "source": result.title_page.source,
            "draft_date": result.title_page.draft_date,
            "contact": result.title_page.contact,
            "copyright": result.title_page.copyright,
            "notes": result.title_page.notes,
            "custom": result.title_page.custom,
        },
        "elements": [
            {
                "type": e.type.value,
                "text": e.text,
                "line_number": e.line_number,
                "character_name": e.character_name,
                "character_extension": e.character_extension,
                "scene_number": e.scene_number,
            }
            for e in result.elements
        ],
        "characters": result.characters,
        "scenes": result.scenes,
        "metadata": result.metadata,
    }
