"""Sanity tests to verify test infrastructure works."""

import pytest

from scenemachine import __version__


def test_version_exists() -> None:
    """Verify package version is defined."""
    assert __version__ is not None
    assert isinstance(__version__, str)


def test_version_format() -> None:
    """Verify version follows semver format."""
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


@pytest.mark.asyncio
async def test_async_works() -> None:
    """Verify async tests work."""
    result = await async_function()
    assert result == "async works"


async def async_function() -> str:
    """Simple async function for testing."""
    return "async works"
