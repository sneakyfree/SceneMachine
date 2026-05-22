"""Secrets Management Module.

Provides secure handling of secrets and sensitive configuration.
Supports multiple secret providers for different deployment environments.
"""

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


def mask_secret(secret: str, visible_chars: int = 4) -> str:
    """Mask a secret for safe logging/display.

    Args:
        secret: The secret to mask
        visible_chars: Number of characters to show at start/end

    Returns:
        Masked string like "sk-a1...9z"
    """
    if not secret:
        return "***"
    if len(secret) <= visible_chars * 2:
        return "*" * len(secret)
    return f"{secret[:visible_chars]}...{secret[-visible_chars:]}"


@dataclass
class SecretMetadata:
    """Metadata about a secret."""

    name: str
    source: str  # Provider name
    last_rotated: str | None = None
    expires_at: str | None = None


class SecretProvider(ABC):
    """Abstract base class for secret providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging/debugging."""
        pass

    @abstractmethod
    def get(self, key: str) -> str | None:
        """Get a secret value by key.

        Args:
            key: The secret key/name

        Returns:
            The secret value or None if not found
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a secret exists.

        Args:
            key: The secret key/name

        Returns:
            True if secret exists
        """
        pass

    def get_all_keys(self) -> list[str]:
        """Get all available secret keys.

        Returns:
            List of secret keys
        """
        return []


class EnvironmentSecretProvider(SecretProvider):
    """Secret provider that reads from environment variables.

    This is the default provider and suitable for most deployments.
    Supports optional prefix for namespacing secrets.
    """

    def __init__(self, prefix: str = "") -> None:
        """Initialize environment provider.

        Args:
            prefix: Optional prefix for environment variables (e.g., "SM_")
        """
        self._prefix = prefix.upper()

    @property
    def name(self) -> str:
        return "environment"

    def _get_key(self, key: str) -> str:
        """Get the full environment variable name."""
        return f"{self._prefix}{key.upper()}"

    def get(self, key: str) -> str | None:
        """Get secret from environment variable."""
        env_key = self._get_key(key)
        value = os.environ.get(env_key)
        if value:
            logger.debug(f"Found secret {env_key} in environment")
        return value

    def exists(self, key: str) -> bool:
        """Check if environment variable exists."""
        return self._get_key(key) in os.environ

    def get_all_keys(self) -> list[str]:
        """Get all environment variables with prefix."""
        if not self._prefix:
            return []
        return [k[len(self._prefix) :].lower() for k in os.environ if k.startswith(self._prefix)]


class FileSecretProvider(SecretProvider):
    """Secret provider that reads from a JSON secrets file.

    Suitable for development or Docker secrets mounted as files.
    The file should be a JSON object with key-value pairs.
    """

    def __init__(self, file_path: str | Path) -> None:
        """Initialize file provider.

        Args:
            file_path: Path to the secrets JSON file
        """
        self._path = Path(file_path)
        self._secrets: dict[str, str] = {}
        self._loaded = False

    @property
    def name(self) -> str:
        return f"file:{self._path.name}"

    def _load(self) -> None:
        """Load secrets from file."""
        if self._loaded:
            return

        if not self._path.exists():
            logger.warning(f"Secrets file not found: {self._path}")
            self._loaded = True
            return

        try:
            with open(self._path) as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._secrets = {k: str(v) for k, v in data.items()}
                    logger.info(f"Loaded {len(self._secrets)} secrets from {self._path}")
                else:
                    logger.error(f"Secrets file must contain a JSON object: {self._path}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse secrets file: {e}")
        except Exception as e:
            logger.error(f"Failed to load secrets file: {e}")

        self._loaded = True

    def get(self, key: str) -> str | None:
        """Get secret from file."""
        self._load()
        return self._secrets.get(key.lower())

    def exists(self, key: str) -> bool:
        """Check if secret exists in file."""
        self._load()
        return key.lower() in self._secrets

    def get_all_keys(self) -> list[str]:
        """Get all secret keys from file."""
        self._load()
        return list(self._secrets.keys())


