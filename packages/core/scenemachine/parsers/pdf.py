"""PDF screenplay parser.

Extracts text from PDF screenplays and converts to structured format.
Supports both digital PDFs and scanned documents (via OCR).
"""

import io
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PDFPage:
    """Extracted content from a PDF page."""

    page_number: int
    text: str
    lines: List[str]
    is_ocr: bool = False


@dataclass
class PDFExtractionResult:
    """Result of PDF text extraction."""

    pages: List[PDFPage]
    total_pages: int
    text: str
    is_scanned: bool
    extraction_method: str
    warnings: List[str]


class PDFParser:
    """Parser for PDF screenplay files.

    Extracts text from PDFs and attempts to parse screenplay structure.
    Falls back to OCR for scanned documents.
    """

    # Screenplay formatting patterns
    SCENE_HEADING_PATTERN = re.compile(
        r"^\s*(INT\.?|EXT\.?|INT\.?/EXT\.?|I/E\.?)\s+.+",
        re.IGNORECASE,
    )

    CHARACTER_PATTERN = re.compile(r"^\s{20,}([A-Z][A-Z\s\-\'\.]+)\s*$")

    DIALOGUE_INDENT_PATTERN = re.compile(r"^\s{10,25}\S")

    TRANSITION_PATTERN = re.compile(r"^\s*[A-Z\s]+TO:\s*$")

    PAGE_NUMBER_PATTERN = re.compile(r"^\s*\d+\.?\s*$")

    def __init__(self, use_ocr: bool = True) -> None:
        """Initialize PDF parser.

        Args:
            use_ocr: Whether to use OCR for scanned documents
        """
        self.use_ocr = use_ocr
        self._fitz_available = self._check_fitz()
        self._tesseract_available = self._check_tesseract() if use_ocr else False

    def _check_fitz(self) -> bool:
        """Check if PyMuPDF is available."""
        try:
            import fitz  # noqa: F401

            return True
        except ImportError:
            logger.warning("PyMuPDF (fitz) not installed. PDF parsing limited.")
            return False

    def _check_tesseract(self) -> bool:
        """Check if Tesseract OCR is available."""
        try:
            import pytesseract  # noqa: F401

            # Try to get version to verify tesseract is installed
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            logger.warning("Tesseract OCR not available. Scanned PDFs not supported.")
            return False

    def parse(self, file_path: Path | str) -> Dict[str, Any]:
        """Parse a PDF screenplay file.

        Args:
            file_path: Path to PDF file

        Returns:
            Dictionary with extracted screenplay content
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        # Extract text from PDF
        extraction = self._extract_text(file_path)

        # Parse extracted text into screenplay structure
        parsed = self._parse_text(extraction.text)

        return {
            "raw_text": extraction.text,
            "pages": [
                {
                    "page_number": p.page_number,
                    "text": p.text,
                    "is_ocr": p.is_ocr,
                }
                for p in extraction.pages
            ],
            "total_pages": extraction.total_pages,
            "is_scanned": extraction.is_scanned,
            "extraction_method": extraction.extraction_method,
            "warnings": extraction.warnings,
            **parsed,
        }

    def parse_bytes(self, data: bytes, filename: str = "screenplay.pdf") -> Dict[str, Any]:
        """Parse PDF from bytes.

        Args:
            data: PDF file bytes
            filename: Optional filename for context

        Returns:
            Dictionary with extracted screenplay content
        """
        extraction = self._extract_text_from_bytes(data)
        parsed = self._parse_text(extraction.text)

        return {
            "raw_text": extraction.text,
            "pages": [
                {
                    "page_number": p.page_number,
                    "text": p.text,
                    "is_ocr": p.is_ocr,
                }
                for p in extraction.pages
            ],
            "total_pages": extraction.total_pages,
            "is_scanned": extraction.is_scanned,
            "extraction_method": extraction.extraction_method,
            "warnings": extraction.warnings,
            **parsed,
        }

    def _extract_text(self, file_path: Path) -> PDFExtractionResult:
        """Extract text from PDF file."""
        with open(file_path, "rb") as f:
            return self._extract_text_from_bytes(f.read())

    def _extract_text_from_bytes(self, data: bytes) -> PDFExtractionResult:
        """Extract text from PDF bytes."""
        if not self._fitz_available:
            return self._fallback_extraction(data)

        import fitz

        pages: List[PDFPage] = []
        warnings: List[str] = []
        is_scanned = False

        try:
            doc = fitz.open(stream=data, filetype="pdf")

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()

                # Check if page has meaningful text
                if len(text.strip()) < 50:
                    # Might be scanned - try OCR
                    if self.use_ocr and self._tesseract_available:
                        ocr_text = self._ocr_page(page)
                        if ocr_text:
                            pages.append(
                                PDFPage(
                                    page_number=page_num + 1,
                                    text=ocr_text,
                                    lines=ocr_text.split("\n"),
                                    is_ocr=True,
                                )
                            )
                            is_scanned = True
                            continue

                pages.append(
                    PDFPage(
                        page_number=page_num + 1,
                        text=text,
                        lines=text.split("\n"),
                        is_ocr=False,
                    )
                )

            doc.close()

        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            warnings.append(f"Extraction error: {str(e)}")

        # Combine all pages
        full_text = "\n\n".join(p.text for p in pages)

        return PDFExtractionResult(
            pages=pages,
            total_pages=len(pages),
            text=full_text,
            is_scanned=is_scanned,
            extraction_method="pymupdf" + ("+ocr" if is_scanned else ""),
            warnings=warnings,
        )

    def _ocr_page(self, page: Any) -> Optional[str]:
        """OCR a single PDF page.

        Args:
            page: PyMuPDF page object

        Returns:
            Extracted text or None
        """
        try:
            import pytesseract
            from PIL import Image

            # Render page to image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))

            # Run OCR
            text = pytesseract.image_to_string(img, lang="eng")
            return text

        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return None

    def _fallback_extraction(self, data: bytes) -> PDFExtractionResult:
        """Fallback text extraction without PyMuPDF."""
        # Try pdfplumber as fallback
        try:
            import pdfplumber

            pages: List[PDFPage] = []

            with pdfplumber.open(io.BytesIO(data)) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    pages.append(
                        PDFPage(
                            page_number=i + 1,
                            text=text,
                            lines=text.split("\n"),
                        )
                    )

            full_text = "\n\n".join(p.text for p in pages)

            return PDFExtractionResult(
                pages=pages,
                total_pages=len(pages),
                text=full_text,
                is_scanned=False,
                extraction_method="pdfplumber",
                warnings=[],
            )

        except ImportError:
            return PDFExtractionResult(
                pages=[],
                total_pages=0,
                text="",
                is_scanned=False,
                extraction_method="none",
                warnings=["No PDF library available. Install pymupdf or pdfplumber."],
            )

    def _parse_text(self, text: str) -> Dict[str, Any]:
        """Parse extracted text into screenplay structure.

        This is a heuristic-based parser that attempts to identify
        screenplay elements based on formatting patterns.
        """
        lines = text.split("\n")
        elements: List[Dict[str, Any]] = []
        characters: set[str] = set()
        scenes: List[Dict[str, Any]] = []

        current_scene: Optional[Dict[str, Any]] = None
        scene_count = 0
        line_number = 0

        i = 0
        while i < len(lines):
            line = lines[i]
            line_number += 1
            stripped = line.strip()

            # Skip empty lines and page numbers
            if not stripped or self.PAGE_NUMBER_PATTERN.match(stripped):
                i += 1
                continue

            # Scene heading
            if self.SCENE_HEADING_PATTERN.match(stripped):
                # Save previous scene
                if current_scene:
                    scenes.append(current_scene)

                scene_count += 1
                scene_info = self._parse_scene_heading(stripped)

                current_scene = {
                    "number": str(scene_count),
                    "sequence": scene_count,
                    "type": scene_info["type"],
                    "location": scene_info["location"],
                    "time_of_day": scene_info["time_of_day"],
                    "heading": stripped,
                    "line_number": line_number,
                    "elements": [],
                    "characters": [],
                    "dialogue_count": 0,
                    "action_lines": [],
                }

                elements.append(
                    {
                        "type": "scene_heading",
                        "text": stripped,
                        "line_number": line_number,
                    }
                )

            # Transition
            elif self.TRANSITION_PATTERN.match(stripped):
                elements.append(
                    {
                        "type": "transition",
                        "text": stripped,
                        "line_number": line_number,
                    }
                )

            # Character (centered, all caps)
            elif self._is_character_line(line, lines, i):
                char_name = stripped.split("(")[0].strip()
                characters.add(char_name)

                elements.append(
                    {
                        "type": "character",
                        "text": stripped,
                        "name": char_name,
                        "line_number": line_number,
                    }
                )

                if current_scene:
                    if char_name not in current_scene["characters"]:
                        current_scene["characters"].append(char_name)

                # Look for dialogue
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    next_stripped = next_line.strip()

                    if not next_stripped:
                        break

                    if self._is_dialogue_line(next_line):
                        line_number += 1
                        elements.append(
                            {
                                "type": "dialogue",
                                "text": next_stripped,
                                "line_number": line_number,
                            }
                        )
                        if current_scene:
                            current_scene["dialogue_count"] += 1
                        i += 1
                    elif next_stripped.startswith("(") and next_stripped.endswith(")"):
                        line_number += 1
                        elements.append(
                            {
                                "type": "parenthetical",
                                "text": next_stripped[1:-1],
                                "line_number": line_number,
                            }
                        )
                        i += 1
                    else:
                        break

                continue

            # Action (default)
            else:
                elements.append(
                    {
                        "type": "action",
                        "text": stripped,
                        "line_number": line_number,
                    }
                )

                if current_scene:
                    current_scene["action_lines"].append(stripped)

            i += 1

        # Don't forget the last scene
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

    def _parse_scene_heading(self, text: str) -> Dict[str, str]:
        """Parse scene heading into components."""
        result = {"type": "", "location": "", "time_of_day": ""}

        # Match scene type
        match = re.match(
            r"^\s*(INT\.?|EXT\.?|INT\.?/EXT\.?|I/E\.?)\s*\.?\s*",
            text,
            re.IGNORECASE,
        )

        if match:
            result["type"] = match.group(1).upper().rstrip(".")
            rest = text[match.end() :].strip()

            # Split by dash for time of day
            if " - " in rest:
                parts = rest.rsplit(" - ", 1)
                result["location"] = parts[0].strip()
                result["time_of_day"] = parts[1].strip() if len(parts) > 1 else ""
            else:
                result["location"] = rest

        return result

    def _is_character_line(
        self, line: str, all_lines: List[str], index: int
    ) -> bool:
        """Determine if a line is a character cue."""
        stripped = line.strip()

        # Must be uppercase (allowing some punctuation)
        if not re.match(r"^[A-Z][A-Z\s\-\'\.0-9\(\)]+$", stripped):
            return False

        # Should be indented (centered)
        leading_spaces = len(line) - len(line.lstrip())
        if leading_spaces < 15:
            return False

        # Should be followed by dialogue
        if index + 1 < len(all_lines):
            next_line = all_lines[index + 1]
            if next_line.strip() and self._is_dialogue_line(next_line):
                return True

        return False

    def _is_dialogue_line(self, line: str) -> bool:
        """Determine if a line is dialogue."""
        if not line.strip():
            return False

        # Dialogue is typically indented but not as much as character
        leading_spaces = len(line) - len(line.lstrip())
        return 10 <= leading_spaces <= 30


def parse_pdf(file_path: Path | str) -> Dict[str, Any]:
    """Convenience function to parse a PDF screenplay.

    Args:
        file_path: Path to PDF file

    Returns:
        Dictionary with parsed screenplay data
    """
    parser = PDFParser()
    return parser.parse(file_path)
