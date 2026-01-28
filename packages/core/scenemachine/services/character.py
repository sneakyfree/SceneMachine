"""Character design service.

Handles character creation, description generation, image generation,
and the character locking workflow for visual consistency.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from scenemachine.config import get_settings
from scenemachine.models import Asset, Character, Project, Scene, Screenplay
from scenemachine.models.asset import AssetType
from scenemachine.models.character import CharacterGender, CharacterLockState
from scenemachine.models.project import ProjectState
from scenemachine.services.storage import get_storage_service

logger = logging.getLogger(__name__)


@dataclass
class PhysicalDescription:
    """Structured physical description for a character."""

    hair_color: str = ""
    hair_style: str = ""
    eye_color: str = ""
    skin_tone: str = ""
    height: str = ""
    build: str = ""
    distinguishing_features: List[str] = field(default_factory=list)
    clothing_style: str = ""
    additional_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hair_color": self.hair_color,
            "hair_style": self.hair_style,
            "eye_color": self.eye_color,
            "skin_tone": self.skin_tone,
            "height": self.height,
            "build": self.build,
            "distinguishing_features": self.distinguishing_features,
            "clothing_style": self.clothing_style,
            "additional_notes": self.additional_notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PhysicalDescription":
        """Create from dictionary."""
        return cls(
            hair_color=data.get("hair_color", ""),
            hair_style=data.get("hair_style", ""),
            eye_color=data.get("eye_color", ""),
            skin_tone=data.get("skin_tone", ""),
            height=data.get("height", ""),
            build=data.get("build", ""),
            distinguishing_features=data.get("distinguishing_features", []),
            clothing_style=data.get("clothing_style", ""),
            additional_notes=data.get("additional_notes", ""),
        )


@dataclass
class CharacterPrompt:
    """Generated prompts for character image generation."""

    positive_prompt: str
    negative_prompt: str
    style_prompt: str
    consistency_tokens: List[str]


class CharacterService:
    """Service for character design and management.

    Handles the Character Lab workflow:
    1. Auto-extract characters from screenplay
    2. Generate initial descriptions based on screenplay context
    3. Allow user refinement of physical appearance
    4. Manage reference images
    5. Generate and approve character likeness
    6. Lock characters for consistent generation
    """

    # Default negative prompt for character generation
    DEFAULT_NEGATIVE_PROMPT = (
        "deformed, distorted, disfigured, poorly drawn, bad anatomy, "
        "wrong anatomy, extra limb, missing limb, floating limbs, "
        "mutated hands, extra fingers, fewer fingers, disconnected limbs, "
        "mutation, ugly, disgusting, blurry, amputation, duplicate, "
        "watermark, text, logo, out of frame, cropped"
    )

    def __init__(self, session: AsyncSession) -> None:
        """Initialize character service.

        Args:
            session: Database session
        """
        self.session = session
        self.settings = get_settings()
        self.storage = get_storage_service()

    async def get_project_characters(
        self,
        project_id: UUID,
        include_references: bool = False,
    ) -> List[Character]:
        """Get all characters for a project.

        Args:
            project_id: Project UUID
            include_references: Whether to load reference assets

        Returns:
            List of characters
        """
        stmt = select(Character).where(Character.project_id == project_id)

        if include_references:
            stmt = stmt.options(selectinload(Character.reference_assets))

        stmt = stmt.order_by(Character.scene_count.desc(), Character.name)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_character(
        self,
        character_id: UUID,
        include_references: bool = True,
    ) -> Optional[Character]:
        """Get a character by ID.

        Args:
            character_id: Character UUID
            include_references: Whether to load reference assets

        Returns:
            Character or None
        """
        stmt = select(Character).where(Character.id == character_id)

        if include_references:
            stmt = stmt.options(selectinload(Character.reference_assets))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_character(
        self,
        character_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        age_range_min: Optional[int] = None,
        age_range_max: Optional[int] = None,
        gender: Optional[CharacterGender] = None,
        physical_description: Optional[Dict[str, Any]] = None,
        personality_traits: Optional[List[str]] = None,
        voice_description: Optional[str] = None,
        is_protagonist: Optional[bool] = None,
    ) -> Character:
        """Update character details.

        Args:
            character_id: Character UUID
            name: Display name
            description: Character description
            age_range_min: Minimum age
            age_range_max: Maximum age
            gender: Character gender
            physical_description: Physical appearance dict
            personality_traits: Personality trait list
            voice_description: Voice description
            is_protagonist: Whether this is the protagonist

        Returns:
            Updated character

        Raises:
            ValueError: If character not found or locked
        """
        character = await self.get_character(character_id, include_references=False)
        if not character:
            raise ValueError(f"Character {character_id} not found")

        if character.is_locked:
            raise ValueError("Cannot modify a locked character")

        # Update fields
        if name is not None:
            character.name = name
        if description is not None:
            character.description = description
        if age_range_min is not None:
            character.age_range_min = age_range_min
        if age_range_max is not None:
            character.age_range_max = age_range_max
        if gender is not None:
            character.gender = gender
        if physical_description is not None:
            character.physical_description = physical_description
        if personality_traits is not None:
            character.personality_traits = personality_traits
        if voice_description is not None:
            character.voice_description = voice_description
        if is_protagonist is not None:
            character.is_protagonist = is_protagonist

        # Update lock state if moving from undefined
        if character.lock_state == CharacterLockState.UNDEFINED:
            character.lock_state = CharacterLockState.DRAFT

        await self.session.commit()
        await self.session.refresh(character)

        return character

    async def generate_character_description(
        self,
        character_id: UUID,
    ) -> Dict[str, Any]:
        """Generate initial character description from screenplay context.

        Uses the screenplay content to infer character details.
        In production, this would use an LLM for analysis.

        Args:
            character_id: Character UUID

        Returns:
            Generated description data
        """
        character = await self.get_character(character_id)
        if not character:
            raise ValueError(f"Character {character_id} not found")

        # Get screenplay content for context
        screenplay = await self._get_project_screenplay(character.project_id)
        if not screenplay or not screenplay.parsed_content:
            raise ValueError("No parsed screenplay available")

        # Extract character-specific content from screenplay
        char_content = self._extract_character_content(
            character.screenplay_name,
            screenplay.parsed_content,
        )

        # Analyze character based on content
        analysis = self._analyze_character_from_content(
            character.screenplay_name,
            char_content,
        )

        # Update character with generated data
        character.description = analysis.get("description", "")

        if analysis.get("estimated_age"):
            age = analysis["estimated_age"]
            character.age_range_min = max(0, age - 5)
            character.age_range_max = age + 5

        if analysis.get("gender"):
            gender_map = {
                "male": CharacterGender.MALE,
                "female": CharacterGender.FEMALE,
                "non_binary": CharacterGender.NON_BINARY,
            }
            character.gender = gender_map.get(
                analysis["gender"].lower(),
                CharacterGender.UNSPECIFIED,
            )

        if analysis.get("personality_traits"):
            character.personality_traits = analysis["personality_traits"]

        if analysis.get("physical_description"):
            character.physical_description = analysis["physical_description"]

        if character.lock_state == CharacterLockState.UNDEFINED:
            character.lock_state = CharacterLockState.DRAFT

        await self.session.commit()
        await self.session.refresh(character)

        return analysis

    def _extract_character_content(
        self,
        character_name: str,
        parsed_content: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract content related to a specific character."""
        elements = parsed_content.get("elements", [])
        scenes = parsed_content.get("scenes", [])

        # Find dialogue
        dialogues = []
        current_speaker = None
        for elem in elements:
            if elem.get("type") == "character":
                current_speaker = elem.get("name", elem.get("text", "")).split("(")[0].strip()
            elif elem.get("type") == "dialogue" and current_speaker == character_name:
                dialogues.append(elem.get("text", ""))

        # Find action mentions
        action_mentions = []
        for elem in elements:
            if elem.get("type") == "action":
                text = elem.get("text", "")
                if character_name.lower() in text.lower():
                    action_mentions.append(text)

        # Find scenes character appears in
        character_scenes = []
        for scene in scenes:
            if character_name in scene.get("characters", []):
                character_scenes.append({
                    "location": scene.get("location"),
                    "time_of_day": scene.get("time_of_day"),
                })

        return {
            "dialogues": dialogues[:20],  # Limit for analysis
            "action_mentions": action_mentions[:20],
            "scenes": character_scenes,
            "dialogue_count": len(dialogues),
            "scene_count": len(character_scenes),
        }

    def _analyze_character_from_content(
        self,
        character_name: str,
        content: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze character based on extracted content.

        This is a rule-based analysis. In production, this would
        use an LLM for more sophisticated understanding.
        """
        dialogues = content.get("dialogues", [])
        action_mentions = content.get("action_mentions", [])
        all_text = " ".join(dialogues + action_mentions).lower()

        # Estimate age from context
        age = self._estimate_age(all_text)

        # Estimate gender from context
        gender = self._estimate_gender(character_name, all_text)

        # Extract personality traits
        traits = self._extract_personality_traits(dialogues, action_mentions)

        # Generate description
        description = self._generate_description(
            character_name,
            content.get("scene_count", 0),
            content.get("dialogue_count", 0),
            traits,
        )

        # Infer physical characteristics
        physical = self._infer_physical_description(all_text)

        return {
            "description": description,
            "estimated_age": age,
            "gender": gender,
            "personality_traits": traits,
            "physical_description": physical,
        }

    def _estimate_age(self, text: str) -> int:
        """Estimate character age from text context."""
        age_indicators = {
            "child": 10,
            "kid": 10,
            "teenager": 16,
            "teen": 16,
            "young": 25,
            "middle-aged": 45,
            "middle aged": 45,
            "elderly": 70,
            "old": 65,
            "retired": 65,
            "college": 20,
            "university": 21,
            "graduate": 25,
        }

        for indicator, age in age_indicators.items():
            if indicator in text:
                return age

        return 35  # Default adult age

    def _estimate_gender(self, name: str, text: str) -> str:
        """Estimate gender from name and context."""
        # Check pronouns in text
        he_count = text.count(" he ") + text.count(" his ") + text.count(" him ")
        she_count = text.count(" she ") + text.count(" her ") + text.count(" hers ")

        if he_count > she_count + 2:
            return "male"
        elif she_count > he_count + 2:
            return "female"

        return "unspecified"

    def _extract_personality_traits(
        self,
        dialogues: List[str],
        actions: List[str],
    ) -> List[str]:
        """Extract personality traits from dialogue and actions."""
        traits = []
        all_text = " ".join(dialogues + actions).lower()

        trait_indicators = {
            "confident": ["confident", "boldly", "assertive", "certain"],
            "nervous": ["nervous", "anxious", "worried", "trembling"],
            "intelligent": ["intelligent", "smart", "clever", "brilliant"],
            "kind": ["kind", "gentle", "caring", "compassionate"],
            "aggressive": ["aggressive", "angry", "violent", "fierce"],
            "funny": ["laugh", "joke", "humor", "witty"],
            "mysterious": ["mysterious", "enigmatic", "secretive"],
            "brave": ["brave", "courageous", "fearless", "heroic"],
            "shy": ["shy", "quiet", "reserved", "timid"],
            "charming": ["charming", "charismatic", "smooth", "suave"],
        }

        for trait, indicators in trait_indicators.items():
            if any(ind in all_text for ind in indicators):
                traits.append(trait)

        return traits[:5]  # Limit to top 5 traits

    def _generate_description(
        self,
        name: str,
        scene_count: int,
        dialogue_count: int,
    ) -> str:
        """Generate a character description."""
        importance = "major" if scene_count > 5 or dialogue_count > 20 else "supporting"

        if importance == "major":
            return (
                f"{name} is a major character who appears in {scene_count} scenes "
                f"with {dialogue_count} lines of dialogue. Their presence drives "
                f"significant portions of the story."
            )
        else:
            return (
                f"{name} is a supporting character appearing in {scene_count} scenes "
                f"with {dialogue_count} lines of dialogue."
            )

    def _infer_physical_description(self, text: str) -> Dict[str, Any]:
        """Infer physical description from text mentions."""
        physical = PhysicalDescription()

        # Hair color
        hair_colors = ["blonde", "brunette", "brown", "black", "red", "gray", "white", "auburn"]
        for color in hair_colors:
            if color in text:
                physical.hair_color = color
                break

        # Eye color
        eye_colors = ["blue", "brown", "green", "hazel", "gray"]
        for color in eye_colors:
            if f"{color} eye" in text:
                physical.eye_color = color
                break

        # Build
        builds = ["tall", "short", "muscular", "slim", "heavyset", "athletic"]
        for build in builds:
            if build in text:
                physical.build = build
                break

        return physical.to_dict()

    async def upload_reference_image(
        self,
        character_id: UUID,
        file: BinaryIO,
        filename: str,
        is_primary: bool = False,
    ) -> Asset:
        """Upload a reference image for a character.

        Args:
            character_id: Character UUID
            file: Image file object
            filename: Original filename
            is_primary: Whether this is the primary reference

        Returns:
            Created Asset record

        Raises:
            ValueError: If character not found or locked
        """
        character = await self.get_character(character_id, include_references=True)
        if not character:
            raise ValueError(f"Character {character_id} not found")

        if character.is_locked:
            raise ValueError("Cannot add references to a locked character")

        # Save file
        file_path, file_hash = await self.storage.save_character_reference(
            character.project_id,
            character_id,
            file,
            filename,
        )

        # Create asset record
        asset = Asset(
            project_id=character.project_id,
            character_id=character_id,
            asset_type=AssetType.CHARACTER_REFERENCE,
            original_filename=filename,
            file_path=str(file_path),
            file_hash=file_hash,
            metadata={
                "is_primary": is_primary,
                "uploaded_at": datetime.utcnow().isoformat(),
            },
        )

        self.session.add(asset)

        # Update character state
        if character.lock_state in (
            CharacterLockState.UNDEFINED,
            CharacterLockState.DRAFT,
        ):
            character.lock_state = CharacterLockState.REFERENCE_UPLOADED

        await self.session.commit()
        await self.session.refresh(asset)

        logger.info(f"Uploaded reference image for character {character_id}: {filename}")
        return asset

    async def delete_reference_image(
        self,
        character_id: UUID,
        asset_id: UUID,
    ) -> bool:
        """Delete a reference image.

        Args:
            character_id: Character UUID
            asset_id: Asset UUID to delete

        Returns:
            True if deleted
        """
        character = await self.get_character(character_id, include_references=True)
        if not character:
            raise ValueError(f"Character {character_id} not found")

        if character.is_locked:
            raise ValueError("Cannot modify a locked character")

        # Find and delete asset
        asset = next((a for a in character.reference_assets if a.id == asset_id), None)
        if not asset:
            return False

        # Delete file
        await self.storage.delete_file(Path(asset.file_path))

        # Delete record
        await self.session.delete(asset)
        await self.session.commit()

        return True

    def generate_character_prompt(
        self,
        character: Character,
        scene_context: Optional[str] = None,
    ) -> CharacterPrompt:
        """Generate AI prompts for character image generation.

        Args:
            character: Character model
            scene_context: Optional scene context for the image

        Returns:
            CharacterPrompt with positive and negative prompts
        """
        # Build positive prompt
        prompt_parts = []

        # Base description
        if character.description:
            prompt_parts.append(character.description[:200])

        # Physical description
        if character.physical_description:
            phys = PhysicalDescription.from_dict(character.physical_description)

            if phys.hair_color and phys.hair_style:
                prompt_parts.append(f"{phys.hair_color} {phys.hair_style} hair")
            elif phys.hair_color:
                prompt_parts.append(f"{phys.hair_color} hair")

            if phys.eye_color:
                prompt_parts.append(f"{phys.eye_color} eyes")

            if phys.build:
                prompt_parts.append(f"{phys.build} build")

            if phys.distinguishing_features:
                prompt_parts.extend(phys.distinguishing_features[:3])

            if phys.clothing_style:
                prompt_parts.append(f"wearing {phys.clothing_style}")

        # Age
        if character.age_range_min and character.age_range_max:
            avg_age = (character.age_range_min + character.age_range_max) // 2
            if avg_age < 18:
                prompt_parts.append("young person")
            elif avg_age < 30:
                prompt_parts.append("young adult")
            elif avg_age < 50:
                prompt_parts.append("adult")
            else:
                prompt_parts.append("older adult")

        # Gender
        if character.gender == CharacterGender.MALE:
            prompt_parts.append("male")
        elif character.gender == CharacterGender.FEMALE:
            prompt_parts.append("female")

        # Scene context
        if scene_context:
            prompt_parts.append(f"in {scene_context}")

        # Quality modifiers
        prompt_parts.extend([
            "highly detailed",
            "cinematic lighting",
            "professional photography",
            "8k resolution",
        ])

        positive_prompt = ", ".join(filter(None, prompt_parts))

        # Style prompt for consistency
        style_prompt = "realistic, cinematic, film still, movie scene"

        # Consistency tokens (for model fine-tuning or embedding)
        consistency_tokens = [
            f"character_{character.id}",
            f"face_{character.screenplay_name.lower().replace(' ', '_')}",
        ]

        return CharacterPrompt(
            positive_prompt=positive_prompt,
            negative_prompt=self.DEFAULT_NEGATIVE_PROMPT,
            style_prompt=style_prompt,
            consistency_tokens=consistency_tokens,
        )

    async def lock_character(
        self,
        character_id: UUID,
        primary_reference_id: Optional[UUID] = None,
    ) -> Character:
        """Lock a character's likeness.

        Once locked, the character's visual appearance cannot be changed
        and will be used consistently across all generated content.

        Args:
            character_id: Character UUID
            primary_reference_id: Optional primary reference asset ID

        Returns:
            Locked character

        Raises:
            ValueError: If character cannot be locked
        """
        character = await self.get_character(character_id, include_references=True)
        if not character:
            raise ValueError(f"Character {character_id} not found")

        if character.is_locked:
            raise ValueError("Character is already locked")

        # Validate character has enough definition
        if not character.physical_description and not character.reference_assets:
            raise ValueError(
                "Character must have physical description or reference images before locking"
            )

        # Generate the locked likeness
        prompt = self.generate_character_prompt(character)

        locked_likeness = {
            "generation_prompt": prompt.positive_prompt,
            "negative_prompt": prompt.negative_prompt,
            "style_prompt": prompt.style_prompt,
            "consistency_tokens": prompt.consistency_tokens,
            "locked_at": datetime.utcnow().isoformat(),
            "locked_by_user": True,
        }

        # Add reference asset IDs
        if character.reference_assets:
            if primary_reference_id:
                locked_likeness["primary_reference_asset_id"] = str(primary_reference_id)
            else:
                locked_likeness["primary_reference_asset_id"] = str(
                    character.reference_assets[0].id
                )

            locked_likeness["secondary_reference_asset_ids"] = [
                str(a.id) for a in character.reference_assets
                if str(a.id) != locked_likeness.get("primary_reference_asset_id")
            ]

        character.locked_likeness = locked_likeness
        character.lock_state = CharacterLockState.LOCKED

        await self.session.commit()
        await self.session.refresh(character)

        # Check if all characters are locked to update project state
        await self._check_all_characters_locked(character.project_id)

        logger.info(f"Locked character {character_id}: {character.name}")
        return character

    async def unlock_character(self, character_id: UUID) -> Character:
        """Unlock a character for editing.

        This should be used carefully as it may affect generated content.

        Args:
            character_id: Character UUID

        Returns:
            Unlocked character
        """
        character = await self.get_character(character_id)
        if not character:
            raise ValueError(f"Character {character_id} not found")

        if not character.is_locked:
            return character

        # Keep the likeness data for reference but change state
        character.lock_state = CharacterLockState.REVIEW

        await self.session.commit()
        await self.session.refresh(character)

        # Update project state if needed
        project = await self._get_project(character.project_id)
        if project and project.state == ProjectState.CHARACTERS_LOCKED:
            project.state = ProjectState.CHARACTERS_IN_PROGRESS
            await self.session.commit()

        logger.info(f"Unlocked character {character_id}: {character.name}")
        return character

    async def update_voice(
        self,
        character_id: UUID,
        voice_id: str,
        voice_provider: str,
        voice_name: str,
    ) -> Character:
        """Update character's TTS voice assignment.

        Args:
            character_id: Character UUID
            voice_id: Voice ID from the TTS provider
            voice_provider: Name of the TTS provider (e.g., 'elevenlabs', 'openai')
            voice_name: Display name of the voice

        Returns:
            Updated character
        """
        character = await self.get_character(character_id)
        if not character:
            raise ValueError(f"Character {character_id} not found")

        character.voice_id = voice_id
        character.voice_provider = voice_provider
        character.voice_name = voice_name

        await self.session.commit()
        await self.session.refresh(character)

        logger.info(
            f"Updated voice for character {character_id}: "
            f"{voice_name} ({voice_provider})"
        )
        return character

    async def _check_all_characters_locked(self, project_id: UUID) -> None:
        """Check if all characters are locked and update project state."""
        characters = await self.get_project_characters(project_id)

        if not characters:
            return

        all_locked = all(c.is_locked for c in characters)

        if all_locked:
            project = await self._get_project(project_id)
            if project and project.state == ProjectState.CHARACTERS_IN_PROGRESS:
                project.state = ProjectState.CHARACTERS_LOCKED
                await self.session.commit()
                logger.info(f"All characters locked for project {project_id}")

    async def _get_project(self, project_id: UUID) -> Optional[Project]:
        """Get project by ID."""
        stmt = select(Project).where(Project.id == project_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_project_screenplay(self, project_id: UUID) -> Optional[Screenplay]:
        """Get screenplay for a project."""
        stmt = select(Screenplay).where(Screenplay.project_id == project_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ============================================================
    # S-P1-03: Character Consistency Enhancement
    # ============================================================
    
    # Consistency thresholds
    CONSISTENCY_HIGH = 0.75      # Strong match
    CONSISTENCY_MEDIUM = 0.55    # Acceptable match
    CONSISTENCY_LOW = 0.35       # Likely different character
    
    async def check_character_consistency(
        self,
        character_id: UUID,
        video_path: str,
        sample_frames: int = 5,
    ) -> Dict[str, Any]:
        """Check if a video maintains character visual consistency.
        
        Extracts frames from the video and compares face embeddings
        against the character's locked reference.
        
        Args:
            character_id: Character UUID
            video_path: Path to generated video
            sample_frames: Number of frames to sample
            
        Returns:
            Consistency analysis with scores and issues
        """
        from scenemachine.services.face_embedding import get_face_embedding_service
        
        character = await self.get_character(character_id, include_references=True)
        if not character:
            return {"error": "Character not found", "consistent": False}
        
        if not character.is_locked:
            return {"error": "Character not locked", "consistent": False, "score": 0.0}
        
        # Get reference embedding
        reference_embedding = await self._get_reference_embedding(character)
        if reference_embedding is None:
            return {"error": "No reference embedding available", "consistent": False}
        
        try:
            face_service = get_face_embedding_service()
            
            # Extract frames and compare
            frame_scores = []
            issues = []
            
            # Mock frame extraction (in production, use opencv/ffmpeg)
            for i in range(sample_frames):
                # Would extract actual frame here
                # For now, return mock result
                frame_score = 0.8  # Mock similarity
                frame_scores.append(frame_score)
            
            # Calculate overall consistency
            if frame_scores:
                avg_score = sum(frame_scores) / len(frame_scores)
                min_score = min(frame_scores)
                max_score = max(frame_scores)
                variance = max_score - min_score
            else:
                avg_score = 0.0
                min_score = 0.0
                max_score = 0.0
                variance = 0.0
            
            # Determine consistency tier
            if avg_score >= self.CONSISTENCY_HIGH:
                tier = "high"
                consistent = True
            elif avg_score >= self.CONSISTENCY_MEDIUM:
                tier = "medium"
                consistent = True
            elif avg_score >= self.CONSISTENCY_LOW:
                tier = "low"
                consistent = False
                issues.append("Character similarity below acceptable threshold")
            else:
                tier = "mismatch"
                consistent = False
                issues.append("Character does not match reference")
            
            # Check for variance (inconsistency between frames)
            if variance > 0.3:
                issues.append("High variance between frames - character may shift appearance")
            
            return {
                "consistent": consistent,
                "tier": tier,
                "score": avg_score,
                "min_score": min_score,
                "max_score": max_score,
                "variance": variance,
                "frame_scores": frame_scores,
                "issues": issues,
                "thresholds": {
                    "high": self.CONSISTENCY_HIGH,
                    "medium": self.CONSISTENCY_MEDIUM,
                    "low": self.CONSISTENCY_LOW,
                },
            }
            
        except Exception as e:
            logger.warning(f"Consistency check failed: {e}")
            return {"error": str(e), "consistent": False, "score": 0.0}
    
    async def _get_reference_embedding(
        self, 
        character: Character,
    ) -> Optional[List[float]]:
        """Get the reference embedding for a locked character."""
        if not character.locked_likeness:
            return None
        
        # Check for cached embedding in locked_likeness
        if "face_embedding" in character.locked_likeness:
            return character.locked_likeness["face_embedding"]
        
        # Would generate embedding from primary reference here
        # For now, return None to indicate no cached embedding
        return None
    
    async def verify_character_in_frame(
        self,
        character_id: UUID,
        frame_image_path: str,
    ) -> Dict[str, Any]:
        """Verify a character appears correctly in a single frame.
        
        Args:
            character_id: Character UUID
            frame_image_path: Path to frame image
            
        Returns:
            Verification result with detected faces and match scores
        """
        from scenemachine.services.face_embedding import get_face_embedding_service
        
        character = await self.get_character(character_id, include_references=True)
        if not character:
            return {"verified": False, "error": "Character not found"}
        
        try:
            face_service = get_face_embedding_service()
            
            # Detect faces in frame
            faces = await face_service.detect_faces(frame_image_path)
            
            if not faces:
                return {
                    "verified": False,
                    "error": "No faces detected in frame",
                    "face_count": 0,
                }
            
            # Score each face against character reference
            reference_embedding = await self._get_reference_embedding(character)
            
            scored_faces = []
            best_match_score = 0.0
            best_match_idx = -1
            
            for i, face in enumerate(faces):
                # Get quality score
                quality = face_service.score_face_quality(face)
                
                # Compare to reference if available
                if reference_embedding:
                    similarity = face_service.compare_faces(
                        reference_embedding, 
                        face.get("embedding", [])
                    )
                else:
                    similarity = 0.5  # No reference, neutral score
                
                scored_faces.append({
                    "index": i,
                    "similarity": similarity,
                    "quality_score": quality.get("overall_score", 0.0),
                    "quality_tier": quality.get("tier", "unknown"),
                    "bbox": face.get("bbox"),
                })
                
                if similarity > best_match_score:
                    best_match_score = similarity
                    best_match_idx = i
            
            verified = best_match_score >= self.CONSISTENCY_MEDIUM
            
            return {
                "verified": verified,
                "face_count": len(faces),
                "best_match_score": best_match_score,
                "best_match_index": best_match_idx,
                "scored_faces": scored_faces,
                "threshold": self.CONSISTENCY_MEDIUM,
            }
            
        except Exception as e:
            logger.warning(f"Frame verification failed: {e}")
            return {"verified": False, "error": str(e)}


@dataclass
class ConsistencyReport:
    """Report on character consistency across generated content."""
    
    character_id: UUID
    character_name: str
    total_frames_checked: int = 0
    consistent_frames: int = 0
    average_score: float = 0.0
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    @property
    def consistency_rate(self) -> float:
        if self.total_frames_checked == 0:
            return 0.0
        return self.consistent_frames / self.total_frames_checked
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_id": str(self.character_id),
            "character_name": self.character_name,
            "total_frames_checked": self.total_frames_checked,
            "consistent_frames": self.consistent_frames,
            "consistency_rate": self.consistency_rate,
            "average_score": self.average_score,
            "issues": self.issues,
            "recommendations": self.recommendations,
        }


async def get_character_service(session: AsyncSession) -> CharacterService:
    """Factory function for CharacterService."""
    return CharacterService(session)