class SecretsManager:
    """Centralized secrets management.

    Supports multiple providers with priority ordering.
    Providers are checked in order; first match wins.

    Usage:
        manager = SecretsManager()
        manager.add_provider(EnvironmentSecretProvider())
        manager.add_provider(FileSecretProvider("secrets.json"))

        api_key = manager.get("api_key")
    """

    # Secret keys that should never be logged
    SENSITIVE_PATTERNS = [
        re.compile(r".*api[_-]?key.*", re.IGNORECASE),
        re.compile(r".*secret.*", re.IGNORECASE),
        re.compile(r".*password.*", re.IGNORECASE),
        re.compile(r".*token.*", re.IGNORECASE),
        re.compile(r".*private[_-]?key.*", re.IGNORECASE),
        re.compile(r".*credential.*", re.IGNORECASE),
    ]

    def __init__(self) -> None:
        self._providers: list[SecretProvider] = []
        self._cache: dict[str, str] = {}
        self._cache_enabled = True

    def add_provider(self, provider: SecretProvider) -> "SecretsManager":
        """Add a secret provider.

        Args:
            provider: The provider to add

        Returns:
            Self for chaining
        """
        self._providers.append(provider)
        logger.debug(f"Added secret provider: {provider.name}")
        return self

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get a secret value.

        Args:
            key: The secret key
            default: Default value if not found

        Returns:
            The secret value or default
        """
        # Check cache
        if self._cache_enabled and key in self._cache:
            return self._cache[key]

        # Try providers in order
        for provider in self._providers:
            value = provider.get(key)
            if value is not None:
                if self._cache_enabled:
                    self._cache[key] = value
                return value

        return default

    def get_required(self, key: str) -> str:
        """Get a required secret, raising if not found.

        Args:
            key: The secret key

        Returns:
            The secret value

        Raises:
            ValueError: If secret is not found
        """
        value = self.get(key)
        if value is None:
            raise ValueError(f"Required secret not found: {key}")
        return value

    def exists(self, key: str) -> bool:
        """Check if a secret exists in any provider.

        Args:
            key: The secret key

        Returns:
            True if secret exists
        """
        return any(provider.exists(key) for provider in self._providers)

    def get_metadata(self, key: str) -> SecretMetadata | None:
        """Get metadata about a secret.

        Args:
            key: The secret key

        Returns:
            SecretMetadata or None if not found
        """
        for provider in self._providers:
            if provider.exists(key):
                return SecretMetadata(name=key, source=provider.name)
        return None

    def is_sensitive(self, key: str) -> bool:
        """Check if a key is for a sensitive value.

        Args:
            key: The key to check

        Returns:
            True if key matches sensitive patterns
        """
        return any(pattern.match(key) for pattern in self.SENSITIVE_PATTERNS)

    def clear_cache(self) -> None:
        """Clear the secrets cache."""
        self._cache.clear()

    def disable_cache(self) -> None:
        """Disable secrets caching."""
        self._cache_enabled = False
        self._cache.clear()

    def validate_required(self, keys: list[str]) -> dict[str, bool]:
        """Validate that required secrets exist.

        Args:
            keys: List of required secret keys

        Returns:
            Dict mapping key to exists status
        """
        return {key: self.exists(key) for key in keys}


# Global instance
_secrets_manager: SecretsManager | None = None


def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager instance.

    Creates and configures the manager on first call.

    Returns:
        The SecretsManager instance
    """
    global _secrets_manager

    if _secrets_manager is None:
        _secrets_manager = SecretsManager()

        # Add default providers
        # 1. Environment variables (highest priority)
        _secrets_manager.add_provider(EnvironmentSecretProvider())

        # 2. Namespaced environment variables
        _secrets_manager.add_provider(EnvironmentSecretProvider(prefix="SM_"))

        # 3. Secrets file if it exists
        secrets_file = Path("./secrets.json")
        if secrets_file.exists():
            _secrets_manager.add_provider(FileSecretProvider(secrets_file))

        logger.info("Initialized secrets manager")

    return _secrets_manager
