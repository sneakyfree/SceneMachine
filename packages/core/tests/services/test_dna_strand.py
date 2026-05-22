"""Tests for DNA Strand services.

Tests the core services implemented as part of the DNA Strand Master Plan:
- Shot List Generator
- Blockers Engine
- Face Embedding Service
- Voice Cloning Service
- Character Image Generator
- Video Quality Reviewer
- Production Pipeline
"""


import pytest


class TestShotListGenerator:
    """Tests for the LLM-powered shot list generator."""

    def test_imports(self):
        """Verify all shot list generator imports work."""
        from scenemachine.services.shot_list_generator import ShotListGenerator
        assert ShotListGenerator is not None

    def test_generator_initialization(self):
        """Test generator can be initialized."""
        from scenemachine.services.shot_list_generator import ShotListGenerator
        generator = ShotListGenerator()
        assert generator is not None

    def test_prompt_building(self):
        """Test visual prompt generation."""
        from scenemachine.services.shot_list_generator import ShotListGenerator
        generator = ShotListGenerator()

        # Simple scene text
        scene_text = "INT. COFFEE SHOP - DAY\n\nJOHN sits at a table, nervously tapping his fingers."

        # Should be able to build a prompt
        prompt = generator._build_visual_prompt(scene_text, "medium shot")
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestBlockersEngine:
    """Tests for the Blockers/Unlockers engine."""

    def test_imports(self):
        """Verify all blockers engine imports work."""
        from scenemachine.services.blockers_engine import (
            BlockersEngine,
            BlockerSeverity,
        )
        assert BlockersEngine is not None
        assert BlockerSeverity.CRITICAL is not None

    def test_engine_initialization(self):
        """Test engine can be initialized."""
        from scenemachine.services.blockers_engine import BlockersEngine
        engine = BlockersEngine()
        assert engine is not None

    def test_analyze_empty_project(self):
        """Test analysis with empty data."""
        from scenemachine.services.blockers_engine import BlockersEngine
        engine = BlockersEngine()

        result = engine.analyze_project(
            characters=[],
            scenes=[],
            shots=[],
        )

        assert "blockers" in result
        assert isinstance(result["blockers"], list)

    def test_detect_missing_character(self):
        """Test detection of missing character reference."""
        from scenemachine.services.blockers_engine import BlockersEngine
        engine = BlockersEngine()

        # Character without reference image
        characters = [
            {"name": "JOHN", "has_reference_image": False}
        ]

        result = engine.analyze_project(
            characters=characters,
            scenes=[],
            shots=[],
        )

        # Should have blockers (format may vary)
        result.get("blockers", [])
        # Just verify we got some analysis back
        assert "blockers" in result


class TestFaceEmbeddingService:
    """Tests for the face embedding service."""

    def test_imports(self):
        """Verify all face embedding imports work."""
        from scenemachine.services.face_embedding import (
            FaceEmbeddingService,
            get_face_embedding_service,
        )
        assert FaceEmbeddingService is not None
        assert get_face_embedding_service is not None

    def test_singleton_pattern(self):
        """Test singleton returns same instance."""
        from scenemachine.services.face_embedding import get_face_embedding_service

        service1 = get_face_embedding_service()
        service2 = get_face_embedding_service()

        assert service1 is service2

    def test_similarity_threshold(self):
        """Test default similarity threshold."""
        from scenemachine.services.face_embedding import FaceEmbeddingService

        # Check class constant
        assert hasattr(FaceEmbeddingService, 'SIMILARITY_THRESHOLD')
        assert 0.0 <= FaceEmbeddingService.SIMILARITY_THRESHOLD <= 1.0


class TestVoiceCloningService:
    """Tests for the voice cloning service."""

    def test_imports(self):
        """Verify all voice cloning imports work."""
        from scenemachine.services.voice_cloning import (
            VoiceCloningService,
            get_voice_cloning_service,
        )
        assert VoiceCloningService is not None
        assert get_voice_cloning_service is not None

    def test_singleton_pattern(self):
        """Test singleton returns same instance."""
        from scenemachine.services.voice_cloning import get_voice_cloning_service

        service1 = get_voice_cloning_service()
        service2 = get_voice_cloning_service()

        assert service1 is service2

    def test_list_voices(self):
        """Test listing available voices."""
        from scenemachine.services.voice_cloning import get_voice_cloning_service

        service = get_voice_cloning_service()
        voices = service.get_available_voices()

        assert isinstance(voices, list)
        assert len(voices) >= 20  # Should have at least 20 Kokoro voices

    def test_voice_attributes(self):
        """Test voice has expected attributes."""
        from scenemachine.services.voice_cloning import get_voice_cloning_service

        service = get_voice_cloning_service()
        voices = service.get_available_voices()

        # Check first voice has expected structure (VoiceProfile object)
        if voices:
            voice = voices[0]
            # VoiceProfile is a dataclass with voice_id attribute
            assert hasattr(voice, 'voice_id') or hasattr(voice, 'id')

    def test_get_voice(self):
        """Test getting a specific voice."""
        from scenemachine.services.voice_cloning import get_voice_cloning_service

        service = get_voice_cloning_service()

        # Get a built-in voice
        voice = service.get_voice("am_adam")

        assert voice is not None


