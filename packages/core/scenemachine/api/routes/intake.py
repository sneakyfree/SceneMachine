"""Screenplay intake and analysis API routes.

Implements the DNA strand master plan's TurboTax-style intake wizard backend.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from scenemachine.parsers import FDXParser, FountainParser, PDFParser
from scenemachine.services.blockers_engine import BlockersEngine
from scenemachine.services.shot_list_generator import ShotListGenerator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intake", tags=["intake"])


# --- Request/Response Models ---

class ParseScreenplayRequest(BaseModel):
    """Request to parse screenplay text directly."""
    content: str = Field(..., description="Raw screenplay text content")
    format: str = Field("fountain", description="Format: fountain, txt")


class ParseScreenplayResponse(BaseModel):
    """Response from screenplay parsing."""
    success: bool
    title: str | None = None
    author: str | None = None
    scenes: list[dict[str, Any]] = []
    characters: list[str] = []
    warnings: list[str] = []
    metadata: dict[str, Any] = {}


class GenerateShotListRequest(BaseModel):
    """Request to generate shot list from parsed screenplay."""
    parsed_screenplay: dict[str, Any]


class GenerateShotListResponse(BaseModel):
    """Response from shot list generation."""
    success: bool
    title: str | None = None
    scenes: list[dict[str, Any]] = []
    characters: list[dict[str, Any]] = []
    contradictions: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    warnings: list[str] = []


class AnalyzeBlockersRequest(BaseModel):
    """Request to analyze blockers."""
    characters: list[dict[str, Any]] = []
    scenes: list[dict[str, Any]] = []
    shots: list[dict[str, Any]] = []
    settings: dict[str, Any] | None = None


class AnalyzeBlockersResponse(BaseModel):
    """Response from blocker analysis."""
    success: bool
    blockers: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    can_proceed: bool = True


# --- Endpoints ---

@router.post("/parse/text", response_model=ParseScreenplayResponse)
async def parse_screenplay_text(request: ParseScreenplayRequest):
    """Parse screenplay from text content.

    Supports Fountain and plain text formats.
    """
    try:
        if request.format.lower() == "fountain":
            parser = FountainParser()
            result = parser.parse(request.content)
        else:
            # Treat as plain text, attempt Fountain parsing
            parser = FountainParser()
            result = parser.parse(request.content)

        return ParseScreenplayResponse(
            success=True,
            title=result.get("title_page", {}).get("title") if isinstance(result.get("title_page"), dict) else None,
            author=result.get("title_page", {}).get("author") if isinstance(result.get("title_page"), dict) else None,
            scenes=result.get("scenes", []),
            characters=result.get("characters", []),
            warnings=result.get("warnings", []),
            metadata=result.get("metadata", {}),
        )

    except Exception as e:
        logger.exception(f"Error parsing screenplay: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/parse/file", response_model=ParseScreenplayResponse)
async def parse_screenplay_file(
    file: UploadFile = File(...),
):
    """Parse screenplay from uploaded file.

    Supports .fountain, .fdx, .pdf, and .txt files.
    """
    filename = file.filename or "screenplay.txt"
    suffix = Path(filename).suffix.lower()

    try:
        content = await file.read()

        if suffix in (".fountain", ".txt"):
            text = content.decode("utf-8")
            parser = FountainParser()
            result = parser.parse(text)

        elif suffix == ".fdx":
            parser = FDXParser()
            result = parser.parse_bytes(content, filename)

        elif suffix == ".pdf":
            # Save to temp file for PDF parser
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            try:
                parser = PDFParser()
                result = parser.parse(tmp_path)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {suffix}. Supported: .fountain, .fdx, .pdf, .txt"
            )

        return ParseScreenplayResponse(
            success=True,
            title=result.get("title") or (result.get("title_page", {}).get("title") if isinstance(result.get("title_page"), dict) else None),
            author=result.get("author") or (result.get("title_page", {}).get("author") if isinstance(result.get("title_page"), dict) else None),
            scenes=result.get("scenes", []),
            characters=result.get("characters", []),
            warnings=result.get("warnings", []),
            metadata=result.get("metadata", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error parsing file {filename}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/shot-list", response_model=GenerateShotListResponse)
async def generate_shot_list(request: GenerateShotListRequest):
    """Generate shot list from parsed screenplay.

    Creates detailed shot breakdown with:
    - Visual prompts for video generation
    - Camera angles and movements
    - Dialogue extraction
    - Duration estimates
    - Confidence scores
    - Contradiction detection
    """
    try:
        generator = ShotListGenerator()
        result = generator.generate(request.parsed_screenplay)

        return GenerateShotListResponse(
            success=True,
            title=result.get("title"),
            scenes=result.get("scenes", []),
            characters=result.get("characters", []),
            contradictions=result.get("contradictions", []),
            summary=result.get("summary", {}),
            warnings=result.get("warnings", []),
        )

    except Exception as e:
        logger.exception(f"Error generating shot list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-blockers", response_model=AnalyzeBlockersResponse)
async def analyze_blockers(request: AnalyzeBlockersRequest):
    """Analyze project for blockers.

    Returns prioritized list of issues that:
    - Block generation (critical)
    - Risk quality (high/medium)
    - Need polish (low)

    Each blocker includes an "unlocker" - suggested fix with effort/impact.
    """
    try:
        engine = BlockersEngine()
        result = engine.analyze_project(
            characters=request.characters,
            scenes=request.scenes,
            shots=request.shots,
            settings=request.settings,
        )

        return AnalyzeBlockersResponse(
            success=True,
            blockers=result.get("blockers", []),
            summary=result.get("summary", {}),
            can_proceed=result.get("summary", {}).get("can_proceed", True),
        )

    except Exception as e:
        logger.exception(f"Error analyzing blockers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported screenplay formats."""
    return {
        "formats": [
            {
                "extension": ".fountain",
                "name": "Fountain",
                "description": "Plain text screenplay format",
                "docs": "https://fountain.io/syntax",
            },
            {
                "extension": ".fdx",
                "name": "Final Draft",
                "description": "Industry standard XML format",
                "docs": "https://www.finaldraft.com/",
            },
            {
                "extension": ".pdf",
                "name": "PDF",
                "description": "Attempts OCR if scanned",
                "docs": None,
            },
            {
                "extension": ".txt",
                "name": "Plain Text",
                "description": "Attempts Fountain parsing",
                "docs": None,
            },
        ]
    }
