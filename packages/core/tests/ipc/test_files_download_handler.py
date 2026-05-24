"""Tests for the files.downloadFile IPC handler.

Closes the regression window on P0-3 (renderer called `files.downloadFile`
with no backend handler — every Download button hung the desktop UI).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scenemachine.config import get_settings
from scenemachine.ipc.handlers import register_handlers
from scenemachine.ipc.server import IPCServer


@pytest.fixture
def ipc_server() -> IPCServer:
    server = IPCServer("/tmp/test_files_download.sock")
    register_handlers(server)
    return server


@pytest.fixture
def download_handler(ipc_server: IPCServer):
    handler = ipc_server.handlers.get("files.downloadFile")
    assert handler is not None, "files.downloadFile handler must be registered"
    return handler


@pytest.fixture
def fake_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return a real file inside a tmp data-dir, with settings.data_dir pointed at it."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    src = data_dir / "projects" / "00000000-0000-0000-0000-000000000001"
    src.mkdir(parents=True)
    video_path = src / "shot.mp4"
    video_path.write_bytes(b"\x00fake video bytes")

    settings = get_settings()
    monkeypatch.setattr(settings, "data_dir", data_dir)
    return video_path


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect Path.home() so we don't litter the real ~/Downloads during tests."""
    home = tmp_path / "fake_home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    return home


async def test_downloads_file_to_user_downloads(download_handler, fake_source, fake_home) -> None:
    """Happy path: copies the source into ~/Downloads with the requested name."""
    result = await download_handler(
        path=str(fake_source),
        filename="my-shot.mp4",
    )

    assert result["success"] is True
    destination = Path(result["destinationPath"])
    assert destination.exists(), "downloaded file should exist at destinationPath"
    assert destination.parent == fake_home / "Downloads"
    assert destination.name == "my-shot.mp4"
    assert destination.read_bytes() == fake_source.read_bytes()


async def test_collision_appends_counter(download_handler, fake_source, fake_home) -> None:
    """A second download of the same name must NOT overwrite the first."""
    first = await download_handler(path=str(fake_source), filename="shot.mp4")
    second = await download_handler(path=str(fake_source), filename="shot.mp4")

    first_path = Path(first["destinationPath"])
    second_path = Path(second["destinationPath"])
    assert first_path != second_path
    assert first_path.exists() and second_path.exists()
    assert second_path.name == "shot (1).mp4"


@pytest.mark.parametrize(
    "bad_name",
    ["", ".", "..", "../escape.mp4", "sub/dir.mp4", "back\\slash.mp4"],
)
async def test_rejects_traversal_filenames(
    download_handler, fake_source, fake_home, bad_name: str
) -> None:
    """filename must be a bare name — anything else is a bug or attack."""
    with pytest.raises(ValueError):
        await download_handler(path=str(fake_source), filename=bad_name)


async def test_rejects_source_outside_data_dir(
    download_handler, fake_source, fake_home, tmp_path: Path
) -> None:
    """Source path must resolve under data_dir — renderer cannot grab /etc/passwd."""
    outside = tmp_path / "elsewhere.mp4"
    outside.write_bytes(b"not mine")
    with pytest.raises(PermissionError):
        await download_handler(path=str(outside), filename="leaked.mp4")


async def test_missing_source_raises(download_handler, fake_source, fake_home) -> None:
    """If source doesn't exist, raise FileNotFoundError instead of writing 0 bytes."""
    missing = fake_source.parent / "nonexistent.mp4"
    with pytest.raises(FileNotFoundError):
        await download_handler(path=str(missing), filename="ghost.mp4")


async def test_rejects_non_regular_file(download_handler, fake_source, fake_home) -> None:
    """Directories are not downloadable — raise ValueError, don't recurse."""
    # The directory containing fake_source is inside the data dir.
    a_dir = fake_source.parent
    with pytest.raises(ValueError):
        await download_handler(path=str(a_dir), filename="dir.mp4")