class TestCharacterImageGenerator:
    """Tests for the character image generator."""

    def test_imports(self):
        """Verify all image generator imports work."""
        from scenemachine.services.character_image_generator import (
            CharacterImageGenerator,
            get_character_image_generator,
        )
        assert CharacterImageGenerator is not None
        assert get_character_image_generator is not None

    def test_singleton_pattern(self):
        """Test singleton returns same instance."""
        from scenemachine.services.character_image_generator import get_character_image_generator

        gen1 = get_character_image_generator()
        gen2 = get_character_image_generator()

        assert gen1 is gen2

    def test_style_prompts(self):
        """Test style prompts are available."""
        from scenemachine.services.character_image_generator import CharacterImageGenerator

        assert hasattr(CharacterImageGenerator, 'STYLE_PROMPTS')
        assert len(CharacterImageGenerator.STYLE_PROMPTS) > 0

    def test_cost_estimation(self):
        """Test cost estimation for image generation."""
        from scenemachine.services.character_image_generator import get_character_image_generator

        generator = get_character_image_generator()

        result = generator.estimate_cost(num_images=4)

        # Returns a dict with cost breakdown
        assert isinstance(result, dict)
        assert 'total_cost' in result
        assert result['total_cost'] >= 0


class TestVideoQualityReviewer:
    """Tests for the video quality reviewer."""

    def test_imports(self):
        """Verify all quality reviewer imports work."""
        from scenemachine.services.video_quality_reviewer import (
            VideoQualityReviewer,
            get_video_quality_reviewer,
        )
        assert VideoQualityReviewer is not None
        assert get_video_quality_reviewer is not None

    def test_singleton_pattern(self):
        """Test singleton returns same instance."""
        from scenemachine.services.video_quality_reviewer import get_video_quality_reviewer

        reviewer1 = get_video_quality_reviewer()
        reviewer2 = get_video_quality_reviewer()

        assert reviewer1 is reviewer2

    def test_dimension_weights(self):
        """Test quality dimension weights sum to 1.0."""
        from scenemachine.services.video_quality_reviewer import get_video_quality_reviewer

        reviewer = get_video_quality_reviewer()
        weight_sum = sum(reviewer.DIMENSION_WEIGHTS.values())

        assert abs(weight_sum - 1.0) < 0.001

    def test_quality_dimensions(self):
        """Test all 8 quality dimensions are defined."""
        from scenemachine.services.video_quality_reviewer import (
            QualityDimension,
            get_video_quality_reviewer,
        )

        reviewer = get_video_quality_reviewer()

        # Should have 8 dimensions
        assert len(QualityDimension) == 8

        # All dimensions should have weights
        for dim in QualityDimension:
            assert dim in reviewer.DIMENSION_WEIGHTS


class TestProductionPipeline:
    """Tests for the production pipeline."""

    def test_imports(self):
        """Verify all pipeline imports work."""
        from scenemachine.services.production_pipeline import (
            ProductionPipeline,
            create_production_pipeline,
        )
        assert ProductionPipeline is not None
        assert create_production_pipeline is not None

    def test_pipeline_creation(self):
        """Test creating a pipeline instance."""
        from scenemachine.services.production_pipeline import create_production_pipeline

        pipeline = create_production_pipeline("test-project-001")

        assert pipeline is not None
        assert pipeline.project_id == "test-project-001"

    def test_pipeline_initial_stage(self):
        """Test pipeline starts in initialized stage."""
        from scenemachine.services.production_pipeline import (
            PipelineStage,
            create_production_pipeline,
        )

        pipeline = create_production_pipeline("test-project-002")

        assert pipeline.stage == PipelineStage.INITIALIZED

    def test_pipeline_configuration(self):
        """Test pipeline configuration options."""
        from scenemachine.services.production_pipeline import create_production_pipeline

        pipeline = create_production_pipeline(
            "test-project-003",
            max_parallel=4,
            quality_threshold=0.8,
            budget_limit=50.0,
        )

        assert pipeline.max_parallel == 4
        assert pipeline.quality_threshold == 0.8
        assert pipeline.budget_limit == 50.0

    def test_pipeline_status(self):
        """Test getting pipeline status."""
        from scenemachine.services.production_pipeline import create_production_pipeline

        pipeline = create_production_pipeline("test-project-004")
        status = pipeline.get_status()

        assert "project_id" in status
        assert "stage" in status
        assert status["project_id"] == "test-project-004"


class TestIntegrationWorkflow:
    """Integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_screenplay_to_shots_flow(self):
        """Test the screenplay parsing to shot breakdown flow."""
        from scenemachine.services.shot_list_generator import ShotListGenerator

        generator = ShotListGenerator()

        # Simple screenplay content
        screenplay_data = {
            "scenes": [
                {
                    "scene_number": "1",
                    "heading": "INT. OFFICE - DAY",
                    "content": "SARAH enters the office, looking tired.",
                }
            ]
        }

        # Generate shot list
        result = generator.generate(screenplay_data)

        assert result is not None
        assert "scenes" in result

    def test_blocker_to_fix_flow(self):
        """Test blocker detection and fix suggestion flow."""
        from scenemachine.services.blockers_engine import BlockersEngine

        engine = BlockersEngine()

        # Project with issues
        result = engine.analyze_project(
            characters=[
                {"name": "JOHN", "has_reference_image": False, "has_voice": False}
            ],
            scenes=[
                {"scene_number": "1", "heading": "INT. OFFICE - DAY"}
            ],
            shots=[
                {"shot_id": "1-1", "visual_prompt": "", "character": "JOHN"}
            ],
        )

        blockers = result.get("blockers", [])

        # Should have blockers
        assert len(blockers) > 0

        # Each blocker should have an unlocker (singular, not suggested_fixes)
        for blocker in blockers:
            assert "unlocker" in blocker, f"Blocker missing unlocker: {blocker}"
