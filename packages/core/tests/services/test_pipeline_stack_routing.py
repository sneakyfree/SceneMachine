"""Test that ProductionPipeline._generate_videos uses StackRouter +
the registry-resolved provider (PR follow-up to #40).

These are unit tests — they monkey-patch the global ProviderRegistry
with a stub provider so no real ComfyUI is touched. The goal is to
verify the wiring (routing + request construction + provider dispatch)
rather than the generation itself.
"""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import pytest


class _StubProvider:
    """Provider stub that records every generate() call and returns
    a settable result. Matches the generators.base.GenerationProvider
    duck-typed surface for what the pipeline needs.
    """

    def __init__(self) -> None:
        self.calls: list = []
        self.next_result = None  # caller sets this per test

    @property
    def name(self) -> str:
        return "stub-pipeline-provider"

    async def generate(self, request, progress_callback=None):
        self.calls.append({
            "shot_id": str(request.shot_id),
            "prompt": request.prompt,
            "model_id": (request.extra_params or {}).get("model_id"),
            "input_image_path": request.input_image_path,
            "character_refs": list(request.character_references or []),
            "duration_seconds": request.duration_seconds,
        })
        if self.next_result is not None:
            return self.next_result
        from scenemachine.generators.base import GenerationResult
        return GenerationResult(
            success=True,
            output_path=f"shots/{request.shot_id}/output.mp4",
            duration_seconds=request.duration_seconds,
            cost_usd=0.0,
            metadata={"provider": self.name, "quality_score": 0.9},
        )


def _make_pipeline(tmp_path: Path):
    """Build a fresh ProductionPipeline with no global state."""
    from scenemachine.services.production_pipeline import (
        ProductionPipeline,
        ShotGenerationStatus,
    )
    p = ProductionPipeline(
        project_id="test-routing",
        output_dir=tmp_path,
        max_parallel=1,
        quality_threshold=0.0,  # disable regen loop
    )
    return p, ShotGenerationStatus


@pytest.fixture
def stub_registry(monkeypatch):
    """Replace the global ProviderRegistry with one containing a stub for LOCAL."""
    from scenemachine.generators import base as base_module
    from scenemachine.models.generation_job import JobProvider

    stub = _StubProvider()

    class _StubRegistry:
        def get_provider(self, kind):
            return stub if kind == JobProvider.LOCAL else None

        def list_providers(self):
            return [JobProvider.LOCAL]

    monkeypatch.setattr(base_module, "get_provider_registry", lambda: _StubRegistry())
    return stub


@pytest.fixture
def stub_reviewer(monkeypatch):
    """Disable the video quality reviewer — we're not testing it here."""
    class _NoReview:
        async def review_video(self, path):
            return {"overall_score": 1.0}

    from scenemachine.services import video_quality_reviewer
    monkeypatch.setattr(
        video_quality_reviewer,
        "get_video_quality_reviewer",
        lambda: _NoReview(),
    )


@pytest.mark.asyncio
async def test_t2v_routing_for_simple_shot(tmp_path, stub_registry, stub_reviewer):
    """A shot with no characters + no continuity routes to T2V and the
    provider gets a GenerationRequest with model_id=wan22-t2v-14b-fp8."""
    pipeline, ShotStatus = _make_pipeline(tmp_path)

    shot_id = str(uuid4())
    pipeline.shot_list = {"scenes": [{"shots": [{
        "shot_id": shot_id,
        "description": "establishing wide of a misty pine forest at dawn",
        "character_ids": [],
        "duration_seconds": 3.0,
        "shot_type": "establishing",
    }]}]}
    pipeline.characters = []

    shot = ShotStatus(shot_id=shot_id, scene_id="scene-1", status="queued")
    await pipeline._generate_videos([shot])

    assert len(stub_registry.calls) == 1
    call = stub_registry.calls[0]
    assert call["model_id"] == "wan22-t2v-14b-fp8"
    assert call["input_image_path"] is None
    assert call["character_refs"] == []
    assert shot.status == "completed"


@pytest.mark.asyncio
async def test_animate_routing_when_character_ref_available(
    tmp_path, stub_registry, stub_reviewer
):
    """A shot with a character_id AND a registered reference image routes
    to Animate. The character_references list is forwarded to the provider."""
    pipeline, ShotStatus = _make_pipeline(tmp_path)

    shot_id = str(uuid4())
    hero_id = str(uuid4())
    pipeline.shot_list = {"scenes": [{"shots": [{
        "shot_id": shot_id,
        "description": "close-up of the hero, dialogue",
        "character_ids": [hero_id],
        "duration_seconds": 3.0,
        "shot_type": "close_up",
    }]}]}
    pipeline.characters = [
        {"id": hero_id, "reference_image_path": "hero.png"},
    ]

    shot = ShotStatus(shot_id=shot_id, scene_id="scene-1", status="queued")
    await pipeline._generate_videos([shot])

    assert len(stub_registry.calls) == 1
    call = stub_registry.calls[0]
    assert call["model_id"] == "wan22-animate-14b"
    assert call["character_refs"] == [
        {"character_id": hero_id, "reference_image_path": "hero.png"}
    ]
    assert shot.status == "completed"


@pytest.mark.asyncio
async def test_provider_failure_propagates_to_shot_status(
    tmp_path, stub_registry, stub_reviewer
):
    """When the provider returns success=False, the shot is marked failed
    with the error message — no silent placeholder mp4 (regression test
    for the pre-#40 silent-fallback bug)."""
    from scenemachine.generators.base import GenerationResult

    pipeline, ShotStatus = _make_pipeline(tmp_path)
    stub_registry.next_result = GenerationResult(
        success=False,
        error_code="COMFYUI_UNAVAILABLE",
        error_message="ComfyUI server is not running on this host",
    )

    shot_id = str(uuid4())
    pipeline.shot_list = {"scenes": [{"shots": [{
        "shot_id": shot_id,
        "description": "anything",
        "character_ids": [],
        "duration_seconds": 3.0,
    }]}]}
    pipeline.characters = []

    shot = ShotStatus(shot_id=shot_id, scene_id="scene-1", status="queued")
    await pipeline._generate_videos([shot])

    assert shot.status == "failed"
    assert "ComfyUI server is not running" in (shot.error or "")
    assert shot.video_path is None or not Path(shot.video_path or "").exists()


@pytest.mark.asyncio
async def test_no_provider_registered_fails_all_shots_loudly(
    tmp_path, monkeypatch, stub_reviewer
):
    """When the registry has NO provider for LOCAL, every shot is marked
    failed with an actionable error. This is the loud-failure replacement
    for the prior silent placeholder."""
    from scenemachine.generators import base as base_module
    from scenemachine.models.generation_job import JobProvider

    class _EmptyRegistry:
        def get_provider(self, kind):
            return None

        def list_providers(self):
            return []

    monkeypatch.setattr(base_module, "get_provider_registry", lambda: _EmptyRegistry())

    pipeline, ShotStatus = _make_pipeline(tmp_path)
    shot_id = str(uuid4())
    pipeline.shot_list = {"scenes": [{"shots": [{
        "shot_id": shot_id,
        "description": "any",
        "character_ids": [],
        "duration_seconds": 3.0,
    }]}]}
    pipeline.characters = []

    shot = ShotStatus(shot_id=shot_id, scene_id="scene-1", status="queued")
    await pipeline._generate_videos([shot])

    assert shot.status == "failed"
    assert "provider" in (shot.error or "").lower()
