"""Tests for CharacterService."""

from uuid import uuid4

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.models import Character, Project
from scenemachine.models.character import CharacterGender, CharacterLockState
from scenemachine.services.character import (
    CharacterService,
    PhysicalDescription,
)


@pytest_asyncio.fixture
async def character_service(db_session: AsyncSession) -> CharacterService:
    """Create CharacterService instance."""
    return CharacterService(db_session)


@pytest_asyncio.fixture
async def sample_character(db_session: AsyncSession, sample_project: Project) -> Character:
    """Create a sample character for testing."""
    character = Character(
        project_id=sample_project.id,
        name="JOHN",
        dialogue_count=10,
        scene_count=5,
        first_appearance="1",
        description="A determined man in his 30s.",
        gender=CharacterGender.MALE,
    )
    db_session.add(character)
    await db_session.commit()
    await db_session.refresh(character)
    return character


class TestPhysicalDescription:
    """Test suite for PhysicalDescription dataclass."""

    def test_to_dict(self):
        """Test converting PhysicalDescription to dict."""
        desc = PhysicalDescription(
            hair_color="brown",
            hair_style="short",
            eye_color="blue",
            skin_tone="fair",
            height="tall",
            build="athletic",
            distinguishing_features=["scar on left cheek"],
            clothing_style="casual",
            additional_notes="Always wears a watch",
        )
        result = desc.to_dict()

        assert result["hair_color"] == "brown"
        assert result["eye_color"] == "blue"
        assert "scar on left cheek" in result["distinguishing_features"]

    def test_from_dict(self):
        """Test creating PhysicalDescription from dict."""
        data = {
            "hair_color": "black",
            "hair_style": "curly",
            "eye_color": "green",
            "skin_tone": "olive",
            "height": "average",
            "build": "slim",
            "distinguishing_features": ["tattoo", "piercing"],
            "clothing_style": "formal",
            "additional_notes": "Wears glasses",
        }
        desc = PhysicalDescription.from_dict(data)

        assert desc.hair_color == "black"
        assert desc.hair_style == "curly"
        assert len(desc.distinguishing_features) == 2

    def test_from_dict_with_defaults(self):
        """Test creating PhysicalDescription with missing fields."""
        data = {"hair_color": "red"}
        desc = PhysicalDescription.from_dict(data)

        assert desc.hair_color == "red"
        assert desc.eye_color == ""
        assert desc.distinguishing_features == []

    def test_roundtrip(self):
        """Test dict conversion roundtrip."""
        original = PhysicalDescription(
            hair_color="blonde",
            eye_color="brown",
            distinguishing_features=["freckles"],
        )
        data = original.to_dict()
        restored = PhysicalDescription.from_dict(data)

        assert restored.hair_color == original.hair_color
        assert restored.eye_color == original.eye_color
        assert restored.distinguishing_features == original.distinguishing_features


class TestCharacterService:
    """Test suite for CharacterService."""

    async def test_get_project_characters(
        self,
        character_service: CharacterService,
        sample_character: Character,
        sample_project: Project,
    ):
        """Test getting characters for a project."""
        characters = await character_service.get_project_characters(sample_project.id)
        assert len(characters) == 1
        assert characters[0].name == "JOHN"

    async def test_get_project_characters_empty(
        self,
        character_service: CharacterService,
        sample_project: Project,
    ):
        """Test getting characters for project with no characters."""
        characters = await character_service.get_project_characters(sample_project.id)
        assert len(characters) == 0

    async def test_get_project_characters_ordered_by_scene_count(
        self,
        character_service: CharacterService,
        db_session: AsyncSession,
        sample_project: Project,
    ):
        """Test characters are ordered by scene count."""
        # Create multiple characters with different scene counts
        char1 = Character(
            project_id=sample_project.id,
            name="MINOR",
            dialogue_count=1,
            scene_count=1,
        )
        char2 = Character(
            project_id=sample_project.id,
            name="MAIN",
            dialogue_count=20,
            scene_count=15,
        )
        char3 = Character(
            project_id=sample_project.id,
            name="SUPPORTING",
            dialogue_count=10,
            scene_count=8,
        )
        db_session.add_all([char1, char2, char3])
        await db_session.commit()

        characters = await character_service.get_project_characters(sample_project.id)

        # Should be ordered by scene_count descending
        assert characters[0].name == "MAIN"
        assert characters[1].name == "SUPPORTING"
        assert characters[2].name == "MINOR"

    async def test_get_character(
        self,
        character_service: CharacterService,
        sample_character: Character,
    ):
        """Test getting a single character."""
        character = await character_service.get_character(sample_character.id)
        assert character is not None
        assert character.name == "JOHN"

    async def test_get_character_not_found(
        self,
        character_service: CharacterService,
    ):
        """Test getting non-existent character."""
        character = await character_service.get_character(uuid4())
        assert character is None


