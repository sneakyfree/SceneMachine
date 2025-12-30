"""Tests for PDF screenplay parser."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from scenemachine.parsers.pdf import PDFParser, PDFPage, PDFExtractionResult, parse_pdf


class TestPDFParser:
    """Test suite for PDFParser class."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance with OCR disabled."""
        return PDFParser(use_ocr=False)

    @pytest.fixture
    def parser_with_ocr(self):
        """Create a parser instance with OCR enabled."""
        return PDFParser(use_ocr=True)

    def test_init_without_ocr(self, parser):
        """Test parser initialization without OCR."""
        assert parser.use_ocr is False
        assert parser._tesseract_available is False

    def test_scene_heading_pattern(self, parser):
        """Test scene heading regex pattern."""
        pattern = parser.SCENE_HEADING_PATTERN

        # Should match
        assert pattern.match("INT. LIVING ROOM - DAY")
        assert pattern.match("EXT. BEACH - NIGHT")
        assert pattern.match("INT./EXT. CAR - DAY")
        assert pattern.match("I/E. BUILDING - CONTINUOUS")
        assert pattern.match("  INT. ROOM - DAY")  # With leading spaces

        # Should not match
        assert not pattern.match("INTERIOR ROOM")  # No period/abbreviation
        assert not pattern.match("Some action text")
        assert not pattern.match("JOHN")  # Character name

    def test_transition_pattern(self, parser):
        """Test transition regex pattern."""
        pattern = parser.TRANSITION_PATTERN

        # Should match
        assert pattern.match("CUT TO:")
        assert pattern.match("FADE TO:")
        assert pattern.match("DISSOLVE TO:")
        assert pattern.match("SMASH CUT TO:")

        # Should not match
        assert not pattern.match("CUT")
        assert not pattern.match("Some action")

    def test_page_number_pattern(self, parser):
        """Test page number regex pattern."""
        pattern = parser.PAGE_NUMBER_PATTERN

        # Should match
        assert pattern.match("1")
        assert pattern.match("  42  ")
        assert pattern.match("103.")

        # Should not match
        assert not pattern.match("Page 1")
        assert not pattern.match("INT. ROOM")

    def test_parse_scene_heading(self, parser):
        """Test scene heading parsing."""
        result = parser._parse_scene_heading("INT. LIVING ROOM - DAY")

        assert result["type"] == "INT"
        assert result["location"] == "LIVING ROOM"
        assert result["time_of_day"] == "DAY"

    def test_parse_scene_heading_exterior(self, parser):
        """Test exterior scene heading parsing."""
        result = parser._parse_scene_heading("EXT. BEACH - NIGHT")

        assert result["type"] == "EXT"
        assert result["location"] == "BEACH"
        assert result["time_of_day"] == "NIGHT"

    def test_parse_scene_heading_no_time(self, parser):
        """Test scene heading without time of day."""
        result = parser._parse_scene_heading("INT. WAREHOUSE")

        assert result["type"] == "INT"
        assert result["location"] == "WAREHOUSE"
        assert result["time_of_day"] == ""

    def test_is_character_line_valid(self, parser):
        """Test character line detection."""
        lines = [
            "                         JOHN",
            "          Hello, how are you today?",
        ]

        assert parser._is_character_line(lines[0], lines, 0) is True

    def test_is_character_line_not_centered(self, parser):
        """Test character line with insufficient indentation."""
        lines = [
            "JOHN",  # Not indented enough
            "Hello, how are you?",
        ]

        assert parser._is_character_line(lines[0], lines, 0) is False

    def test_is_character_line_lowercase(self, parser):
        """Test lowercase text is not a character."""
        lines = [
            "                         Some action text",
            "More text.",
        ]

        assert parser._is_character_line(lines[0], lines, 0) is False

    def test_is_dialogue_line(self, parser):
        """Test dialogue line detection."""
        # Proper dialogue indentation (10-30 spaces)
        assert parser._is_dialogue_line("          Hello there!")
        assert parser._is_dialogue_line("               Some dialogue.")

        # Too little indentation
        assert not parser._is_dialogue_line("Hi")
        assert not parser._is_dialogue_line("     Short")

        # Too much indentation (character line territory)
        assert not parser._is_dialogue_line("                                Too indented")

    def test_parse_text_simple_screenplay(self, parser):
        """Test parsing simple screenplay text."""
        text = """1

INT. LIVING ROOM - DAY

                    John enters the room.

                         JOHN
          Hello everyone!

                         MARY
          Hi John!

CUT TO:

EXT. GARDEN - DAY

                    Birds are singing.

2
"""
        result = parser._parse_text(text)

        assert "elements" in result
        assert "characters" in result
        assert "scenes" in result
        assert "metadata" in result

        # Check scenes
        assert len(result["scenes"]) == 2
        assert result["scenes"][0]["location"] == "LIVING ROOM"
        assert result["scenes"][1]["location"] == "GARDEN"

        # Check characters
        assert "JOHN" in result["characters"]
        assert "MARY" in result["characters"]

    def test_parse_text_extracts_dialogue_count(self, parser):
        """Test dialogue counting per scene."""
        text = """
INT. ROOM - DAY

                         JOHN
          Line one.

                         JOHN
          Line two.

                         MARY
          Line three.
"""
        result = parser._parse_text(text)

        assert len(result["scenes"]) == 1
        scene = result["scenes"][0]
        assert scene["dialogue_count"] == 3

    def test_metadata_counts(self, parser):
        """Test metadata contains correct counts."""
        text = """
INT. ROOM - DAY

                         JOHN
          Hello.

INT. OFFICE - NIGHT

                         MARY
          Goodbye.
"""
        result = parser._parse_text(text)
        metadata = result["metadata"]

        assert metadata["scene_count"] == 2
        assert metadata["character_count"] == 2
        assert metadata["element_count"] > 0


