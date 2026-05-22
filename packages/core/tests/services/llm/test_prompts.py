"""Tests for LLM prompts."""

from scenemachine.services.llm.prompts import CopilotPrompts, PromptTemplates


class TestPromptTemplates:
    """Tests for prompt templates."""

    def test_system_context_exists(self):
        """Should have system context."""
        assert PromptTemplates.SYSTEM_CONTEXT
        assert "Steven" in PromptTemplates.SYSTEM_CONTEXT
        assert "SceneMachine" in PromptTemplates.SYSTEM_CONTEXT

    def test_analysis_format_exists(self):
        """Should have analysis format."""
        assert PromptTemplates.ANALYSIS_FORMAT
        assert "JSON" in PromptTemplates.ANALYSIS_FORMAT


class TestCopilotPrompts:
    """Tests for co-pilot prompts."""

    def test_chat_prompt_basic(self):
        """Should generate chat prompt."""
        prompt = CopilotPrompts.chat_prompt(
            message="How can I improve this scene?",
            project_context={},
        )

        assert "How can I improve this scene?" in prompt
        assert "User Message:" in prompt

    def test_chat_prompt_with_context(self):
        """Should include project context."""
        prompt = CopilotPrompts.chat_prompt(
            message="Help me",
            project_context={
                "project_name": "My Film",
                "screenplay_title": "The Story",
                "current_scene": {
                    "heading": "INT. OFFICE - DAY",
                    "description": "A busy office",
                },
            },
        )

        assert "My Film" in prompt
        assert "The Story" in prompt
        assert "INT. OFFICE - DAY" in prompt

    def test_chat_prompt_with_history(self):
        """Should include conversation history."""
        prompt = CopilotPrompts.chat_prompt(
            message="Continue",
            project_context={},
            conversation_history=[
                {"role": "user", "content": "Previous question"},
                {"role": "assistant", "content": "Previous answer"},
            ],
        )

        assert "Conversation History" in prompt
        assert "Previous question" in prompt

    def test_analyze_project_prompt(self):
        """Should generate analysis prompt."""
        prompt = CopilotPrompts.analyze_project_prompt(
            project_context={"name": "Test Project", "genre": "Drama"},
            scenes=[
                {"sequence": 1, "heading": "INT. OFFICE - DAY"},
                {"sequence": 2, "heading": "EXT. PARK - NIGHT"},
            ],
            characters=[
                {"name": "John", "description": "The protagonist"},
            ],
        )

        assert "Test Project" in prompt
        assert "Drama" in prompt
        assert "INT. OFFICE - DAY" in prompt
        assert "John" in prompt
        assert "JSON" in prompt

    def test_analyze_project_prompt_limits_scenes(self):
        """Should limit scenes to 20."""
        many_scenes = [{"sequence": i, "heading": f"Scene {i}"} for i in range(30)]

        prompt = CopilotPrompts.analyze_project_prompt(
            project_context={},
            scenes=many_scenes,
            characters=[],
        )

        # Should include first 20, not all 30
        assert "Scene 19" in prompt
        assert "Scene 25" not in prompt

    def test_suggest_scene_prompt(self):
        """Should generate scene suggestion prompt."""
        prompt = CopilotPrompts.suggest_scene_prompt(
            scene={
                "heading": "INT. KITCHEN - NIGHT",
                "description": "A tense conversation",
                "mood": "suspenseful",
                "shots": [
                    {"description": "Wide shot of kitchen"},
                    {"description": "Close-up on knife"},
                ],
            },
            characters=[
                {"name": "Sarah"},
                {"name": "Mike"},
            ],
        )

        assert "INT. KITCHEN - NIGHT" in prompt
        assert "suspenseful" in prompt
        assert "Sarah" in prompt
        assert "Mike" in prompt
        assert "Wide shot of kitchen" in prompt

    def test_suggest_scene_prompt_with_adjacent(self):
        """Should include adjacent scenes."""
        prompt = CopilotPrompts.suggest_scene_prompt(
            scene={"heading": "Scene 2"},
            characters=[],
            adjacent_scenes={
                "previous": {"heading": "Scene 1"},
                "next": {"heading": "Scene 3"},
            },
        )

        assert "Previous Scene: Scene 1" in prompt
        assert "Next Scene: Scene 3" in prompt

    def test_suggest_shot_prompt(self):
        """Should generate shot suggestion prompt."""
        prompt = CopilotPrompts.suggest_shot_prompt(
            shot={
                "shot_type": "CLOSE_UP",
                "camera_movement": "DOLLY",
                "description": "Character's reaction",
                "generation_prompt": "A close-up of a face showing surprise",
            },
            scene_context={
                "heading": "INT. OFFICE - DAY",
                "mood": "tense",
            },
        )

        assert "CLOSE_UP" in prompt
        assert "DOLLY" in prompt
        assert "Character's reaction" in prompt
        assert "tense" in prompt

    def test_suggest_shot_prompt_with_adjacent(self):
        """Should include adjacent shots."""
        prompt = CopilotPrompts.suggest_shot_prompt(
            shot={"description": "Current shot"},
            scene_context={},
            adjacent_shots={
                "previous": {"description": "Previous shot desc"},
                "next": {"description": "Next shot desc"},
            },
        )

        assert "Previous Shot:" in prompt
        assert "Next Shot:" in prompt

    def test_enhance_prompt_prompt(self):
        """Should generate prompt enhancement request."""
        prompt = CopilotPrompts.enhance_prompt_prompt(
            original_prompt="A man walking in a park",
            shot_context={
                "shot_type": "WIDE",
                "camera_movement": "TRACKING",
                "mood": "peaceful",
            },
        )

        assert "A man walking in a park" in prompt
        assert "WIDE" in prompt
        assert "TRACKING" in prompt
        assert "peaceful" in prompt
        assert "enhanced prompt" in prompt.lower()

    def test_enhance_prompt_with_style(self):
        """Should include style preferences."""
        prompt = CopilotPrompts.enhance_prompt_prompt(
            original_prompt="A scene",
            shot_context={},
            style_preferences={
                "aspect_ratio": "2.39:1",
                "color_palette": "warm",
                "lighting": "golden hour",
            },
        )

        assert "2.39:1" in prompt
        assert "warm" in prompt
        assert "golden hour" in prompt

    def test_generate_shot_breakdown_prompt(self):
        """Should generate shot breakdown request."""
        prompt = CopilotPrompts.generate_shot_breakdown_prompt(
            scene={
                "heading": "INT. RESTAURANT - EVENING",
                "description": "A romantic dinner",
                "mood": "intimate",
                "content": "JOHN and SARAH sit across from each other. They share a moment.",
            },
            characters=[
                {"name": "JOHN"},
                {"name": "SARAH"},
            ],
        )

        assert "INT. RESTAURANT - EVENING" in prompt
        assert "romantic dinner" in prompt
        assert "JOHN" in prompt
        assert "SARAH" in prompt
        assert "shot breakdown" in prompt.lower()
        assert "JSON" in prompt

    def test_generate_shot_breakdown_with_style(self):
        """Should include visual style."""
        prompt = CopilotPrompts.generate_shot_breakdown_prompt(
            scene={"heading": "Test"},
            characters=[],
            visual_style={
                "overall_look": "noir",
                "lighting_style": "high contrast",
                "camera_movement": "static",
            },
        )

        assert "noir" in prompt
        assert "high contrast" in prompt
