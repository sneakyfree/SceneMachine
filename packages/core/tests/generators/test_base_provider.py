"""
Pure-logic tests for generators/base.py — provider capabilities, request
validation, default concrete methods, and the dataclasses. Uses a minimal
in-memory fake provider (no network, no mocking of externals).
"""

import uuid

from scenemachine.generators.base import (
    GenerationProvider,
    GenerationRequest,
    GenerationResult,
    ProviderCapabilities,
    ProviderFeature,
    VideoModel,
)
from scenemachine.models.generation_job import JobProvider


class _FakeProvider(GenerationProvider):
    """Minimal concrete provider exercising the ABC's default methods."""

    @property
    def name(self) -> str:
        return "fake"

    @property
    def provider_type(self) -> JobProvider:
        return list(JobProvider)[0]

    async def generate(self, request, progress_callback=None) -> GenerationResult:
        return GenerationResult(success=True, output_path="/tmp/out.mp4")

    async def check_availability(self) -> bool:
        return True


def _req(**kw):
    base = dict(
        shot_id=uuid.uuid4(),
        prompt="a shot",
        width=1280,
        height=720,
        fps=24,
        duration_seconds=3.0,
    )
    base.update(kw)
    return GenerationRequest(**base)


# ---- ProviderCapabilities ------------------------------------------------

def test_capabilities_supports():
    caps = ProviderCapabilities(features=[ProviderFeature.TEXT_TO_VIDEO])
    assert caps.supports(ProviderFeature.TEXT_TO_VIDEO) is True
    assert caps.supports(ProviderFeature.IMAGE_TO_VIDEO) is False


# ---- validate_request ----------------------------------------------------

def test_validate_request_valid_has_no_errors():
    assert _FakeProvider().validate_request(_req()) == []


def test_validate_request_flags_width_height():
    errors = _FakeProvider().validate_request(_req(width=5000, height=5000))
    assert any("Width" in e for e in errors)
    assert any("Height" in e for e in errors)


def test_validate_request_flags_duration_and_fps():
    too_long = _FakeProvider().validate_request(_req(duration_seconds=100))
    assert any("exceeds maximum" in e for e in too_long)
    too_short = _FakeProvider().validate_request(_req(duration_seconds=0.1))
    assert any("below minimum" in e for e in too_short)
    bad_fps = _FakeProvider().validate_request(_req(fps=999))
    assert any("FPS" in e for e in bad_fps)


# ---- default concrete methods --------------------------------------------

def test_default_concrete_methods():
    p = _FakeProvider()
    assert p.estimate_cost(duration_seconds=5.0) == 0.0
    assert p.list_models() == []
    assert p.get_model("anything") is None
    assert p.capabilities.supports(ProviderFeature.TEXT_TO_VIDEO) is True


async def test_check_health_available():
    health = await _FakeProvider().check_health()
    assert health.available is True


async def test_cancel_default_false():
    assert await _FakeProvider().cancel("job-1") is False


# ---- dataclasses ---------------------------------------------------------

def test_dataclass_construction():
    r = GenerationResult(success=False, error_message="boom", error_code="E1")
    assert r.success is False and r.metadata == {}
    m = VideoModel(id="m1", name="Model One")
    assert m.supports_text_to_video is True and m.extra_params == {}
