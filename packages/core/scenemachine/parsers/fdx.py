"""Final Draft (.fdx) screenplay parser.

Parses Final Draft XML format screenplays into structured format.
Final Draft is the industry-standard screenwriting software.
"""

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FDXParagraph:
    """A paragraph element from FDX."""
    
    element_type: str
    text: str
    scene_number: Optional[str] = None
    character_name: Optional[str] = None
    dual_dialogue: bool = False


@dataclass
class FDXScene:
    """A parsed scene from FDX."""
    
    scene_number: str
    scene_type: str  # INT, EXT, INT/EXT
    location: str
    time_of_day: str
    elements: List[FDXParagraph] = field(default_factory=list)


@dataclass
class FDXParseResult:
    """Result of parsing an FDX file."""
    
    title: Optional[str] = None
    author: Optional[str] = None
    copyright: Optional[str] = None
    contact: Optional[str] = None
    draft_date: Optional[str] = None
    revision: Optional[str] = None
    
    scenes: List[FDXScene] = field(default_factory=list)
    characters: List[str] = field(default_factory=list)
    elements: List[FDXParagraph] = field(default_factory=list)
    
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FDXParser:
    """Parser for Final Draft (.fdx) screenplay files.
    
    Final Draft files are XML-based with a specific schema for
    representing screenplay elements. This parser extracts:
    - Title page information
    - Scene headings with INT/EXT detection
    - Character names and dialogue
    - Action descriptions
    - Transitions
    """
    
    # Element type mappings from FDX to our internal types
    ELEMENT_TYPES = {
        "Scene Heading": "scene_heading",
        "Action": "action",
        "Character": "character",
        "Dialogue": "dialogue",
        "Parenthetical": "parenthetical",
        "Transition": "transition",
        "Shot": "shot",
        "General": "general",
        "Cast List": "cast_list",
    }
    
    # Scene heading pattern
    SCENE_HEADING_PATTERN = re.compile(
        r"^(INT|EXT|INT\./EXT\.|INT/EXT|I/E)\.?\s+(.+?)(?:\s*[-–—]\s*(.+))?$",
        re.IGNORECASE
    )
    
    def __init__(self):
        """Initialize the FDX parser."""
        self._characters: set = set()
        self._current_scene: Optional[FDXScene] = None
        self._scenes: List[FDXScene] = []
        self._elements: List[FDXParagraph] = []
    
    def parse(self, file_path: Path | str) -> Dict[str, Any]:
        """Parse a Final Draft file.
        
        Args:
            file_path: Path to the .fdx file
            
        Returns:
            Dictionary with parsed screenplay data
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"FDX file not found: {file_path}")
        
        if file_path.suffix.lower() != ".fdx":
            raise ValueError(f"Expected .fdx file, got: {file_path.suffix}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return self.parse_content(content)
    
    def parse_bytes(self, data: bytes, filename: str = "screenplay.fdx") -> Dict[str, Any]:
        """Parse FDX from bytes.
        
        Args:
            data: FDX file bytes
            filename: Optional filename for context
            
        Returns:
            Dictionary with parsed screenplay data
        """
        # Try UTF-8 first, then fallback to other encodings
        encodings = ["utf-8", "utf-16", "latin-1", "cp1252"]
        content = None
        
        for encoding in encodings:
            try:
                content = data.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            raise ValueError("Could not decode FDX file with any supported encoding")
        
        return self.parse_content(content, filename)
    
    def parse_content(self, content: str, filename: str = "screenplay.fdx") -> Dict[str, Any]:
        """Parse FDX XML content.
        
        Args:
            content: FDX XML content
            filename: Optional filename for context
            
        Returns:
            Dictionary with parsed screenplay data
        """
        # Reset state
        self._characters = set()
        self._current_scene = None
        self._scenes = []
        self._elements = []
        
        result = FDXParseResult()
        
        try:
            # Parse XML
            root = ET.fromstring(content)
            
            # Extract metadata
            self._parse_title_page(root, result)
            
            # Extract content paragraphs
            self._parse_content(root, result)
            
            # Finalize current scene
            if self._current_scene:
                self._scenes.append(self._current_scene)
            
            result.scenes = self._scenes
            result.characters = sorted(list(self._characters))
            result.elements = self._elements
            
        except ET.ParseError as e:
            logger.error(f"XML parse error in {filename}: {e}")
            result.warnings.append(f"XML parse error: {e}")
        
        return self._to_dict(result)
    
    def _parse_title_page(self, root: ET.Element, result: FDXParseResult) -> None:
        """Extract title page information."""
        # Look for TitlePage element
        title_page = root.find(".//TitlePage")
        
        if title_page is None:
            return
        
        # Extract title page paragraphs
        for para in title_page.findall(".//Paragraph"):
            para_type = para.get("Type", "").lower()
            text = self._get_paragraph_text(para)
            
            if not text:
                continue
            
            if "title" in para_type:
                result.title = text
            elif "written by" in para_type or "author" in para_type:
                result.author = text
            elif "copyright" in para_type:
                result.copyright = text
            elif "contact" in para_type or "address" in para_type:
                result.contact = text
            elif "draft" in para_type or "date" in para_type:
                result.draft_date = text
            elif "revision" in para_type:
                result.revision = text
    
    def _parse_content(self, root: ET.Element, result: FDXParseResult) -> None:
        """Parse the main screenplay content."""
        # Find Content element
        content = root.find(".//Content")
        
        if content is None:
            result.warnings.append("No Content element found in FDX")
            return
        
        # Process each paragraph
        for para in content.findall(".//Paragraph"):
            self._process_paragraph(para, result)
    
    def _process_paragraph(self, para: ET.Element, result: FDXParseResult) -> None:
        """Process a single paragraph element."""
        para_type = para.get("Type", "General")
        text = self._get_paragraph_text(para)
        
        if not text.strip():
            return
        
        # Create paragraph object
        fdx_para = FDXParagraph(
            element_type=self.ELEMENT_TYPES.get(para_type, para_type.lower()),
            text=text.strip(),
        )
        
        # Handle scene headings
        if para_type == "Scene Heading":
            self._handle_scene_heading(fdx_para, para)
        
        # Handle character names
        elif para_type == "Character":
            char_name = self._extract_character_name(text)
            if char_name:
                self._characters.add(char_name)
                fdx_para.character_name = char_name
        
        # Check for dual dialogue
        if para.get("DualDialogue") == "Start" or para.get("DualDialogue") == "True":
            fdx_para.dual_dialogue = True
        
        # Add to current scene if available
        if self._current_scene:
            self._current_scene.elements.append(fdx_para)
        
        self._elements.append(fdx_para)
    
    def _handle_scene_heading(self, fdx_para: FDXParagraph, para: ET.Element) -> None:
        """Handle a scene heading paragraph."""
        # Save current scene
        if self._current_scene:
            self._scenes.append(self._current_scene)
        
        # Parse scene heading
        text = fdx_para.text
        match = self.SCENE_HEADING_PATTERN.match(text)
        
        scene_number = para.get("Number", str(len(self._scenes) + 1))
        
        if match:
            scene_type = match.group(1).upper()
            location = match.group(2).strip()
            time_of_day = match.group(3).strip() if match.group(3) else ""
            
            # Normalize scene type
            if scene_type in ("I/E", "INT./EXT."):
                scene_type = "INT/EXT"
        else:
            # Fallback parsing
            scene_type = "INT" if "INT" in text.upper() else "EXT"
            location = text
            time_of_day = ""
        
        self._current_scene = FDXScene(
            scene_number=scene_number,
            scene_type=scene_type,
            location=location,
            time_of_day=time_of_day,
        )
        
        fdx_para.scene_number = scene_number
    
    def _get_paragraph_text(self, para: ET.Element) -> str:
        """Extract text from a paragraph element."""
        texts = []
        
        # Get text from Text elements
        for text_elem in para.findall(".//Text"):
            if text_elem.text:
                texts.append(text_elem.text)
        
        # If no Text elements, try direct text
        if not texts and para.text:
            texts.append(para.text)
        
        return " ".join(texts)
    
    def _extract_character_name(self, text: str) -> Optional[str]:
        """Extract character name from character cue."""
        # Remove parentheticals like (V.O.), (O.S.), (CONT'D)
        name = re.sub(r"\s*\([^)]+\)\s*", "", text).strip()
        
        # Character names are typically uppercase
        if name.isupper():
            return name
        
        return name.upper() if name else None
    
    def _to_dict(self, result: FDXParseResult) -> Dict[str, Any]:
        """Convert parse result to dictionary."""
        return {
            "title": result.title,
            "author": result.author,
            "copyright": result.copyright,
            "contact": result.contact,
            "draft_date": result.draft_date,
            "revision": result.revision,
            "scenes": [
                {
                    "scene_number": scene.scene_number,
                    "scene_type": scene.scene_type,
                    "location": scene.location,
                    "time_of_day": scene.time_of_day,
                    "slug": f"{scene.scene_type}. {scene.location}"
                             + (f" - {scene.time_of_day}" if scene.time_of_day else ""),
                    "elements": [
                        {
                            "type": elem.element_type,
                            "text": elem.text,
                            "character_name": elem.character_name,
                            "dual_dialogue": elem.dual_dialogue,
                        }
                        for elem in scene.elements
                    ],
                }
                for scene in result.scenes
            ],
            "characters": result.characters,
            "elements": [
                {
                    "type": elem.element_type,
                    "text": elem.text,
                    "character_name": elem.character_name,
                    "scene_number": elem.scene_number,
                }
                for elem in result.elements
            ],
            "warnings": result.warnings,
            "metadata": {
                "format": "fdx",
                "scene_count": len(result.scenes),
                "character_count": len(result.characters),
                "element_count": len(result.elements),
            },
        }


def parse_fdx(file_path: Path | str) -> Dict[str, Any]:
    """Convenience function to parse an FDX screenplay.
    
    Args:
        file_path: Path to FDX file
        
    Returns:
        Dictionary with parsed screenplay data
    """
    parser = FDXParser()
    return parser.parse(file_path)
