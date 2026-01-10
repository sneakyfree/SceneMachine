"""Tests for password hashing utilities."""

import pytest

from scenemachine.auth.password import hash_password, verify_password


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_returns_string(self):
        """hash_password should return a string."""
        result = hash_password("mypassword123")
        assert isinstance(result, str)

    def test_hash_password_not_equal_to_plaintext(self):
        """Hashed password should not equal plaintext."""
        password = "mypassword123"
        hashed = hash_password(password)
        assert hashed != password

    def test_hash_password_produces_different_hashes(self):
        """Same password should produce different hashes (due to salt)."""
        password = "mypassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """verify_password should return True for correct password."""
        password = "mypassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """verify_password should return False for incorrect password."""
        password = "mypassword123"
        hashed = hash_password(password)
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_empty_string(self):
        """verify_password should handle empty strings."""
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False

    def test_hash_password_unicode(self):
        """hash_password should handle unicode passwords."""
        password = "пароль123"  # Russian for "password"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_hash_password_long_password(self):
        """hash_password should handle long passwords."""
        password = "a" * 1000
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_hash_password_special_characters(self):
        """hash_password should handle special characters."""
        password = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