class TestPDFExtraction:
    """Test PDF extraction functionality."""

    @pytest.fixture
    def parser(self):
        return PDFParser(use_ocr=False)

    @patch("scenemachine.parsers.pdf.PDFParser._check_fitz")
    def test_fallback_when_no_fitz(self, mock_fitz, parser):
        """Test fallback extraction when PyMuPDF is not available."""
        mock_fitz.return_value = False
        parser._fitz_available = False

        result = parser._fallback_extraction(b"fake pdf bytes")

        # Without any PDF library, should return empty result
        assert isinstance(result, PDFExtractionResult)

    @patch("fitz.open")
    def test_extract_text_from_bytes(self, mock_fitz_open, parser):
        """Test text extraction from PDF bytes."""
        # Mock PyMuPDF document
        mock_page = MagicMock()
        mock_page.get_text.return_value = """INT. ROOM - DAY

JOHN
Hello!
"""
        mock_doc = MagicMock()
        mock_doc.__len__ = lambda self: 1
        mock_doc.__iter__ = lambda self: iter([mock_page])
        mock_doc.__getitem__ = lambda self, i: mock_page
        mock_fitz_open.return_value = mock_doc

        parser._fitz_available = True
        result = parser._extract_text_from_bytes(b"fake pdf bytes")

        assert isinstance(result, PDFExtractionResult)
        assert len(result.pages) == 1
        assert "JOHN" in result.text


class TestParsePDFFunction:
    """Test the parse_pdf convenience function."""

    @patch("scenemachine.parsers.pdf.PDFParser.parse")
    def test_parse_pdf_function(self, mock_parse):
        """Test parse_pdf convenience function."""
        mock_parse.return_value = {
            "elements": [],
            "characters": [],
            "scenes": [],
            "metadata": {},
        }

        result = parse_pdf(Path("/fake/path.pdf"))

        assert isinstance(result, dict)
        mock_parse.assert_called_once()


class TestPDFPageDataclass:
    """Test PDFPage dataclass."""

    def test_pdf_page_creation(self):
        """Test PDFPage creation."""
        page = PDFPage(
            page_number=1,
            text="Some text",
            lines=["Some text"],
            is_ocr=False,
        )

        assert page.page_number == 1
        assert page.text == "Some text"
        assert page.lines == ["Some text"]
        assert page.is_ocr is False

    def test_pdf_page_ocr_flag(self):
        """Test PDFPage with OCR flag."""
        page = PDFPage(
            page_number=1,
            text="OCR text",
            lines=["OCR text"],
            is_ocr=True,
        )

        assert page.is_ocr is True


class TestPDFExtractionResult:
    """Test PDFExtractionResult dataclass."""

    def test_extraction_result_creation(self):
        """Test PDFExtractionResult creation."""
        pages = [PDFPage(page_number=1, text="Text", lines=["Text"])]

        result = PDFExtractionResult(
            pages=pages,
            total_pages=1,
            text="Text",
            is_scanned=False,
            extraction_method="pymupdf",
            warnings=[],
        )

        assert result.total_pages == 1
        assert result.extraction_method == "pymupdf"
        assert result.is_scanned is False
        assert len(result.warnings) == 0

    def test_extraction_result_with_warnings(self):
        """Test PDFExtractionResult with warnings."""
        result = PDFExtractionResult(
            pages=[],
            total_pages=0,
            text="",
            is_scanned=False,
            extraction_method="none",
            warnings=["Warning 1", "Warning 2"],
        )

        assert len(result.warnings) == 2
        assert "Warning 1" in result.warnings
