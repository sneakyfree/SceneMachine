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
async def test_i2v_continuity_routes_second_shot(tmp_path, stub_registry, stub_reviewer, monkeypatch):
    """Two shots in the same scene, no characters: first shot routes to T2V
    (no prior frame), then its last frame is extracted and seeded into the
    second shot's request — second shot must route to I2V via continuity.
    """
    from scenemachine.services.production_pipeline import ShotGenerationStatus

    pipeline, _ = _make_pipeline(tmp_path)
    scene_id = "scene-1"
    sid1, sid2 = str(uuid4()), str(uuid4())
    pipeline.shot_list = {"scenes": [{"scene_number": scene_id, "shots": [
        {"shot_id": sid1, "description": "establishing wide", "character_ids": [], "duration_seconds": 3.0},
        {"shot_id": sid2, "description": "medium follow", "character_ids": [], "duration_seconds": 3.0},
    ]}]}
    pipeline.characters = []

    # Stub the ffmpeg last-frame extractor: pretend it always succeeds and
    # returns a synthetic filename. The pipeline's stack_router will then
    # see it and route the SECOND shot to I2V.
    from scenemachine.utils import ffmpeg as ffmpeg_module
    class _StubFfmpeg:
        async def extract_frame(self, video_path, output_path, timestamp=1.0, quality=2):
            from pathlib import Path
            Path(str(output_path)).write_bytes(b"\xff\xd8\xff\xd9")  # tiny valid JPEG
            return Path(str(output_path))
    monkeypatch.setattr(ffmpeg_module, "get_ffmpeg", lambda: _StubFfmpeg())

    # Make the stub provider write a 1-byte mp4 so Path(video_path).exists() is True
    from scenemachine.generators.base import GenerationResult
    real_outputs = tmp_path / "shots"
    real_outputs.mkdir(exist_ok=True)
    def _make_real_result(req):
        out_dir = real_outputs / str(req.shot_id)
        out_dir.mkdir(exist_ok=True)
        mp4 = out_dir / "output.mp4"
        mp4.write_bytes(b"\x00" * 1024)
        return GenerationResult(
            success=True,
            output_path=f"shots/{req.shot_id}/output.mp4",
            duration_seconds=req.duration_seconds,
            cost_usd=0.0,
            metadata={"quality_score": 1.0},
        )
    async def _gen(req, progress_callback=None):
        stub_registry.calls.append({
            "shot_id": str(req.shot_id),
            "model_id": (req.extra_params or {}).get("model_id"),
            "input_image_path": req.input_image_path,
        })
        return _make_real_result(req)
    stub_registry.generate = _gen

    # Point pipeline.output_dir at the same tree the stub writes to so the
    # generated mp4 paths actually exist on disk for last-frame extraction.
    pipeline.output_dir = tmp_path
    # And settings.output_dir is used by the pipeline for path resolution.
    from scenemachine.config import get_settings
    monkeypatch.setattr(get_settings(), "output_dir", tmp_path)

    s1 = ShotGenerationStatus(shot_id=sid1, scene_id=scene_id, status="queued")
    s2 = ShotGenerationStatus(shot_id=sid2, scene_id=scene_id, status="queued")
    await pipeline._generate_videos([s1, s2])

    # 2 generations executed, in sequence
    assert len(stub_registry.calls) == 2
    first, second = stub_registry.calls
    # First shot: no prior frame → T2V
    assert first["model_id"] == "wan22-t2v-14b-fp8"
    assert first["input_image_path"] is None
    # Second shot: SHOULD have a prev_shot frame, routing to I2V
    assert second["model_id"] == "wan22-i2v-14b-fp8", (
        f"second shot should route I2V but got {second['model_id']} — "
        f"continuity wiring is broken"
    )
    assert second["input_image_path"] is not None
    assert second["input_image_path"].startswith("continuity_")


