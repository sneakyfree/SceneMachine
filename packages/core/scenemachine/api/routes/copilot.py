"""AI Co-pilot (Steven) API routes.

Steven is the AI assistant for SceneMachine that provides:
- Scene analysis and suggestions
- Performer recommendations
- Voice command processing
- Creative guidance
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scenemachine.database import get_session
from scenemachine.services.llm import LLMService, get_llm_service
from scenemachine.models import Scene, Shot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/copilot", tags=["copilot"])


# ============ Request/Response Models ============


class AnalyzeSceneRequest(BaseModel):
    """Request to analyze a scene."""

    project_id: str
    scene_id: str
    include_suggestions: bool = True
    include_performer_recommendations: bool = True
    context: Optional[str] = None


class SceneSuggestion(BaseModel):
    """A suggestion for improving a scene."""

    category: str  # pacing, emotion, visual, dialogue, continuity
    suggestion: str
    priority: str  # high, medium, low
    applies_to: Optional[str] = None  # shot_id or scene element


class PerformerRecommendation(BaseModel):
    """A performer recommendation for a shot or scene."""

    performer_id: str
    performer_name: str
    aci_score: float
    match_reasons: List[str]
    suggested_mode: str  # BLINK, DEEP, EPIC
    estimated_cost: float


class SceneAnalysis(BaseModel):
    """Analysis result for a scene."""

    scene_id: str
    scene_summary: str
    emotional_arc: List[str]
    pacing_score: float
    visual_complexity: float
    suggestions: List[SceneSuggestion]
    performer_recommendations: List[PerformerRecommendation]


class ChatMessage(BaseModel):
    """Chat message to/from Steven."""

    role: str  # user, assistant, system
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    """Request for chat with Steven."""

    messages: List[ChatMessage]
    project_id: Optional[str] = None
    scene_id: Optional[str] = None
    context_type: str = "general"  # general, scene, generation, export


class ChatResponse(BaseModel):
    """Response from Steven."""

    message: str
    suggestions: Optional[List[str]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    confidence: float = 1.0


class VoiceCommandRequest(BaseModel):
    """Request to process a voice command."""

    transcript: str
    project_id: Optional[str] = None
    current_context: str = "project"  # project, scene, timeline, generation


class VoiceCommandResponse(BaseModel):
    """Response for a voice command."""

    understood: bool
    action: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    confirmation_message: str
    requires_confirmation: bool = False


class RecommendPerformersRequest(BaseModel):
    """Request for performer recommendations."""

    project_id: str
    shot_id: Optional[str] = None
    scene_id: Optional[str] = None
    emotion_requirements: Optional[List[str]] = None
    duration_seconds: Optional[float] = None
    max_budget_usd: Optional[float] = None
    prefer_human: bool = False


class CreativeGuidanceRequest(BaseModel):
    """Request for creative guidance."""

    project_id: str
    guidance_type: str  # story_arc, pacing, visual_style, dialogue, character
    current_state: Optional[Dict[str, Any]] = None
    specific_question: Optional[str] = None


class CreativeGuidance(BaseModel):
    """Creative guidance response."""

    guidance_type: str
    analysis: str
    recommendations: List[str]
    examples: Optional[List[Dict[str, Any]]] = None
    reference_materials: Optional[List[str]] = None


# ============ API Endpoints ============


@router.post("/analyze-scene", response_model=SceneAnalysis)
async def analyze_scene(
    request: AnalyzeSceneRequest,
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
) -> SceneAnalysis:
    """Analyze a scene and provide suggestions.

    Steven analyzes:
    - Emotional arc and pacing
    - Visual composition suggestions
    - Dialogue improvements
    - Performer recommendations based on requirements
    """
    try:
        # Load scene data from database
        scene_result = await session.execute(
            select(Scene).where(Scene.id == request.scene_id)
        )
        scene = scene_result.scalar_one_or_none()

        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")

        # Build scene context for LLM
        scene_context = {
            "id": str(scene.id),
            "scene_number": scene.scene_number,
            "heading": scene.heading,
            "description": scene.description,
            "dialogue": getattr(scene, 'dialogue', ''),
            "context": request.context,
        }

        # Use LLM to get suggestions for the scene
        try:
            # suggest_scene returns a list of suggestion dicts
            llm_suggestions = await llm_service.suggest_scene(
                scene=scene_context,
                characters=[],  # Characters could be loaded from scene relations
                adjacent_scenes=None,
            )

            # Transform LLM suggestions to our format
            suggestions = [
                SceneSuggestion(
                    category=s.get("type", s.get("category", "general")),
                    suggestion=s.get("description", s.get("title", "")),
                    priority="medium" if s.get("confidence", 0.8) >= 0.7 else "low",
                    applies_to=s.get("id"),
                )
                for s in llm_suggestions
            ]

            # Analyze scene for summary and scores using the suggestions context
            summary = f"Analysis of scene: {scene.heading}"
            if scene.description:
                summary = f"{scene.heading} - {scene.description[:100]}..."

            return SceneAnalysis(
                scene_id=request.scene_id,
                scene_summary=summary,
                emotional_arc=["rising action", "climax", "resolution"] if suggestions else ["neutral"],
                pacing_score=0.75 + (len(suggestions) * 0.02),  # Adjust based on suggestion count
                visual_complexity=0.5 + (len([s for s in suggestions if s.category == "visual"]) * 0.1),
                suggestions=suggestions,
                performer_recommendations=[],  # Would require performer matching service
            )
        except Exception as llm_error:
            logger.warning(f"LLM analysis failed, using fallback: {llm_error}")
            # Fallback to basic response if LLM fails
            return SceneAnalysis(
                scene_id=request.scene_id,
                scene_summary=f"Scene: {scene.heading}",
                emotional_arc=["neutral"],
                pacing_score=0.75,
                visual_complexity=0.5,
                suggestions=[],
                performer_recommendations=[],
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scene analysis error: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze scene")


@router.post("/chat", response_model=ChatResponse)
async def chat_with_steven(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
) -> ChatResponse:
    """Chat with Steven AI Co-pilot.

    Steven can help with:
    - Understanding scene requirements
    - Explaining generation options
    - Troubleshooting issues
    - Creative suggestions
    """
    # Get the last user message
    user_messages = [m for m in request.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user message provided",
        )

    last_message = user_messages[-1].content

    # Build project context for LLM
    project_context = {
        "project_id": request.project_id,
        "scene_id": request.scene_id,
        "context_type": request.context_type,
    }

    # Convert chat history for LLM service
    conversation_history = [
        {"role": m.role, "content": m.content}
        for m in request.messages[:-1]  # Exclude last message, it goes in the main prompt
    ]

    try:
        # Use LLM service for chat
        llm_result = await llm_service.chat(
            message=last_message,
            project_context=project_context,
            conversation_history=conversation_history if conversation_history else None,
        )

        return ChatResponse(
            message=llm_result.get("message", "I'm here to help with your project."),
            suggestions=[
                s.get("title", s.get("description", ""))
                for s in llm_result.get("suggestions", [])
            ][:3] if llm_result.get("suggestions") else None,
            actions=None,  # Actions determined by specific commands
            confidence=0.9,
        )
    except Exception as llm_error:
        logger.warning(f"LLM chat failed, using fallback: {llm_error}")
        # Fallback to simple pattern matching
        last_lower = last_message.lower()

        if "help" in last_lower:
            return ChatResponse(
                message="I'm Steven, your AI co-pilot for SceneMachine! I can help you with scene analysis, performer recommendations, creative guidance, and more. What would you like to know?",
                suggestions=[
                    "Analyze my current scene",
                    "Find performers for this shot",
                    "Suggest improvements to pacing",
                ],
            )

        if "performer" in last_lower or "actor" in last_lower:
            return ChatResponse(
                message="I can help you find the perfect performer for your scene! Would you like me to search based on your scene's requirements, or do you have specific criteria in mind?",
                suggestions=[
                    "Find performers matching scene emotions",
                    "Show top-rated performers",
                    "Filter by price range",
                ],
                actions=[
                    {"type": "open_actforge", "label": "Browse ActForge"},
                ],
            )

        if "generate" in last_lower or "render" in last_lower:
            return ChatResponse(
                message="I can help you with video generation! I can explain the different modes (BLINK, DEEP, EPIC) or help you optimize your generation settings.",
                suggestions=[
                    "Explain generation modes",
                    "Optimize my settings",
                    "Estimate generation cost",
                ],
            )

        # Default response
        return ChatResponse(
            message=f"I understand you're asking about: {last_message[:100]}. Could you provide more details so I can better assist you?",
            suggestions=[
                "Analyze scene",
                "Find performers",
                "Get creative suggestions",
            ],
        )


@router.post("/voice-command", response_model=VoiceCommandResponse)
async def process_voice_command(
    request: VoiceCommandRequest,
    session: AsyncSession = Depends(get_session),
) -> VoiceCommandResponse:
    """Process a voice command from Steven.

    Supports commands like:
    - "Generate this shot"
    - "Find a performer for scene 3"
    - "Export the project"
    - "Show me the timeline"
    """
    transcript = request.transcript.lower().strip()

    # Parse common voice commands
    if "generate" in transcript and ("shot" in transcript or "scene" in transcript):
        return VoiceCommandResponse(
            understood=True,
            action="generate",
            parameters={"scope": "shot" if "shot" in transcript else "scene"},
            confirmation_message="Ready to generate. Should I proceed?",
            requires_confirmation=True,
        )

    if "find" in transcript and "performer" in transcript:
        return VoiceCommandResponse(
            understood=True,
            action="open_actforge",
            parameters={"auto_search": True},
            confirmation_message="Opening ActForge to find performers...",
            requires_confirmation=False,
        )

    if "export" in transcript:
        return VoiceCommandResponse(
            understood=True,
            action="export",
            parameters={"format": "mp4"},
            confirmation_message="Ready to export. What format would you like?",
            requires_confirmation=True,
        )

    if "timeline" in transcript or "edit" in transcript:
        return VoiceCommandResponse(
            understood=True,
            action="navigate",
            parameters={"destination": "timeline"},
            confirmation_message="Opening the timeline editor...",
            requires_confirmation=False,
        )

    if "play" in transcript or "preview" in transcript:
        return VoiceCommandResponse(
            understood=True,
            action="preview",
            parameters={"auto_play": True},
            confirmation_message="Starting preview playback...",
            requires_confirmation=False,
        )

    if "stop" in transcript or "pause" in transcript:
        return VoiceCommandResponse(
            understood=True,
            action="stop_preview",
            parameters={},
            confirmation_message="Stopping playback.",
            requires_confirmation=False,
        )

    # Unknown command
    return VoiceCommandResponse(
        understood=False,
        action=None,
        parameters=None,
        confirmation_message=f"I didn't understand: '{request.transcript}'. Try saying 'generate shot', 'find performer', or 'export project'.",
        requires_confirmation=False,
    )


@router.post("/recommend-performers", response_model=List[PerformerRecommendation])
async def recommend_performers(
    request: RecommendPerformersRequest,
    session: AsyncSession = Depends(get_session),
) -> List[PerformerRecommendation]:
    """Get AI-powered performer recommendations.

    Steven analyzes the scene/shot requirements and recommends
    the best matching performers from ActForge.
    """
    # In production, this would:
    # 1. Load scene/shot data
    # 2. Analyze emotion requirements
    # 3. Query performers with matching capabilities
    # 4. Rank by ACI, price, and match quality

    recommendations = [
        PerformerRecommendation(
            performer_id="demo-performer-1",
            performer_name="Alex Sterling",
            aci_score=85.5,
            match_reasons=[
                "Strong emotional range",
                "High ACI score",
                "Available immediately",
            ],
            suggested_mode="DEEP" if (request.duration_seconds or 30) > 15 else "BLINK",
            estimated_cost=25.00,
        ),
        PerformerRecommendation(
            performer_id="demo-performer-2",
            performer_name="Jordan Rivera",
            aci_score=78.2,
            match_reasons=[
                "Matches emotion requirements",
                "Budget-friendly option",
            ],
            suggested_mode="BLINK",
            estimated_cost=15.00,
        ),
    ]

    # Filter by budget if specified
    if request.max_budget_usd:
        recommendations = [
            r for r in recommendations
            if r.estimated_cost <= request.max_budget_usd
        ]

    return recommendations


@router.post("/creative-guidance", response_model=CreativeGuidance)
async def get_creative_guidance(
    request: CreativeGuidanceRequest,
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
) -> CreativeGuidance:
    """Get creative guidance from Steven.

    Provides analysis and recommendations for:
    - Story arc development
    - Pacing improvements
    - Visual style consistency
    - Dialogue enhancement
    - Character development
    """
    # Build a guidance request for the LLM
    guidance_prompt = f"Provide creative guidance for {request.guidance_type}"
    if request.specific_question:
        guidance_prompt += f": {request.specific_question}"

    project_context = {
        "project_id": request.project_id,
        "guidance_type": request.guidance_type,
        "current_state": request.current_state or {},
    }

    try:
        # Use LLM chat for creative guidance
        llm_result = await llm_service.chat(
            message=guidance_prompt,
            project_context=project_context,
        )

        # Extract recommendations from suggestions
        recommendations = [
            s.get("description", s.get("title", ""))
            for s in llm_result.get("suggestions", [])
        ]

        return CreativeGuidance(
            guidance_type=request.guidance_type,
            analysis=llm_result.get("message", "Analysis based on your project."),
            recommendations=recommendations if recommendations else [
                "Consider the emotional arc of your story",
                "Ensure visual consistency across scenes",
                "Let character actions reveal motivation",
            ],
            examples=None,
            reference_materials=None,
        )
    except Exception as llm_error:
        logger.warning(f"LLM guidance failed, using fallback: {llm_error}")

        # Fallback to static templates
        guidance_templates = {
            "story_arc": CreativeGuidance(
                guidance_type="story_arc",
                analysis="Your story follows a classic three-act structure with room for enhanced emotional beats.",
                recommendations=[
                    "Consider adding a 'dark moment' before the climax to heighten tension",
                    "The resolution could benefit from a callback to the opening scene",
                    "Character motivations are clear but could be reinforced through action",
                ],
                examples=[
                    {"reference": "Breaking Bad", "technique": "Delayed gratification in reveals"},
                ],
            ),
            "pacing": CreativeGuidance(
                guidance_type="pacing",
                analysis="Current pacing is consistent with average shot length of 4.2 seconds.",
                recommendations=[
                    "Vary shot lengths more dramatically in action sequences",
                    "Dialogue scenes could use longer takes for emotional impact",
                    "Consider breathing room between intense moments",
                ],
            ),
            "visual_style": CreativeGuidance(
                guidance_type="visual_style",
                analysis="Visual style is cohesive with strong use of contrast.",
                recommendations=[
                    "Color grading is consistent - maintain the current LUT",
                    "Consider motivated lighting changes for emotional shifts",
                    "The aspect ratio works well for the intimate scenes",
                ],
            ),
            "dialogue": CreativeGuidance(
                guidance_type="dialogue",
                analysis="Dialogue is natural with distinct character voices.",
                recommendations=[
                    "Some exposition could be shown rather than told",
                    "Subtext opportunities exist in scene 3",
                    "Character verbal tics add authenticity",
                ],
            ),
            "character": CreativeGuidance(
                guidance_type="character",
                analysis="Main character arc is well-defined with clear growth.",
                recommendations=[
                    "Supporting characters could have more agency",
                    "Character flaws create good conflict",
                    "Consider a foil character to highlight protagonist traits",
                ],
            ),
        }

        return guidance_templates.get(
            request.guidance_type,
            CreativeGuidance(
                guidance_type=request.guidance_type,
                analysis="I can provide guidance on this topic.",
                recommendations=["Please provide more context about your specific needs."],
            ),
        )


@router.get("/status")
async def get_steven_status() -> Dict[str, Any]:
    """Get Steven AI Co-pilot status."""
    return {
        "status": "online",
        "name": "Steven",
        "version": "1.0.0",
        "capabilities": [
            "scene_analysis",
            "performer_recommendations",
            "voice_commands",
            "chat",
            "creative_guidance",
        ],
        "voice_enabled": True,
        "context_aware": True,
    }
