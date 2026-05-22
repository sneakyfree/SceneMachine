"""Tests for Fountain screenplay parser."""

import pytest

from scenemachine.parsers.fountain import FountainParser, parse_fountain


class TestFountainParser:
    """Test suite for FountainParser class."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return FountainParser()

    def test_parse_empty_content(self, parser):
        """Test parsing empty content."""
        result = parser.parse("")
        assert result.elements == []
        assert result.characters == set()

    def test_parse_title_page(self, parser):
        """Test parsing title page."""
        content = """Title: My Great Movie
Author: John Doe
Draft date: 2024-01-15

FADE IN:
"""
        result = parser.parse(content)
        assert result.title_page.title == "My Great Movie"
        assert result.title_page.author == "John Doe"
        assert result.title_page.draft_date == "2024-01-15"

    def test_parse_scene_heading(self, parser):
        """Test parsing scene headings."""
        content = """INT. LIVING ROOM - DAY

Some action here.
"""
        result = parser.parse(content)

        # Find scene heading element
        scene_heading = next(
            (e for e in result.elements if e.element_type == "scene_heading"), None
        )

        assert scene_heading is not None
        assert "LIVING ROOM" in scene_heading.text
        assert "DAY" in scene_heading.text

    def test_parse_exterior_scene(self, parser):
        """Test parsing exterior scene heading."""
        content = """EXT. BEACH - NIGHT

Waves crash on the shore.
"""
        result = parser.parse(content)

        scene_heading = next(
            (e for e in result.elements if e.element_type == "scene_heading"), None
        )

        assert scene_heading is not None
        assert "EXT" in scene_heading.text
        assert "BEACH" in scene_heading.text
        assert "NIGHT" in scene_heading.text

    def test_parse_character_and_dialogue(self, parser):
        """Test parsing character names and dialogue."""
        content = """INT. OFFICE - DAY

JOHN
Hello, how are you?

MARY
I'm doing well, thank you.
"""
        result = parser.parse(content)

        # Check characters were extracted
        assert "JOHN" in result.characters
        assert "MARY" in result.characters

        # Check dialogue elements
        dialogues = [e for e in result.elements if e.element_type == "dialogue"]
        assert len(dialogues) >= 2

    def test_parse_action_lines(self, parser):
        """Test parsing action lines."""
        content = """INT. ROOM - DAY

John walks across the room. He picks up a book and examines it carefully.
"""
        result = parser.parse(content)

        actions = [e for e in result.elements if e.element_type == "action"]
        assert len(actions) >= 1

        action_text = " ".join(a.text for a in actions)
        assert "walks" in action_text
        assert "book" in action_text

    def test_parse_parenthetical(self, parser):
        """Test parsing parentheticals."""
        content = """INT. ROOM - DAY

JOHN
(whispering)
Don't tell anyone.
"""
        result = parser.parse(content)

        parenthetical = next(
            (e for e in result.elements if e.element_type == "parenthetical"), None
        )

        assert parenthetical is not None
        assert "whispering" in parenthetical.text

    def test_parse_transition(self, parser):
        """Test parsing transitions."""
        content = """INT. ROOM - DAY

John looks up.

CUT TO:

EXT. STREET - DAY
"""
        result = parser.parse(content)

        transition = next((e for e in result.elements if e.element_type == "transition"), None)

        assert transition is not None
        assert "CUT TO" in transition.text

    def test_parse_dual_dialogue(self, parser):
        """Test parsing dual dialogue."""
        content = """INT. ROOM - DAY

JOHN
Left side.

MARY ^
Right side.
"""
        result = parser.parse(content)

        # Both characters should be detected
        assert "JOHN" in result.characters
        assert "MARY" in result.characters

    def test_extract_scenes(self, parser):
        """Test scene extraction."""
        content = """INT. KITCHEN - MORNING

Alice makes breakfast.

EXT. BACKYARD - DAY

Bob tends the garden.

INT. LIVING ROOM - EVENING

They watch TV together.
"""
        result = parser.parse(content)
        scenes = result.to_dict().get("scenes", [])

        assert len(scenes) == 3

        # Check first scene
        assert scenes[0]["location"] == "KITCHEN"
        assert scenes[0]["time_of_day"] == "MORNING"

        # Check second scene
        assert "BACKYARD" in scenes[1]["location"]
        assert scenes[1]["time_of_day"] == "DAY"

    def test_parse_forced_scene_heading(self, parser):
        """Test forced scene heading with period prefix."""
        content = """.CUSTOM SCENE

Action here.
"""
        result = parser.parse(content)

        scene_heading = next(
            (e for e in result.elements if e.element_type == "scene_heading"), None
        )

        assert scene_heading is not None

    def test_character_with_extension(self, parser):
        """Test character with V.O. or O.S. extension."""
        content = """INT. ROOM - DAY

NARRATOR (V.O.)
Once upon a time...

GHOST (O.S.)
Hello?
"""
        result = parser.parse(content)

        # Character names should be extracted without extensions
        assert "NARRATOR" in result.characters or "NARRATOR (V.O.)" in result.characters
        assert "GHOST" in result.characters or "GHOST (O.S.)" in result.characters

    def test_parse_fountain_convenience_function(self):
        """Test the parse_fountain convenience function."""
        content = """Title: Test Script

INT. ROOM - DAY

HERO
Hello world!
"""
        result = parse_fountain(content)

        assert isinstance(result, dict)
        assert "elements" in result
        assert "characters" in result
        assert "scenes" in result
        assert "metadata" in result

    def test_metadata_extraction(self, parser):
        """Test metadata is correctly extracted."""
        content = """Title: My Movie

INT. SCENE ONE - DAY

ALICE
Line one.

ALICE
Line two.

BOB
Line three.

INT. SCENE TWO - NIGHT

BOB
Line four.
"""
        result = parser.parse(content)
        metadata = result.to_dict().get("metadata", {})

        assert metadata.get("scene_count") == 2
        assert metadata.get("character_count") == 2
        assert metadata.get("element_count") > 0


class TestFountainEdgeCases:
    """Test edge cases and complex scenarios."""

    @pytest.fixture
    def parser(self):
        return FountainParser()

    def test_multiple_blank_lines(self, parser):
        """Test handling of multiple blank lines."""
        content = """INT. ROOM - DAY



JOHN
Hello.



EXT. STREET - DAY
"""
        result = parser.parse(content)

        scenes = result.to_dict().get("scenes", [])
        assert len(scenes) == 2

    def test_unicode_content(self, parser):
        """Test handling of unicode characters."""
        content = """INT. CAFÉ - DAY

MARIE
Bonjour! Comment ça va?

PIERRE
Très bien, merci.
"""
        result = parser.parse(content)

        assert "MARIE" in result.characters
        assert "PIERRE" in result.characters

    def test_numbered_scenes(self, parser):
        """Test handling of numbered scene headings."""
        content = """INT. ROOM - DAY #1#

Action.

EXT. STREET - NIGHT #2#

More action.
"""
        result = parser.parse(content)

        scenes = result.to_dict().get("scenes", [])
        assert len(scenes) == 2

    def test_continuous_time(self, parser):
        """Test CONTINUOUS time of day."""
        content = """INT. HALLWAY - DAY

She walks to the door.

INT. OFFICE - CONTINUOUS

She enters the office.
"""
        result = parser.parse(content)

        scenes = result.to_dict().get("scenes", [])
        assert len(scenes) == 2

        # Second scene should have CONTINUOUS
        assert scenes[1].get("time_of_day") == "CONTINUOUS"
