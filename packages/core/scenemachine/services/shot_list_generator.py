"""LLM-powered shot list generator.

Generates detailed shot breakdowns from parsed screenplays using LLM analysis.
Implements the DNA strand master plan's "Scenario Universe Builder" concept.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

logger = logging.getLogger(__name__)


class CameraAngle(str, Enum):
    """Camera angle/shot type options."""
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE = "extreme_close"
    AERIAL = "aerial"
    POV = "pov"
    OVER_SHOULDER = "over_shoulder"
    TWO_SHOT = "two_shot"
    GROUP = "group"


class CameraMovement(str, Enum):
    """Camera movement types."""
    STATIC = "static"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    DOLLY_IN = "dolly_in"
    DOLLY_OUT = "dolly_out"
    TRACKING = "tracking"
    CRANE = "crane"
    HANDHELD = "handheld"
    ZOOM = "zoom"


class ShotConfidence(str, Enum):
    """Confidence level for generated shots."""
    HIGH = "high"      # >= 0.8
    MEDIUM = "medium"  # >= 0.6
    LOW = "low"        # < 0.6


@dataclass
class DialogueLine:
    """Dialogue line within a shot."""
    character: str
    text: str
    emotion: str = "neutral"
    parenthetical: Optional[str] = None


@dataclass
class GeneratedShot:
    """A generated shot from screenplay analysis."""
    shot_id: str
    visual_prompt: str
    negative_prompt: str = "blurry, low quality, distorted, artifacts"
    camera_angle: CameraAngle = CameraAngle.MEDIUM
    camera_movement: CameraMovement = CameraMovement.STATIC
    characters_in_frame: List[str] = field(default_factory=list)
    dialogue: Optional[DialogueLine] = None
    duration_estimate_seconds: float = 5.0
    confidence: float = 0.7
    unknowns: List[str] = field(default_factory=list)
    source: str = "generated"  # "parsed", "inferred", "user_edited"
    notes: str = ""


@dataclass
class SceneBreakdown:
    """Complete breakdown of a scene into shots."""
    scene_id: str
    scene_number: str
    slug: str
    location: str
    time_of_day: str
    int_ext: str
    description: str
    shots: List[GeneratedShot] = field(default_factory=list)
    characters_present: List[str] = field(default_factory=list)
    estimated_duration_seconds: float = 0.0


@dataclass 
class Contradiction:
    """A detected contradiction in the screenplay."""
    contradiction_id: str
    type: str  # "character_description", "timeline", "location", "prop"
    description: str
    locations: List[Dict[str, Any]]  # Where in script it appears
    severity: str  # "critical", "warning", "info"
    suggested_resolution: Optional[str] = None


@dataclass
class ShotListResult:
    """Result of shot list generation."""
    title: Optional[str]
    scenes: List[SceneBreakdown]
    characters: List[Dict[str, Any]]
    contradictions: List[Contradiction]
    total_shots: int
    estimated_duration_seconds: float
    parse_confidence: float
    warnings: List[str] = field(default_factory=list)


class ShotListGenerator:
    """Generates shot lists from parsed screenplays.
    
    This implements the DNA strand master plan's requirements:
    - Exhaustive shot planning within configured sources
    - Labels unknowns honestly
    - Never invents terms/pricing/eligibility
    - Contradiction detection
    """
    
    # Camera angle inference patterns
    CLOSE_UP_KEYWORDS = [
        "close on", "closeup", "close-up", "insert", "detail",
        "eyes", "face", "hands", "mouth", "tears"
    ]
    
    WIDE_KEYWORDS = [
        "wide", "establishing", "master", "aerial", "panoramic",
        "full shot", "enter", "exit", "entire room"
    ]
    
    POV_KEYWORDS = [
        "pov", "point of view", "through the eyes", "subjective"
    ]
    
    # Emotion inference from parentheticals
    EMOTION_MAP = {
        "angry": ["angry", "furious", "enraged", "shouting", "yelling"],
        "sad": ["sad", "crying", "tearful", "sobbing", "melancholy"],
        "happy": ["happy", "laughing", "joyful", "excited", "smiling"],
        "scared": ["scared", "frightened", "terrified", "nervous", "anxious"],
        "surprised": ["surprised", "shocked", "stunned", "astonished"],
        "whisper": ["whisper", "quiet", "sotto voce", "under breath"],
    }
    
    def __init__(self):
        """Initialize the shot list generator."""
        self._character_descriptions: Dict[str, List[str]] = {}
        self._character_appearances: Dict[str, List[str]] = {}
    
    def generate(self, parsed_screenplay: Dict[str, Any]) -> Dict[str, Any]:
        """Generate shot list from parsed screenplay.
        
        Args:
            parsed_screenplay: Output from FountainParser, PDFParser, or FDXParser
            
        Returns:
            Complete shot list with scenes, shots, and metadata
        """
        # Reset state
        self._character_descriptions = {}
        self._character_appearances = {}
        
        # Extract title
        title = parsed_screenplay.get("title") or parsed_screenplay.get("title_page", {}).get("title")
        
        # Process scenes
        scenes = []
        raw_scenes = parsed_screenplay.get("scenes", [])
        
        for idx, scene_data in enumerate(raw_scenes):
            scene_breakdown = self._process_scene(scene_data, idx + 1)
            scenes.append(scene_breakdown)
        
        # Extract character list with metadata
        characters = self._build_character_list(parsed_screenplay)
        
        # Detect contradictions
        contradictions = self._detect_contradictions(parsed_screenplay, scenes)
        
        # Calculate totals
        total_shots = sum(len(scene.shots) for scene in scenes)
        total_duration = sum(scene.estimated_duration_seconds for scene in scenes)
        
        # Calculate overall confidence
        if total_shots > 0:
            avg_confidence = sum(
                shot.confidence 
                for scene in scenes 
                for shot in scene.shots
            ) / total_shots
        else:
            avg_confidence = 0.0
        
        result = ShotListResult(
            title=title,
            scenes=scenes,
            characters=characters,
            contradictions=contradictions,
            total_shots=total_shots,
            estimated_duration_seconds=total_duration,
            parse_confidence=avg_confidence,
        )
        
        return self._to_dict(result)
    
    def _process_scene(self, scene_data: Dict[str, Any], scene_index: int) -> SceneBreakdown:
        """Process a single scene into a shot breakdown."""
        scene_number = scene_data.get("scene_number", str(scene_index))
        scene_id = f"scene_{scene_number.zfill(3)}"
        
        # Parse slug
        slug = scene_data.get("slug", "")
        location = scene_data.get("location", "")
        time_of_day = scene_data.get("time_of_day", "")
        int_ext = scene_data.get("scene_type", "INT")
        
        # Collect scene elements
        elements = scene_data.get("elements", [])
        
        # Extract description (action elements)
        descriptions = []
        for elem in elements:
            if elem.get("type") in ("action", "Action"):
                descriptions.append(elem.get("text", ""))
        description = " ".join(descriptions)
        
        # Generate shots from scene
        shots = self._generate_shots(scene_id, elements)
        
        # Get characters present
        characters_present = list(set(
            elem.get("character_name") or elem.get("character", "")
            for elem in elements
            if elem.get("type") in ("character", "Character", "dialogue", "Dialogue")
            and (elem.get("character_name") or elem.get("character"))
        ))
        
        # Track character appearances
        for char in characters_present:
            if char not in self._character_appearances:
                self._character_appearances[char] = []
            self._character_appearances[char].append(scene_number)
        
        # Calculate duration
        scene_duration = sum(shot.duration_estimate_seconds for shot in shots)
        
        return SceneBreakdown(
            scene_id=scene_id,
            scene_number=scene_number,
            slug=slug,
            location=location,
            time_of_day=time_of_day,
            int_ext=int_ext,
            description=description[:500] if description else "",
            shots=shots,
            characters_present=characters_present,
            estimated_duration_seconds=scene_duration,
        )
    
    def _generate_shots(self, scene_id: str, elements: List[Dict[str, Any]]) -> List[GeneratedShot]:
        """Generate shots from scene elements."""
        shots = []
        shot_index = 1
        current_action = []
        current_dialogue = None
        
        for elem in elements:
            elem_type = elem.get("type", "").lower()
            text = elem.get("text", "")
            
            if elem_type in ("action", "general"):
                # Accumulate action text
                current_action.append(text)
                
                # Check for natural breakpoints
                if self._is_shot_break(text):
                    if current_action:
                        shot = self._create_action_shot(
                            scene_id, shot_index, " ".join(current_action)
                        )
                        shots.append(shot)
                        shot_index += 1
                        current_action = []
            
            elif elem_type == "character":
                # Start tracking dialogue
                char_name = elem.get("character_name") or text.strip()
                current_dialogue = {"character": char_name, "text": "", "parenthetical": None}
            
            elif elem_type == "parenthetical" and current_dialogue:
                current_dialogue["parenthetical"] = text
            
            elif elem_type == "dialogue" and current_dialogue:
                current_dialogue["text"] = text
                
                # Create shot for dialogue
                shot = self._create_dialogue_shot(
                    scene_id, shot_index, current_dialogue, current_action
                )
                shots.append(shot)
                shot_index += 1
                current_action = []
                current_dialogue = None
        
        # Handle remaining action
        if current_action:
            shot = self._create_action_shot(
                scene_id, shot_index, " ".join(current_action)
            )
            shots.append(shot)
        
        # Ensure at least one shot per scene
        if not shots:
            shots.append(GeneratedShot(
                shot_id=f"{scene_id}_001",
                visual_prompt="Empty scene - add description",
                confidence=0.3,
                unknowns=["No content to generate shot from"],
                source="inferred",
            ))
        
        return shots
    
    def _create_action_shot(
        self, scene_id: str, shot_index: int, action_text: str
    ) -> GeneratedShot:
        """Create a shot from action description."""
        shot_id = f"{scene_id}_{str(shot_index).zfill(3)}"
        
        # Infer camera angle
        camera_angle = self._infer_camera_angle(action_text)
        
        # Infer camera movement
        camera_movement = self._infer_camera_movement(action_text)
        
        # Extract characters mentioned
        characters = self._extract_characters_from_text(action_text)
        
        # Build visual prompt
        visual_prompt = self._build_visual_prompt(action_text, characters)
        
        # Calculate confidence
        confidence = self._calculate_confidence(action_text, characters)
        
        # Identify unknowns
        unknowns = self._identify_unknowns(action_text)
        
        # Estimate duration
        duration = self._estimate_duration(action_text)
        
        return GeneratedShot(
            shot_id=shot_id,
            visual_prompt=visual_prompt,
            camera_angle=camera_angle,
            camera_movement=camera_movement,
            characters_in_frame=characters,
            duration_estimate_seconds=duration,
            confidence=confidence,
            unknowns=unknowns,
            source="parsed",
        )
    
    def _create_dialogue_shot(
        self, 
        scene_id: str, 
        shot_index: int, 
        dialogue_info: Dict[str, Any],
        preceding_action: List[str]
    ) -> GeneratedShot:
        """Create a shot for dialogue."""
        shot_id = f"{scene_id}_{str(shot_index).zfill(3)}"
        
        character = dialogue_info["character"]
        dialogue_text = dialogue_info["text"]
        parenthetical = dialogue_info.get("parenthetical", "")
        
        # Infer emotion
        emotion = self._infer_emotion(parenthetical, dialogue_text)
        
        # Create dialogue line
        dialogue = DialogueLine(
            character=character,
            text=dialogue_text,
            emotion=emotion,
            parenthetical=parenthetical,
        )
        
        # Build context from preceding action
        context = " ".join(preceding_action) if preceding_action else ""
        
        # Infer camera angle for dialogue
        camera_angle = self._infer_dialogue_camera_angle(dialogue_text, context)
        
        # Build visual prompt
        visual_prompt = self._build_dialogue_visual_prompt(
            character, dialogue_text, emotion, context
        )
        
        # Estimate duration based on dialogue length
        word_count = len(dialogue_text.split())
        duration = max(3.0, word_count * 0.4)  # ~2.5 words per second
        
        # Calculate confidence
        confidence = 0.8  # Dialogue shots are generally more predictable
        
        return GeneratedShot(
            shot_id=shot_id,
            visual_prompt=visual_prompt,
            camera_angle=camera_angle,
            camera_movement=CameraMovement.STATIC,
            characters_in_frame=[character],
            dialogue=dialogue,
            duration_estimate_seconds=duration,
            confidence=confidence,
            source="parsed",
        )
    
    def _infer_camera_angle(self, text: str) -> CameraAngle:
        """Infer appropriate camera angle from text."""
        text_lower = text.lower()
        
        # Check for explicit mentions
        if any(kw in text_lower for kw in self.CLOSE_UP_KEYWORDS):
            return CameraAngle.CLOSE_UP
        
        if any(kw in text_lower for kw in self.WIDE_KEYWORDS):
            return CameraAngle.WIDE
        
        if any(kw in text_lower for kw in self.POV_KEYWORDS):
            return CameraAngle.POV
        
        # Default based on content
        if "two" in text_lower and any(w in text_lower for w in ["face", "look", "stare"]):
            return CameraAngle.TWO_SHOT
        
        return CameraAngle.MEDIUM
    
    def _infer_camera_movement(self, text: str) -> CameraMovement:
        """Infer camera movement from text."""
        text_lower = text.lower()
        
        movement_keywords = {
            "follows": CameraMovement.TRACKING,
            "pan": CameraMovement.PAN_LEFT,
            "track": CameraMovement.TRACKING,
            "dolly": CameraMovement.DOLLY_IN,
            "push in": CameraMovement.DOLLY_IN,
            "pull back": CameraMovement.DOLLY_OUT,
            "crane": CameraMovement.CRANE,
            "handheld": CameraMovement.HANDHELD,
            "zoom": CameraMovement.ZOOM,
        }
        
        for keyword, movement in movement_keywords.items():
            if keyword in text_lower:
                return movement
        
        return CameraMovement.STATIC
    
    def _infer_dialogue_camera_angle(self, dialogue: str, context: str) -> CameraAngle:
        """Infer camera angle for dialogue shot."""
        combined = (dialogue + " " + context).lower()
        
        # Intense moments get close-ups
        if any(word in combined for word in ["whisper", "confess", "reveal", "cry", "tears"]):
            return CameraAngle.CLOSE_UP
        
        return CameraAngle.MEDIUM
    
    def _infer_emotion(self, parenthetical: Optional[str], dialogue: str) -> str:
        """Infer emotion from parenthetical and dialogue."""
        text = ((parenthetical or "") + " " + (dialogue or "")).lower()
        
        for emotion, keywords in self.EMOTION_MAP.items():
            if any(kw in text for kw in keywords):
                return emotion
        
        return "neutral"
    
    def _extract_characters_from_text(self, text: str) -> List[str]:
        """Extract character names mentioned in text."""
        # Look for names that are known characters
        characters = []
        
        for char in self._character_appearances.keys():
            if char.upper() in text.upper():
                characters.append(char)
        
        # Also look for capitalized names
        words = re.findall(r'\b[A-Z][A-Z]+\b', text)
        for word in words:
            if len(word) > 2 and word not in ["THE", "AND", "INT", "EXT"]:
                if word not in characters:
                    characters.append(word)
        
        return characters[:3]  # Limit to 3 characters per shot
    
    def _build_visual_prompt(self, action_text: str, characters: List[str]) -> str:
        """Build a visual prompt for video generation."""
        # Clean up the action text
        prompt = action_text.strip()
        
        # Add character context
        if characters:
            char_str = ", ".join(characters)
            if char_str.upper() not in prompt.upper():
                prompt = f"{char_str} - {prompt}"
        
        # Limit length
        if len(prompt) > 300:
            prompt = prompt[:297] + "..."
        
        return prompt
    
    def _build_dialogue_visual_prompt(
        self, character: str, dialogue: str, emotion: str, context: str
    ) -> str:
        """Build visual prompt for dialogue shot."""
        parts = []
        
        # Character and emotion
        parts.append(f"{character} speaking")
        if emotion != "neutral":
            parts.append(f"with {emotion} expression")
        
        # Context
        if context:
            parts.append(f"- {context[:100]}")
        
        return ", ".join(parts)
    
    def _calculate_confidence(self, text: str, characters: List[str]) -> float:
        """Calculate confidence score for the shot."""
        confidence = 0.7  # Base confidence
        
        # Reduce confidence for vague descriptions
        vague_words = ["something", "somehow", "perhaps", "maybe", "unclear"]
        for word in vague_words:
            if word in text.lower():
                confidence -= 0.1
        
        # Increase confidence for specific details
        if characters:
            confidence += 0.05 * min(len(characters), 2)
        
        # Bound confidence
        return max(0.3, min(0.95, confidence))
    
    def _identify_unknowns(self, text: str) -> List[str]:
        """Identify unknowns that need clarification."""
        unknowns = []
        
        # Check for time indicators
        if not any(t in text.lower() for t in ["day", "night", "morning", "evening"]):
            if "exterior" in text.lower() or "ext" in text.lower()[:10]:
                unknowns.append("Time of day not specified")
        
        # Check for character details
        if "man" in text.lower() or "woman" in text.lower():
            unknowns.append("Character appearance not specified")
        
        return unknowns
    
    def _estimate_duration(self, text: str) -> float:
        """Estimate shot duration in seconds."""
        # Base duration
        duration = 5.0
        
        # Adjust based on action complexity
        word_count = len(text.split())
        if word_count > 50:
            duration = 8.0
        elif word_count > 100:
            duration = 12.0
        elif word_count < 20:
            duration = 3.0
        
        return duration
    
    def _is_shot_break(self, text: str) -> bool:
        """Determine if text indicates a natural shot break."""
        indicators = [
            "cut to", "angle on", "close on", "wide shot",
            "new angle", "reverse", "another angle"
        ]
        
        return any(ind in text.lower() for ind in indicators)
    
    def _build_character_list(self, parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build character list with metadata."""
        raw_characters = parsed.get("characters", [])
        
        characters = []
        for char_name in raw_characters:
            appearances = self._character_appearances.get(char_name, [])
            
            characters.append({
                "name": char_name,
                "scene_count": len(appearances),
                "first_scene": appearances[0] if appearances else None,
                "scenes": appearances,
            })
        
        # Sort by scene count (prominence)
        characters.sort(key=lambda c: c["scene_count"], reverse=True)
        
        return characters
    
    def _detect_contradictions(
        self, parsed: Dict[str, Any], scenes: List[SceneBreakdown]
    ) -> List[Contradiction]:
        """Detect contradictions in the screenplay."""
        contradictions = []
        
        # Track character descriptions
        char_descriptions: Dict[str, List[Tuple[str, str]]] = {}
        
        for scene in scenes:
            for shot in scene.shots:
                # Look for character descriptions in prompts
                for char in shot.characters_in_frame:
                    desc_matches = re.findall(
                        rf'{char}[,\s]+([\w\s,]+)',
                        shot.visual_prompt,
                        re.IGNORECASE
                    )
                    for match in desc_matches:
                        if char not in char_descriptions:
                            char_descriptions[char] = []
                        char_descriptions[char].append((scene.scene_number, match.strip()))
        
        # Check for height/appearance contradictions
        height_words = ["tall", "short", "medium height"]
        hair_words = ["blonde", "brunette", "redhead", "bald", "gray", "black hair"]
        
        for char, descriptions in char_descriptions.items():
            # Check heights
            heights_found = set()
            for scene_num, desc in descriptions:
                for h in height_words:
                    if h in desc.lower():
                        heights_found.add((h, scene_num))
            
            if len(heights_found) > 1:
                contradictions.append(Contradiction(
                    contradiction_id=f"char_height_{char}",
                    type="character_description",
                    description=f"Character '{char}' has conflicting height descriptions",
                    locations=[{"scene": s, "value": h} for h, s in heights_found],
                    severity="warning",
                    suggested_resolution=f"Clarify {char}'s height in Character Laboratory",
                ))
        
        return contradictions
    
    def _to_dict(self, result: ShotListResult) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "title": result.title,
            "scenes": [
                {
                    "scene_id": scene.scene_id,
                    "scene_number": scene.scene_number,
                    "slug": scene.slug,
                    "location": scene.location,
                    "time_of_day": scene.time_of_day,
                    "int_ext": scene.int_ext,
                    "description": scene.description,
                    "characters_present": scene.characters_present,
                    "estimated_duration_seconds": scene.estimated_duration_seconds,
                    "shots": [
                        {
                            "shot_id": shot.shot_id,
                            "visual_prompt": shot.visual_prompt,
                            "negative_prompt": shot.negative_prompt,
                            "camera_angle": shot.camera_angle.value,
                            "camera_movement": shot.camera_movement.value,
                            "characters_in_frame": shot.characters_in_frame,
                            "dialogue": {
                                "character": shot.dialogue.character,
                                "text": shot.dialogue.text,
                                "emotion": shot.dialogue.emotion,
                                "parenthetical": shot.dialogue.parenthetical,
                            } if shot.dialogue else None,
                            "duration_estimate_seconds": shot.duration_estimate_seconds,
                            "confidence": shot.confidence,
                            "unknowns": shot.unknowns,
                            "source": shot.source,
                        }
                        for shot in scene.shots
                    ],
                }
                for scene in result.scenes
            ],
            "characters": result.characters,
            "contradictions": [
                {
                    "contradiction_id": c.contradiction_id,
                    "type": c.type,
                    "description": c.description,
                    "locations": c.locations,
                    "severity": c.severity,
                    "suggested_resolution": c.suggested_resolution,
                }
                for c in result.contradictions
            ],
            "summary": {
                "total_shots": result.total_shots,
                "total_scenes": len(result.scenes),
                "total_characters": len(result.characters),
                "estimated_duration_seconds": result.estimated_duration_seconds,
                "parse_confidence": result.parse_confidence,
                "contradiction_count": len(result.contradictions),
            },
            "warnings": result.warnings,
        }


def generate_shot_list(parsed_screenplay: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to generate shot list.
    
    Args:
        parsed_screenplay: Output from any screenplay parser
        
    Returns:
        Complete shot list with scenes, shots, and metadata
    """
    generator = ShotListGenerator()
    return generator.generate(parsed_screenplay)
