"""
Tests for LLMService's high-level async methods, driven entirely through the
built-in MockBackend (LLMService defaults to LLMProvider.MOCK) — no real API
calls. Covers chat / analyze_project / suggest_scene / suggest_shot /
enhance_prompt / generate_shot_breakdown and the fallback path.
"""

from scenemachine.services.llm.service import LLMProvider, LLMService

_PROJECT = {"id": "p1", "name": "My Project", "state": "planning", "description": "A film"}
_SCENES = [
    {"scene_number": "1", "heading": "INT. ROOM - DAY", "location": "Room", "summary": "open"}
]
_CHARACTERS = [{"name": "Bob", "description": "a weary detective"}]
_SCENE = {
    "scene_number": "1",
    "heading": "INT. ROOM - DAY",
    "location": "Room",
    "description": "Bob enters.",
    "raw_content": "INT. ROOM - DAY\nBob enters.",
}
_SHOT = {"shot_number": "1", "shot_type": "wide", "description": "Bob in the doorway"}


async def test_chat_returns_structured_dict():
    svc = LLMService()  # MOCK primary
    result = await svc.chat("What should I do next?", _PROJECT)
    assert "message" in result
    assert "suggestions" in result
    assert isinstance(result["suggestions"], list)


async def test_analyze_project_returns_scored_dict():
    svc = LLMService()
    result = await svc.analyze_project(_PROJECT, _SCENES, _CHARACTERS)
    assert result["projectId"] == "p1"
    assert "overallScore" in result
    assert "generatedAt" in result


async def test_suggest_scene_returns_list():
    svc = LLMService()
    assert isinstance(await svc.suggest_scene(_SCENE, _CHARACTERS), list)


async def test_suggest_shot_returns_list():
    svc = LLMService()
    assert isinstance(
        await svc.suggest_shot(_SHOT, {"heading": "INT. ROOM - DAY", "location": "Room"}), list
    )


async def test_enhance_prompt_returns_string():
    svc = LLMService()
    out = await svc.enhance_prompt("a cat on a sofa", {"shot_type": "close-up", "scene": "INT."})
    assert isinstance(out, str)


async def test_generate_shot_breakdown_returns_dict():
    svc = LLMService()
    result = await svc.generate_shot_breakdown(_SCENE, _CHARACTERS)
    assert isinstance(result, dict)


async def test_complete_with_fallback_uses_fallback_when_primary_unconfigured():
    # Primary ANTHROPIC has no API key configured → _get_backend raises →
    # falls back to MOCK, which always succeeds.
    svc = LLMService(primary_provider=LLMProvider.ANTHROPIC, fallback_provider=LLMProvider.MOCK)
    result = await svc.chat("hello", _PROJECT)
    assert "message" in result
