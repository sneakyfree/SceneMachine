"""Regression tests for P1-2 — character_image_generator silent empty-PIL fail.

Before iter 9, when PIL was missing the mock-image branch wrote a 0-byte
PNG and returned `success=True`. Downstream pipeline steps loaded that
empty file as if it were a real reference image. Now it raises.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scenemachine.services.character_image_generator import (
    CharacterImageGenerator,
    ImageProvider,
)


async def test_raises_when_pil_unavailable(tmp_path: Path) -> None:
    """If PIL import fails, raise RuntimeError instead of returning a 0-byte file."""
    gen = CharacterImageGenerator(
        output_dir=tmp_path,
        default_provider=ImageProvider.MOCK,
    )

    # Stub out the PIL imports so the except ImportError branch fires.
    # We can't easily un-import PIL after the suite has run, so patch the
    # specific names referenced inside the try block.
    real_modules = sys.modules.copy()
    try:
        sys.modules["PIL"] = None  # type: ignore[assignment]
        sys.modules["PIL.Image"] = None  # type: ignore[assignment]
        sys.modules["PIL.ImageDraw"] = None  # type: ignore[assignment]
        sys.modules["PIL.ImageFont"] = None  # type: ignore[assignment]

        with pytest.raises(RuntimeError, match="Pillow"):
            await gen._generate_mock(
                prompt="A villain",
                negative_prompt="",
                width=512,
                height=512,
                seed=42,
            )
    finally:
        sys.modules.clear()
        sys.modules.update(real_modules)


async def test_no_zero_byte_files_left_on_disk(tmp_path: Path) -> None:
    """Confirms the failure mode doesn't leave a stub PNG behind."""
    gen = CharacterImageGenerator(
        output_dir=tmp_path,
        default_provider=ImageProvider.MOCK,
    )

    real_modules = sys.modules.copy()
    try:
        sys.modules["PIL"] = None  # type: ignore[assignment]
        sys.modules["PIL.Image"] = None  # type: ignore[assignment]
        sys.modules["PIL.ImageDraw"] = None  # type: ignore[assignment]
        sys.modules["PIL.ImageFont"] = None  # type: ignore[assignment]

        with pytest.raises(RuntimeError):
            await gen._generate_mock(
                prompt="X",
                negative_prompt="",
                width=64,
                height=64,
                seed=1,
            )

        # No PNGs should have been created — the old code wrote `b""` to disk.
        pngs = list(tmp_path.glob("*.png"))
        assert pngs == [], (
            f"_generate_mock left empty PNGs behind: {pngs} — that's the old silent-fail bug"
        )
    finally:
        sys.modules.clear()
        sys.modules.update(real_modules)


async def test_normal_happy_path_still_works(tmp_path: Path) -> None:
    """Sanity: when PIL is available, the mock generator produces a real PNG."""
    gen = CharacterImageGenerator(
        output_dir=tmp_path,
        default_provider=ImageProvider.MOCK,
    )

    result = await gen._generate_mock(
        prompt="A hero in the rain",
        negative_prompt="blurry",
        width=128,
        height=128,
        seed=99,
    )

    assert result.success is True
    out = Path(result.image_path)
    assert out.exists()
    assert out.stat().st_size > 0, "should be a real PNG, not 0 bytes"
    assert result.metadata == {"mock": True}, (
        "happy-path metadata should not contain the contradictory 'empty' flag"
    )
