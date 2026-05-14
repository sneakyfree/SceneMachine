"""Tests for the new GenerationService.generate() bridge method.

Verifies that the service correctly dispatches to a registered provider
without depending on a real ComfyUI process. Uses a stub provider that
satisfies the generators.base.GenerationProvider interface.
"""
from __future__ import annotations

from uuid import uuid4
import pytest


class _StubProvider:
    """Minimal generators.base.GenerationProvider-shaped object.

    The service only calls `.generate(request, progress_callback=...)` and
    reads `.name` — we don't need to inherit from the abstract class for
    this test, just present the duck-typed surface.
    """

    name = "stub-provider"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def generate(self, request, *, progress_callback=None):
        # Capture the call so the test can assert on it
        self.calls.append({
            "shot_id": str(request.shot_id),
            "prompt": request.prompt,
            "model_id": (request.extra_params or {}).get("model_id"),
            "input_image_path": request.input_image_path,
            "character_refs": list(request.character_references or []),
        })
        # Return a generators.base.GenerationResult-shaped object
        from scenemachine.generators.base import GenerationResult
        return GenerationResult(
            success=True,
            output_path=f"shots/{request.shot_id}/output.mp4",
            duration_seconds=request.duration_seconds,
            metadata={"provider": self.name},
        )


def _build_request(**overrides):
    from scenemachine.generators.base import GenerationRequest
    defaults = dict(
        shot_id=uuid4(),
        prompt="a hero walks through a misty forest",
        width=768,
        height=432,
        duration_seconds=3.0,
        fps=24,
    )
    defaults.update(overrides)
    return GenerationRequest(**defaults)


@pytest.mark.asyncio
async def test_generate_routes_to_registered_provider():
    """The service picks the provider matching the requested JobProvider
    enum value and forwards the request unchanged.
    """
    from scenemachine.services.generation import GenerationService
    from scenemachine.models.generation_job import JobProvider

    # Build a service without going through DB / global registry
    svc = GenerationService.__new__(GenerationService)
    svc.session = None
    svc.settings = None
    svc._progress_callbacks = {}
    stub = _StubProvider()
    svc._providers = {JobProvider.LOCAL: stub}

    request = _build_request(prompt="hello world")
    result = await svc.generate(request, provider=JobProvider.LOCAL)

    assert result.success is True
    assert result.output_path.endswith("output.mp4")
    assert len(stub.calls) == 1
    assert stub.calls[0]["prompt"] == "hello world"


@pytest.mark.asyncio
async def test_generate_defaults_to_LOCAL_provider():
    """When the caller doesn't specify a provider, LOCAL (ComfyUI on this
    rig) is the default — matches the documented per-shot pipeline path.
    """
    from scenemachine.services.generation import GenerationService
    from scenemachine.models.generation_job import JobProvider

    svc = GenerationService.__new__(GenerationService)
    svc._providers = {JobProvider.LOCAL: _StubProvider()}
    svc.session = svc.settings = None
    svc._progress_callbacks = {}

    request = _build_request()
    result = await svc.generate(request)  # no provider= kwarg
    assert result.success is True
    assert svc._providers[JobProvider.LOCAL].calls[0]["shot_id"] == str(request.shot_id)


@pytest.mark.asyncio
async def test_generate_raises_when_provider_not_registered():
    """Unregistered providers must fail loudly. Silent fallback would mask
    real configuration bugs (this is exactly the bug we fixed in the
    pipeline: a missing method swallowed by a bare except).
    """
    from scenemachine.services.generation import GenerationService
    from scenemachine.models.generation_job import JobProvider

    svc = GenerationService.__new__(GenerationService)
    svc._providers = {}  # empty registry
    svc.session = svc.settings = None
    svc._progress_callbacks = {}

    request = _build_request()
    with pytest.raises(ValueError, match="No generation provider"):
        await svc.generate(request, provider=JobProvider.LOCAL)


@pytest.mark.asyncio
async def test_generate_forwards_input_image_and_character_refs():
    """The provider receives the full provider-facing request — including
    input_image_path (I2V) and character_references (Animate). These
    are the fields the stack_router populates per shot.
    """
    from scenemachine.services.generation import GenerationService
    from scenemachine.models.generation_job import JobProvider

    svc = GenerationService.__new__(GenerationService)
    stub = _StubProvider()
    svc._providers = {JobProvider.LOCAL: stub}
    svc.session = svc.settings = None
    svc._progress_callbacks = {}

    request = _build_request(
        input_image_path="prev_last.png",
        character_references=[
            {"character_id": "hero", "reference_image_path": "hero.png"}
        ],
        extra_params={"model_id": "wan22-animate-14b"},
    )
    await svc.generate(request, provider=JobProvider.LOCAL)

    call = stub.calls[0]
    assert call["input_image_path"] == "prev_last.png"
    assert call["character_refs"] == [
        {"character_id": "hero", "reference_image_path": "hero.png"}
    ]
    assert call["model_id"] == "wan22-animate-14b"


@pytest.mark.asyncio
async def test_generate_forwards_progress_callback():
    """The service must pass the caller's progress_callback through to the
    provider so the UI/IPC layer can stream progress events. Dropping it
    would silently break the progress bar.
    """
    from scenemachine.services.generation import GenerationService
    from scenemachine.models.generation_job import JobProvider

    received_callbacks: list = []

    class _CallbackCapturingProvider(_StubProvider):
        async def generate(self, request, *, progress_callback=None):
            received_callbacks.append(progress_callback)
            return await super().generate(request, progress_callback=progress_callback)

    svc = GenerationService.__new__(GenerationService)
    cap = _CallbackCapturingProvider()
    svc._providers = {JobProvider.LOCAL: cap}
    svc.session = svc.settings = None
    svc._progress_callbacks = {}

    async def my_cb(p):
        pass

    await svc.generate(_build_request(), progress_callback=my_cb)
    assert received_callbacks == [my_cb]
