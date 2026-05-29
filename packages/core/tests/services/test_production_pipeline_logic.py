"""
Pure-logic tests for ProductionPipeline helpers — prompt building, shot-data
lookup, status, failure-result construction, and result serialization. No
ComfyUI / ffmpeg / DB; the pipeline is built with an explicit temp output dir
and its in-memory state is set directly.
"""

import tempfile
from pathlib import Path

from scenemachine.services.production_pipeline import (
    PipelineResult,
    PipelineStage,
    ProductionPipeline,
    ShotGenerationStatus,
)


def _pipeline():
    return ProductionPipeline(project_id="p1", output_dir=Path(tempfile.mkdtemp()))


def test_build_generation_prompt_full():
    p = _pipeline()
    prompt = p._build_generation_prompt(
        {
            "description": "Bob enters the room",
            "shot_type": "wide",
            "camera_movement": "dolly",
            "characters": [{"name": "Bob"}, "Alice"],
            "mood": "tense",
            "lighting": "low-key",
        }
    )
    assert "Bob enters the room" in prompt
    assert "Camera: wide, dolly" in prompt
    assert "Characters: Bob, Alice" in prompt
    assert "Mood: tense" in prompt
    assert "Lighting: low-key" in prompt


def test_build_generation_prompt_empty_default():
    assert _pipeline()._build_generation_prompt({}) == "A cinematic shot"


def test_build_generation_prompt_atmosphere_fallback():
    prompt = _pipeline()._build_generation_prompt({"atmosphere": "eerie"})
    assert "Mood: eerie" in prompt


def test_get_shot_data():
    p = _pipeline()
    assert p._get_shot_data("s1") is None  # no shot_list yet
    p.shot_list = {
        "scenes": [{"shots": [{"shot_id": "s1", "description": "x"}]}]
    }
    assert p._get_shot_data("s1")["description"] == "x"
    assert p._get_shot_data("missing") is None


def test_get_status():
    p = _pipeline()
    p.total_cost = 30.0
    p.shot_statuses = {
        "s1": ShotGenerationStatus(shot_id="s1", scene_id="sc1", status="completed", quality_score=0.9)
    }
    status = p.get_status()
    assert status["project_id"] == "p1"
    assert status["stage"] == PipelineStage.INITIALIZED.value
    assert status["total_cost"] == 30.0
    assert status["budget_remaining"] == p.budget_limit - 30.0
    assert status["shots"]["s1"]["status"] == "completed"


def test_failure_builds_result():
    p = _pipeline()
    result = p._failure("boom")
    assert isinstance(result, PipelineResult)
    assert result.success is False
    assert result.error == "boom"
    assert result.project_id == "p1"


def test_pipeline_result_to_dict():
    r = PipelineResult(
        project_id="p1",
        success=True,
        stage=PipelineStage.COMPLETED,
        total_shots=5,
        completed_shots=5,
        total_cost_usd=12.5,
    )
    d = r.to_dict()
    assert d["success"] is True
    assert d["stage"] == PipelineStage.COMPLETED.value
    assert d["summary"]["total_shots"] == 5
    assert d["summary"]["total_cost_usd"] == 12.5
