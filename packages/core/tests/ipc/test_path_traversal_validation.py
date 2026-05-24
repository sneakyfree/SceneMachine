"""Tests for the _validate_uploaded_file_path helper.

Closes the P1 IPC path-traversal entries from `docs/INVENTORY_DEFECTS.md`:
both `handle_upload_screenplay` and `handle_add_character_reference`
previously opened any renderer-supplied path with no validation, so a
buggy or hostile renderer could ask Python to read `/etc/passwd` or
`../../home/user/.ssh/id_rsa`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scenemachine.ipc.handlers import _validate_uploaded_file_path


def test_accepts_a_real_temp_file(tmp_path: Path) -> None:
    src = tmp_path / "script.fountain"
    src.write_text("INT. ROOM - DAY\n")
    result = _validate_uploaded_file_path(str(src))
    assert result == src.resolve()


def test_rejects_double_dot_traversal_token(tmp_path: Path) -> None:
    sneaky = tmp_path / ".." / "..wat" / "no.txt"
    with pytest.raises(ValueError, match="traversal"):
        _validate_uploaded_file_path(str(sneaky))


def test_rejects_etc_passwd() -> None:
    with pytest.raises(PermissionError, match="protected"):
        _validate_uploaded_file_path("/etc/passwd")


@pytest.mark.parametrize(
    "forbidden",
    ["/etc/shadow", "/proc/self/cmdline", "/sys/class/net", "/dev/null", "/root/.ssh"],
)
def test_rejects_system_secret_paths(forbidden: str) -> None:
    with pytest.raises(PermissionError):
        _validate_uploaded_file_path(forbidden)


def test_rejects_nonexistent_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _validate_uploaded_file_path(str(tmp_path / "ghost.fountain"))


def test_rejects_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not a regular file"):
        _validate_uploaded_file_path(str(tmp_path))


def test_resolves_symlink_target(tmp_path: Path) -> None:
    """Symlinks pointing to safe targets are followed; targets get the same checks."""
    real = tmp_path / "real.fountain"
    real.write_text("hello")
    link = tmp_path / "link.fountain"
    link.symlink_to(real)

    result = _validate_uploaded_file_path(str(link))
    assert result == real.resolve()


def test_symlink_to_system_secret_blocked(tmp_path: Path) -> None:
    """Symlinks pointing into a forbidden dir must be blocked at the target check."""
    link = tmp_path / "passwd-link"
    try:
        link.symlink_to("/etc/passwd")
    except (OSError, FileExistsError):
        pytest.skip("cannot create symlink in this environment")

    with pytest.raises(PermissionError):
        _validate_uploaded_file_path(str(link))


def test_handles_tilde_expansion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`~/file.txt` should expand to the user's home before validation."""
    home = tmp_path / "home"
    home.mkdir()
    target = home / "script.fountain"
    target.write_text("hi")

    monkeypatch.setenv("HOME", str(home))
    result = _validate_uploaded_file_path("~/script.fountain")
    assert result == target.resolve()
