"""Tests for secrets management module."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from scenemachine.security.secrets import (
    EnvironmentSecretProvider,
    FileSecretProvider,
    SecretsManager,
    mask_secret,
)


class TestMaskSecret:
    """Tests for secret masking."""

    def test_normal_secret(self):
        """Should mask middle of secret."""
        result = mask_secret("sk-abcdefghij123456")
        assert result == "sk-a...3456"

    def test_short_secret(self):
        """Should fully mask short secrets."""
        result = mask_secret("abc")
        assert result == "***"

    def test_empty_secret(self):
        """Should handle empty secrets."""
        assert mask_secret("") == "***"
        assert mask_secret(None) == "***"

    def test_custom_visible_chars(self):
        """Should respect visible_chars parameter."""
        result = mask_secret("abcdefghijklmnop", visible_chars=2)
        assert result == "ab...op"


class TestEnvironmentSecretProvider:
    """Tests for environment variable provider."""

    def test_get_existing_var(self):
        """Should retrieve existing environment variables."""
        os.environ["TEST_SECRET_KEY"] = "test-value"
        try:
            provider = EnvironmentSecretProvider()
            assert provider.get("TEST_SECRET_KEY") == "test-value"
        finally:
            del os.environ["TEST_SECRET_KEY"]

    def test_get_nonexistent_var(self):
        """Should return None for nonexistent variables."""
        provider = EnvironmentSecretProvider()
        assert provider.get("NONEXISTENT_VAR_12345") is None

    def test_with_prefix(self):
        """Should support prefixed variables."""
        os.environ["SM_API_KEY"] = "prefixed-value"
        try:
            provider = EnvironmentSecretProvider(prefix="SM_")
            assert provider.get("API_KEY") == "prefixed-value"
        finally:
            del os.environ["SM_API_KEY"]

    def test_exists(self):
        """Should check variable existence."""
        os.environ["EXISTS_TEST"] = "value"
        try:
            provider = EnvironmentSecretProvider()
            assert provider.exists("EXISTS_TEST") is True
            assert provider.exists("DOES_NOT_EXIST") is False
        finally:
            del os.environ["EXISTS_TEST"]

    def test_name_property(self):
        """Should return provider name."""
        provider = EnvironmentSecretProvider()
        assert provider.name == "environment"


class TestFileSecretProvider:
    """Tests for file-based provider."""

    def test_load_secrets_file(self, tmp_path):
        """Should load secrets from JSON file."""
        secrets = {"api_key": "file-secret", "db_password": "db-pass"}
        secrets_file = tmp_path / "secrets.json"
        secrets_file.write_text(json.dumps(secrets))

        provider = FileSecretProvider(str(secrets_file))
        assert provider.get("api_key") == "file-secret"
        assert provider.get("db_password") == "db-pass"

    def test_nonexistent_file(self):
        """Should handle nonexistent files gracefully."""
        provider = FileSecretProvider("/nonexistent/path/secrets.json")
        assert provider.get("any_key") is None

    def test_invalid_json(self, tmp_path):
        """Should handle invalid JSON gracefully."""
        secrets_file = tmp_path / "invalid.json"
        secrets_file.write_text("not valid json")

        provider = FileSecretProvider(str(secrets_file))
        assert provider.get("any_key") is None

    def test_exists(self, tmp_path):
        """Should check key existence."""
        secrets = {"exists_key": "value"}
        secrets_file = tmp_path / "secrets.json"
        secrets_file.write_text(json.dumps(secrets))

        provider = FileSecretProvider(str(secrets_file))
        assert provider.exists("exists_key") is True
        assert provider.exists("missing_key") is False

    def test_get_all_keys(self, tmp_path):
        """Should list all secret keys."""
        secrets = {"key1": "v1", "key2": "v2", "key3": "v3"}
        secrets_file = tmp_path / "secrets.json"
        secrets_file.write_text(json.dumps(secrets))

        provider = FileSecretProvider(str(secrets_file))
        keys = provider.get_all_keys()
        assert set(keys) == {"key1", "key2", "key3"}


class TestSecretsManager:
    """Tests for secrets manager."""

    def test_single_provider(self):
        """Should work with single provider."""
        os.environ["MANAGER_TEST_KEY"] = "manager-value"
        try:
            manager = SecretsManager()
            manager.add_provider(EnvironmentSecretProvider())
            assert manager.get("MANAGER_TEST_KEY") == "manager-value"
        finally:
            del os.environ["MANAGER_TEST_KEY"]

    def test_provider_priority(self, tmp_path):
        """Should respect provider priority (first match wins)."""
        os.environ["PRIORITY_TEST"] = "env-value"

        secrets = {"priority_test": "file-value"}
        secrets_file = tmp_path / "secrets.json"
        secrets_file.write_text(json.dumps(secrets))

        try:
            manager = SecretsManager()
            # Environment first (higher priority)
            manager.add_provider(EnvironmentSecretProvider())
            manager.add_provider(FileSecretProvider(str(secrets_file)))

            # Environment should win
            assert manager.get("PRIORITY_TEST") == "env-value"
        finally:
            del os.environ["PRIORITY_TEST"]

    def test_get_required(self):
        """Should raise for missing required secrets."""
        manager = SecretsManager()
        manager.add_provider(EnvironmentSecretProvider())

        with pytest.raises(ValueError) as exc_info:
            manager.get_required("DEFINITELY_NOT_SET_12345")

        assert "Required secret not found" in str(exc_info.value)

    def test_get_with_default(self):
        """Should return default for missing secrets."""
        manager = SecretsManager()
        manager.add_provider(EnvironmentSecretProvider())

        result = manager.get("MISSING_KEY", default="fallback")
        assert result == "fallback"

    def test_caching(self):
        """Should cache secret values."""
        os.environ["CACHE_TEST"] = "cached-value"
        try:
            manager = SecretsManager()
            manager.add_provider(EnvironmentSecretProvider())

            # First call
            assert manager.get("CACHE_TEST") == "cached-value"

            # Change env var
            os.environ["CACHE_TEST"] = "new-value"

            # Should still return cached value
            assert manager.get("CACHE_TEST") == "cached-value"

            # Clear cache
            manager.clear_cache()
            assert manager.get("CACHE_TEST") == "new-value"
        finally:
            del os.environ["CACHE_TEST"]

    def test_is_sensitive(self):
        """Should identify sensitive keys."""
        manager = SecretsManager()

        assert manager.is_sensitive("api_key") is True
        assert manager.is_sensitive("API_KEY") is True
        assert manager.is_sensitive("password") is True
        assert manager.is_sensitive("db_password") is True
        assert manager.is_sensitive("secret_token") is True
        assert manager.is_sensitive("username") is False
        assert manager.is_sensitive("port") is False

    def test_validate_required(self):
        """Should validate required secrets."""
        os.environ["VALID_KEY"] = "value"
        try:
            manager = SecretsManager()
            manager.add_provider(EnvironmentSecretProvider())

            result = manager.validate_required(["VALID_KEY", "INVALID_KEY"])
            assert result["VALID_KEY"] is True
            assert result["INVALID_KEY"] is False
        finally:
            del os.environ["VALID_KEY"]

    def test_exists(self):
        """Should check secret existence across providers."""
        os.environ["EXISTS_MANAGER_TEST"] = "value"
        try:
            manager = SecretsManager()
            manager.add_provider(EnvironmentSecretProvider())

            assert manager.exists("EXISTS_MANAGER_TEST") is True
            assert manager.exists("DOES_NOT_EXIST") is False
        finally:
            del os.environ["EXISTS_MANAGER_TEST"]

    def test_chaining(self):
        """Should support method chaining for add_provider."""
        manager = (
            SecretsManager()
            .add_provider(EnvironmentSecretProvider())
            .add_provider(EnvironmentSecretProvider(prefix="SM_"))
        )
        assert len(manager._providers) == 2
