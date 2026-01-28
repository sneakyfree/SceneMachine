"""Character Laboratory API routes.

Provides endpoints for character face embedding, voice cloning,
and reference image generation.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, Body
from pydantic import BaseModel, Field

from scenemachine.services.face_embedding import (
    FaceEmbeddingService,
    get_face_embedding_service,
)
from scenemachine.services.voice_cloning import (
    VoiceCloningService,
    VoiceGender,
    get_voice_cloning_service,
)
from scenemachine.services.character_image_generator import (
    CharacterImageGenerator,
    CharacterImageRequest,
    ImageStyle,
    get_character_image_generator,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/character-lab", tags=["character-lab"])


# --- Request/Response Models ---

class ExtractEmbeddingResponse(BaseModel):
    """Response from face embedding extraction."""
    success: bool
    face_count: int = 0
    faces: List[Dict[str, Any]] = []
    has_primary_embedding: bool = False
    embedding_path: Optional[str] = None
    error: Optional[str] = None


class VoiceListResponse(BaseModel):
    """Response with available voices."""
    voices: List[Dict[str, Any]]
    total: int


class VoiceSuggestRequest(BaseModel):
    """Request to suggest voices for a character."""
    character_name: str
    gender: Optional[str] = None
    age_range: Optional[List[int]] = None
    personality_traits: Optional[List[str]] = None


class GenerateSpeechRequest(BaseModel):
    """Request to generate speech."""
    text: str
    voice_id: str = "am_adam"
    emotion: str = "neutral"
    speed: float = 1.0


class GenerateSpeechResponse(BaseModel):
    """Response from speech generation."""
    success: bool
    audio_path: Optional[str] = None
    duration_seconds: float = 0.0
    sample_rate: int = 24000
    error: Optional[str] = None


class GenerateImagesRequest(BaseModel):
    """Request to generate character reference images."""
    character_name: str
    description: str = ""
    physical_description: Optional[Dict[str, Any]] = None
    gender: Optional[str] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    style: str = "cinematic"
    num_images: int = 4
    width: int = 1024
    height: int = 1024
    seed: Optional[int] = None


class GenerateImagesResponse(BaseModel):
    """Response from image generation."""
    success: bool
    images: List[Dict[str, Any]] = []
    total_generated: int = 0
    estimated_cost: float = 0.0
    error: Optional[str] = None


# --- Face Embedding Endpoints ---

@router.post("/face/extract", response_model=ExtractEmbeddingResponse)
async def extract_face_embedding(
    file: UploadFile = File(...),
    save_embedding: bool = True,
):
    """Extract face embedding from uploaded image.
    
    Returns face detection results with bounding boxes,
    and optionally saves the embedding for later use.
    """
    try:
        # Save uploaded file temporarily
        content = await file.read()
        
        service = get_face_embedding_service()
        result = service.extract_embedding_from_bytes(content)
        
        embedding_path = None
        if save_embedding and result.success and result.primary_embedding is not None:
            # Save embedding to temp location
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".npy", delete=False) as tmp:
                service.save_embedding(result.primary_embedding, tmp.name)
                embedding_path = tmp.name
        
        return ExtractEmbeddingResponse(
            success=result.success,
            face_count=len(result.faces),
            faces=result.to_dict()["faces"],
            has_primary_embedding=result.primary_embedding is not None,
            embedding_path=embedding_path,
            error=result.error,
        )
        
    except Exception as e:
        logger.exception(f"Error extracting face embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/face/compare")
async def compare_faces(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
):
    """Compare two face images for similarity.
    
    Returns whether they appear to be the same person
    and the similarity score.
    """
    try:
        service = get_face_embedding_service()
        
        content1 = await file1.read()
        content2 = await file2.read()
        
        result1 = service.extract_embedding_from_bytes(content1)
        result2 = service.extract_embedding_from_bytes(content2)
        
        if not result1.success or result1.primary_embedding is None:
            return {"success": False, "error": "No face found in first image"}
        
        if not result2.success or result2.primary_embedding is None:
            return {"success": False, "error": "No face found in second image"}
        
        is_same, similarity = service.is_same_person(
            result1.primary_embedding,
            result2.primary_embedding,
        )
        
        return {
            "success": True,
            "is_same_person": is_same,
            "similarity_score": similarity,
            "threshold": service.SIMILARITY_THRESHOLD,
        }
        
    except Exception as e:
        logger.exception(f"Error comparing faces: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Voice Endpoints ---

@router.get("/voice/list", response_model=VoiceListResponse)
async def list_voices(
    gender: Optional[str] = None,
    age_category: Optional[str] = None,
):
    """List available TTS voices.
    
    Can filter by gender (male/female/neutral) and
    age category (child/teen/adult/senior).
    """
    service = get_voice_cloning_service()
    
    voice_gender = VoiceGender(gender) if gender else None
    
    voices = service.get_available_voices(
        gender=voice_gender,
        age_category=age_category,
    )
    
    return VoiceListResponse(
        voices=[v.to_dict() for v in voices],
        total=len(voices),
    )


@router.post("/voice/suggest")
async def suggest_voices(request: VoiceSuggestRequest):
    """Suggest best voices for a character.
    
    Uses character description to rank compatible voices.
    """
    service = get_voice_cloning_service()
    
    voice_gender = None
    if request.gender:
        try:
            voice_gender = VoiceGender(request.gender.lower())
        except ValueError:
            pass
    
    age_range = None
    if request.age_range and len(request.age_range) == 2:
        age_range = tuple(request.age_range)
    
    suggestions = service.suggest_voice(
        character_name=request.character_name,
        gender=voice_gender,
        age_range=age_range,
        personality_traits=request.personality_traits,
    )
    
    return {
        "character_name": request.character_name,
        "suggestions": [v.to_dict() for v in suggestions],
        "total": len(suggestions),
    }


@router.post("/voice/clone")
async def clone_voice(
    name: str = Body(...),
    file: UploadFile = File(...),
):
    """Clone a voice from an audio sample.
    
    Requires 3-10 seconds of clear speech audio.
    """
    try:
        # Save uploaded file
        content = await file.read()
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        service = get_voice_cloning_service()
        profile = service.clone_voice(tmp_path, name)
        
        if profile:
            return {
                "success": True,
                "voice": profile.to_dict(),
            }
        else:
            return {
                "success": False,
                "error": "Failed to clone voice",
            }
            
    except Exception as e:
        logger.exception(f"Error cloning voice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice/generate", response_model=GenerateSpeechResponse)
async def generate_speech(request: GenerateSpeechRequest):
    """Generate speech from text using specified voice.
    
    Supports emotion modifiers: neutral, happy, sad, angry, whisper.
    """
    try:
        service = get_voice_cloning_service()
        
        result = service.generate_speech(
            text=request.text,
            voice_id=request.voice_id,
            emotion=request.emotion,
            speed=request.speed,
        )
        
        return GenerateSpeechResponse(
            success=result.success,
            audio_path=result.audio_path,
            duration_seconds=result.duration_seconds,
            sample_rate=result.sample_rate,
            error=result.error,
        )
        
    except Exception as e:
        logger.exception(f"Error generating speech: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Image Generation Endpoints ---

@router.post("/image/generate", response_model=GenerateImagesResponse)
async def generate_character_images(request: GenerateImagesRequest):
    """Generate character reference images.
    
    Creates multiple candidates based on description.
    Uses Flux Schnell via fal.ai or Replicate.
    """
    try:
        generator = get_character_image_generator()
        
        # Convert style string to enum
        try:
            style = ImageStyle(request.style.lower())
        except ValueError:
            style = ImageStyle.CINEMATIC
        
        # Build age range
        age_range = None
        if request.age_min is not None and request.age_max is not None:
            age_range = (request.age_min, request.age_max)
        
        img_request = CharacterImageRequest(
            character_name=request.character_name,
            description=request.description,
            physical_description=request.physical_description,
            gender=request.gender,
            age_range=age_range,
            style=style,
            num_images=request.num_images,
            width=request.width,
            height=request.height,
            seed=request.seed,
        )
        
        results = await generator.generate_character_images(img_request)
        
        successful = [r for r in results if r.success]
        total_cost = sum(r.cost_credits for r in results)
        
        return GenerateImagesResponse(
            success=len(successful) > 0,
            images=[r.to_dict() for r in results],
            total_generated=len(successful),
            estimated_cost=total_cost,
        )
        
    except Exception as e:
        logger.exception(f"Error generating images: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image/estimate-cost")
async def estimate_image_cost(
    num_images: int = 4,
    provider: Optional[str] = None,
):
    """Estimate cost for image generation.
    
    Returns cost breakdown per image and total.
    """
    generator = get_character_image_generator()
    
    # Convert provider string if provided
    from scenemachine.services.character_image_generator import ImageProvider
    img_provider = None
    if provider:
        try:
            img_provider = ImageProvider(provider.lower())
        except ValueError:
            pass
    
    estimate = generator.estimate_cost(num_images, img_provider)
    
    return estimate


@router.get("/capabilities")
async def get_capabilities():
    """Get Character Lab capabilities and status.
    
    Returns which features are available based on
    installed dependencies.
    """
    capabilities = {
        "face_embedding": {
            "available": False,
            "provider": "InsightFace",
            "description": "Face detection and embedding extraction",
        },
        "voice_cloning": {
            "available": True,
            "provider": "Kokoro TTS",
            "voices_count": 20,
            "description": "Text-to-speech with voice cloning",
        },
        "image_generation": {
            "available": True,
            "providers": ["fal.ai", "replicate", "local"],
            "description": "Character reference image generation",
        },
    }
    
    # Check InsightFace availability
    try:
        import insightface
        capabilities["face_embedding"]["available"] = True
    except ImportError:
        pass
    
    # Check Kokoro availability
    try:
        import kokoro
        capabilities["voice_cloning"]["native"] = True
    except ImportError:
        capabilities["voice_cloning"]["native"] = False
        capabilities["voice_cloning"]["fallback"] = "mock"
    
    return capabilities