@pytest.mark.asyncio
async def test_continuity_does_not_cross_scene_boundary(tmp_path, stub_registry, stub_reviewer, monkeypatch):
    """Two scenes, each with one shot, no characters: both shots route to
    T2V (no continuity carries from scene 1 → scene 2). Each scene runs
    its own sequential loop so prev_frame is scoped per scene.
    """
    from scenemachine.services.production_pipeline import ShotGenerationStatus

    pipeline, _ = _make_pipeline(tmp_path)
    sid1, sid2 = str(uuid4()), str(uuid4())
    pipeline.shot_list = {"scenes": [
        {"scene_number": "scene-a", "shots": [{"shot_id": sid1, "description": "a", "character_ids": [], "duration_seconds": 3.0}]},
        {"scene_number": "scene-b", "shots": [{"shot_id": sid2, "description": "b", "character_ids": [], "duration_seconds": 3.0}]},
    ]}
    pipeline.characters = []

    from scenemachine.utils import ffmpeg as ffmpeg_module
    class _StubFfmpeg:
        async def extract_frame(self, video_path, output_path, timestamp=1.0, quality=2):
            from pathlib import Path as P
            P(str(output_path)).write_bytes(b"\xff\xd8\xff\xd9")
            return P(str(output_path))
    monkeypatch.setattr(ffmpeg_module, "get_ffmpeg", lambda: _StubFfmpeg())

    s1 = ShotGenerationStatus(shot_id=sid1, scene_id="scene-a", status="queued")
    s2 = ShotGenerationStatus(shot_id=sid2, scene_id="scene-b", status="queued")
    await pipeline._generate_videos([s1, s2])

    assert len(stub_registry.calls) == 2
    # Both should be T2V — no continuity ever crossed
    for call in stub_registry.calls:
        assert call["model_id"] == "wan22-t2v-14b-fp8", (
            f"continuity leaked across scenes: shot in own scene got {call['model_id']}"
        )
        assert call["input_image_path"] is None


@pytest.mark.asyncio
async def test_animate_still_wins_over_continuity_when_character_ref_present(
    tmp_path, stub_registry, stub_reviewer, monkeypatch
):
    """Even with a prev-shot frame available, a shot with a character_id +
    ref image must route to Animate (identity preservation outranks
    continuity). This is the rule the StackRouter enforces; this test
    verifies the pipeline upholds it."""
    from scenemachine.services.production_pipeline import ShotGenerationStatus

    pipeline, _ = _make_pipeline(tmp_path)
    sid1, sid2 = str(uuid4()), str(uuid4())
    hero = str(uuid4())
    pipeline.shot_list = {"scenes": [{"scene_number": "s1", "shots": [
        {"shot_id": sid1, "description": "wide", "character_ids": [], "duration_seconds": 3.0},
        {"shot_id": sid2, "description": "close-up of hero", "character_ids": [hero], "duration_seconds": 3.0},
    ]}]}
    pipeline.characters = [{"id": hero, "reference_image_path": "hero.png"}]

    from scenemachine.utils import ffmpeg as ffmpeg_module
    class _StubFfmpeg:
        async def extract_frame(self, video_path, output_path, timestamp=1.0, quality=2):
            from pathlib import Path as P
            P(str(output_path)).write_bytes(b"\xff\xd8\xff\xd9")
            return P(str(output_path))
    monkeypatch.setattr(ffmpeg_module, "get_ffmpeg", lambda: _StubFfmpeg())

    s1 = ShotGenerationStatus(shot_id=sid1, scene_id="s1", status="queued")
    s2 = ShotGenerationStatus(shot_id=sid2, scene_id="s1", status="queued")
    await pipeline._generate_videos([s1, s2])

    assert len(stub_registry.calls) == 2
    # Shot 2 has a character ref AND a prev frame — Animate wins.
    assert stub_registry.calls[1]["model_id"] == "wan22-animate-14b"


@pytest.mark.asyncio
async def test_no_provider_registered_fails_all_shots_loudly(
    tmp_path, monkeypatch, stub_reviewer
):
    """When the registry has NO provider for LOCAL, every shot is marked
    failed with an actionable error. This is the loud-failure replacement
    for the prior silent placeholder."""
    from scenemachine.generators import base as base_module

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