class TestCharacterUpdate:
    """Test suite for character update operations."""

    async def test_update_character_description(
        self,
        character_service: CharacterService,
        sample_character: Character,
        db_session: AsyncSession,
    ):
        """Test updating character description."""
        new_description = "A weathered detective with a troubled past."
        sample_character.description = new_description
        await db_session.commit()
        await db_session.refresh(sample_character)

        character = await character_service.get_character(sample_character.id)
        assert character.description == new_description

    async def test_update_character_physical_description(
        self,
        character_service: CharacterService,
        sample_character: Character,
        db_session: AsyncSession,
    ):
        """Test updating physical description."""
        physical_desc = PhysicalDescription(
            hair_color="gray",
            eye_color="hazel",
            build="stocky",
        )
        sample_character.physical_description = physical_desc.to_dict()
        await db_session.commit()
        await db_session.refresh(sample_character)

        character = await character_service.get_character(sample_character.id)
        desc = PhysicalDescription.from_dict(character.physical_description)
        assert desc.hair_color == "gray"
        assert desc.eye_color == "hazel"


class TestCharacterLocking:
    """Test suite for character locking workflow."""

    async def test_character_initial_state(
        self,
        sample_character: Character,
    ):
        """Test character initial lock state."""
        assert sample_character.lock_state == CharacterLockState.UNLOCKED

    async def test_lock_character(
        self,
        sample_character: Character,
        db_session: AsyncSession,
    ):
        """Test locking a character."""
        sample_character.lock_state = CharacterLockState.LOCKED
        await db_session.commit()
        await db_session.refresh(sample_character)

        assert sample_character.lock_state == CharacterLockState.LOCKED

    async def test_pending_approval_state(
        self,
        sample_character: Character,
        db_session: AsyncSession,
    ):
        """Test pending approval state."""
        sample_character.lock_state = CharacterLockState.PENDING_APPROVAL
        await db_session.commit()
        await db_session.refresh(sample_character)

        assert sample_character.lock_state == CharacterLockState.PENDING_APPROVAL


class TestCharacterGender:
    """Test suite for character gender handling."""

    async def test_gender_enum_values(self):
        """Test all gender enum values."""
        assert CharacterGender.MALE.value == "male"
        assert CharacterGender.FEMALE.value == "female"
        assert CharacterGender.NON_BINARY.value == "non_binary"
        assert CharacterGender.UNSPECIFIED.value == "unspecified"

    async def test_character_gender_assignment(
        self,
        db_session: AsyncSession,
        sample_project: Project,
    ):
        """Test assigning different genders to characters."""
        characters = [
            Character(
                project_id=sample_project.id,
                name="ALEX",
                dialogue_count=5,
                scene_count=3,
                gender=CharacterGender.NON_BINARY,
            ),
            Character(
                project_id=sample_project.id,
                name="SARAH",
                dialogue_count=8,
                scene_count=4,
                gender=CharacterGender.FEMALE,
            ),
        ]
        for char in characters:
            db_session.add(char)
        await db_session.commit()

        for char in characters:
            await db_session.refresh(char)
            if char.name == "ALEX":
                assert char.gender == CharacterGender.NON_BINARY
            elif char.name == "SARAH":
                assert char.gender == CharacterGender.FEMALE


class TestDefaultNegativePrompt:
    """Test suite for default negative prompt."""

    def test_default_negative_prompt_content(self):
        """Test default negative prompt contains key terms."""
        prompt = CharacterService.DEFAULT_NEGATIVE_PROMPT
        assert "deformed" in prompt
        assert "blurry" in prompt
        assert "watermark" in prompt
        assert "extra fingers" in prompt

    def test_default_negative_prompt_is_string(self):
        """Test default negative prompt is a string."""
        prompt = CharacterService.DEFAULT_NEGATIVE_PROMPT
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Should be reasonably detailed


class TestCharacterMetadata:
    """Test suite for character metadata fields."""

    async def test_dialogue_and_scene_counts(
        self,
        sample_character: Character,
    ):
        """Test dialogue and scene count tracking."""
        assert sample_character.dialogue_count == 10
        assert sample_character.scene_count == 5

    async def test_first_appearance(
        self,
        sample_character: Character,
    ):
        """Test first appearance tracking."""
        assert sample_character.first_appearance == "1"

    async def test_voice_settings(
        self,
        sample_character: Character,
        db_session: AsyncSession,
    ):
        """Test voice settings storage."""
        voice_settings = {
            "provider": "elevenlabs",
            "voice_id": "test-voice-123",
            "stability": 0.7,
            "similarity_boost": 0.8,
        }
        sample_character.voice_settings = voice_settings
        await db_session.commit()
        await db_session.refresh(sample_character)

        assert sample_character.voice_settings["provider"] == "elevenlabs"
        assert sample_character.voice_settings["voice_id"] == "test-voice-123"


class TestCharacterQueryOptimization:
    """Test suite for query optimization features."""

    async def test_get_characters_with_references_flag(
        self,
        character_service: CharacterService,
        sample_project: Project,
    ):
        """Test that include_references flag works without errors."""
        # Should not raise even with no reference assets
        characters = await character_service.get_project_characters(
            sample_project.id,
            include_references=True,
        )
        assert isinstance(characters, list)

    async def test_get_character_with_references_flag(
        self,
        character_service: CharacterService,
        sample_character: Character,
    ):
        """Test getting character with references."""
        character = await character_service.get_character(
            sample_character.id,
            include_references=True,
        )
        assert character is not None
        assert character.name == "JOHN"
