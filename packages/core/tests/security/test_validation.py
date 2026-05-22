"""Tests for input validation utilities."""

import pytest

from scenemachine.security.validation import (
    contains_path_traversal,
    is_safe_redirect,
    sanitize_filename,
    sanitize_html,
    sanitize_sql_identifier,
    validate_email,
    validate_url,
)


class TestSanitizeFilename:
    """Tests for filename sanitization."""

    def test_basic_filename(self):
        """Should preserve safe filenames."""
        assert sanitize_filename("document.pdf") == "document.pdf"
        assert sanitize_filename("my_file.txt") == "my_file.txt"

    def test_path_traversal(self):
        """Should remove path traversal attempts."""
        assert ".." not in sanitize_filename("../../../etc/passwd")
        assert ".." not in sanitize_filename("..\\..\\windows\\system32")

    def test_unsafe_characters(self):
        """Should replace unsafe characters."""
        result = sanitize_filename("file<name>.txt")
        assert "<" not in result
        assert ">" not in result

    def test_null_bytes(self):
        """Should remove null bytes."""
        result = sanitize_filename("file\x00name.txt")
        assert "\x00" not in result

    def test_empty_filename(self):
        """Should handle empty filenames."""
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("   ") == "unnamed"

    def test_long_filename(self):
        """Should truncate long filenames."""
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name, max_length=255)
        assert len(result) <= 255
        assert result.endswith(".pdf")

    def test_unicode_filename(self):
        """Should handle unicode filenames."""
        result = sanitize_filename("документ.pdf")
        assert len(result) > 0

    def test_leading_dots(self):
        """Should strip leading dots."""
        result = sanitize_filename("...hidden")
        assert not result.startswith(".")

    def test_windows_reserved(self):
        """Should handle Windows reserved characters."""
        result = sanitize_filename("file:name|test?.txt")
        assert ":" not in result
        assert "|" not in result
        assert "?" not in result


class TestSanitizeHtml:
    """Tests for HTML sanitization."""

    def test_script_tag(self):
        """Should escape script tags."""
        result = sanitize_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_event_handlers(self):
        """Should escape event handlers."""
        result = sanitize_html('<img onerror="alert(1)">')
        assert "onerror=" not in result or "&quot;" in result

    def test_plain_text(self):
        """Should preserve plain text."""
        text = "Hello, World!"
        assert sanitize_html(text) == text

    def test_empty_input(self):
        """Should handle empty input."""
        assert sanitize_html("") == ""
        assert sanitize_html(None) == ""

    def test_ampersand(self):
        """Should escape ampersands."""
        result = sanitize_html("Tom & Jerry")
        assert "&amp;" in result


class TestValidateEmail:
    """Tests for email validation."""

    def test_valid_emails(self):
        """Should accept valid emails."""
        assert validate_email("user@example.com") is True
        assert validate_email("user.name@example.com") is True
        assert validate_email("user+tag@example.com") is True
        assert validate_email("user@sub.domain.com") is True

    def test_invalid_emails(self):
        """Should reject invalid emails."""
        assert validate_email("") is False
        assert validate_email("invalid") is False
        assert validate_email("@example.com") is False
        assert validate_email("user@") is False
        assert validate_email("user@.com") is False
        assert validate_email("user@example") is False

    def test_long_email(self):
        """Should reject very long emails."""
        long_email = "a" * 300 + "@example.com"
        assert validate_email(long_email) is False


class TestValidateUrl:
    """Tests for URL validation."""

    def test_valid_urls(self):
        """Should accept valid URLs."""
        assert validate_url("http://example.com") is True
        assert validate_url("https://example.com") is True
        assert validate_url("https://example.com/path") is True
        assert validate_url("https://example.com:8080") is True

    def test_invalid_urls(self):
        """Should reject invalid URLs."""
        assert validate_url("") is False
        assert validate_url("not-a-url") is False
        assert validate_url("ftp://example.com") is False  # Not in default schemes

    def test_require_https(self):
        """Should enforce HTTPS when required."""
        assert validate_url("http://example.com", require_https=True) is False
        assert validate_url("https://example.com", require_https=True) is True

    def test_custom_schemes(self):
        """Should accept custom schemes."""
        assert validate_url("ftp://example.com", allowed_schemes=["ftp"]) is True

    def test_long_url(self):
        """Should reject very long URLs."""
        long_url = "https://example.com/" + "a" * 3000
        assert validate_url(long_url) is False


class TestIsSafeRedirect:
    """Tests for safe redirect validation."""

    def test_relative_urls(self):
        """Should allow relative URLs."""
        assert is_safe_redirect("/dashboard") is True
        assert is_safe_redirect("/users/123") is True

    def test_protocol_relative(self):
        """Should reject protocol-relative URLs."""
        assert is_safe_redirect("//evil.com/path") is False

    def test_absolute_urls_without_whitelist(self):
        """Should reject absolute URLs without whitelist."""
        assert is_safe_redirect("https://evil.com") is False
        assert is_safe_redirect("http://localhost:8000") is False

    def test_allowed_hosts(self):
        """Should accept URLs to allowed hosts."""
        allowed = ["example.com", "api.example.com"]
        assert is_safe_redirect("https://example.com/path", allowed_hosts=allowed) is True
        assert is_safe_redirect("https://evil.com", allowed_hosts=allowed) is False

    def test_empty_url(self):
        """Should reject empty URLs."""
        assert is_safe_redirect("") is False


class TestContainsPathTraversal:
    """Tests for path traversal detection."""

    def test_basic_traversal(self):
        """Should detect basic path traversal."""
        assert contains_path_traversal("../etc/passwd") is True
        assert contains_path_traversal("..\\windows\\system32") is True

    def test_encoded_traversal(self):
        """Should detect encoded path traversal."""
        assert contains_path_traversal("%2e%2e/etc/passwd") is True

    def test_safe_paths(self):
        """Should allow safe paths."""
        assert contains_path_traversal("/var/www/html") is False
        assert contains_path_traversal("uploads/image.png") is False

    def test_empty_path(self):
        """Should handle empty paths."""
        assert contains_path_traversal("") is False


class TestSanitizeSqlIdentifier:
    """Tests for SQL identifier sanitization."""

    def test_valid_identifiers(self):
        """Should accept valid identifiers."""
        assert sanitize_sql_identifier("users") == "users"
        assert sanitize_sql_identifier("user_roles") == "user_roles"
        assert sanitize_sql_identifier("_private") == "_private"

    def test_invalid_identifiers(self):
        """Should reject invalid identifiers."""
        with pytest.raises(ValueError):
            sanitize_sql_identifier("")

        with pytest.raises(ValueError):
            sanitize_sql_identifier("123table")

        with pytest.raises(ValueError):
            sanitize_sql_identifier("table-name")

        with pytest.raises(ValueError):
            sanitize_sql_identifier("table; DROP TABLE users;--")

    def test_long_identifier(self):
        """Should reject very long identifiers."""
        with pytest.raises(ValueError):
            sanitize_sql_identifier("a" * 200)
