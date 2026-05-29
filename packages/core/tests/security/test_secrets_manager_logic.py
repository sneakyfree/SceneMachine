"""
Tests for the secrets layer — EnvironmentSecretProvider, FileSecretProvider,
and SecretsManager (priority ordering, caching, sensitivity, validation).
No external services; env vars + a temp JSON file.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from scenemachine.security.secrets import (
    EnvironmentSecretProvider,
    FileSecretProvider,
    SecretsManager,
)


def test_environment_provider():
    os.environ["SMX_DB_URL"] = "postgres://x"
    try:
        p = EnvironmentSecretProvider(prefix="SMX_")
        assert p.name == "environment"
        assert p.get("db_url") == "postgres://x"
        assert p.get("missing") is None
        assert p.exists("db_url") is True
        assert "db_url" in p.get_all_keys()
    finally:
        del os.environ["SMX_DB_URL"]


def test_environment_provider_no_prefix_keys_empty():
    assert EnvironmentSecretProvider().get_all_keys() == []


def test_file_provider(tmp_path: Path = None):
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "secrets.json"
        f.write_text(json.dumps({"api_key": "abc", "token": "xyz"}))
        p = FileSecretProvider(f)
        assert p.name.startswith("file:")
        assert p.get("api_key") == "abc"
        assert p.get("TOKEN") == "xyz"  # lookups are lowercased
        assert p.exists("api_key") is True
        assert set(p.get_all_keys()) == {"api_key", "token"}


def test_file_provider_missing_file():
    p = FileSecretProvider("/nonexistent/secrets.json")
    assert p.get("anything") is None
    assert p.exists("anything") is False


def test_manager_priority_and_cache():
    os.environ["SMY_SHARED"] = "from_env"
    try:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "s.json"
            f.write_text(json.dumps({"shared": "from_file", "only_file": "f"}))
            mgr = SecretsManager()
            ret = mgr.add_provider(EnvironmentSecretProvider(prefix="SMY_")).add_provider(
                FileSecretProvider(f)
            )
            assert ret is mgr  # chaining
            # env provider is first → wins for "shared"
            assert mgr.get("shared") == "from_env"
            assert mgr.get("only_file") == "f"
            assert mgr.get("nope", default="d") == "d"
            # cached now
            assert "shared" in mgr._cache
    finally:
        del os.environ["SMY_SHARED"]


def test_manager_get_required_raises():
    mgr = SecretsManager()
    with pytest.raises(ValueError):
        mgr.get_required("definitely_missing")


def test_manager_exists_metadata_validate():
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "s.json"
        f.write_text(json.dumps({"present": "1"}))
        mgr = SecretsManager().add_provider(FileSecretProvider(f))
        assert mgr.exists("present") is True
        assert mgr.exists("absent") is False
        meta = mgr.get_metadata("present")
        assert meta is not None and meta.name == "present"
        assert mgr.get_metadata("absent") is None
        assert mgr.validate_required(["present", "absent"]) == {"present": True, "absent": False}


def test_manager_is_sensitive():
    mgr = SecretsManager()
    assert mgr.is_sensitive("anthropic_api_key") is True
    assert mgr.is_sensitive("DB_PASSWORD") is True
    assert mgr.is_sensitive("access_token") is True
    assert mgr.is_sensitive("region") is False


def test_manager_cache_controls():
    mgr = SecretsManager()
    mgr._cache["k"] = "v"
    mgr.clear_cache()
    assert mgr._cache == {}
    mgr.disable_cache()
    assert mgr._cache_enabled is False
