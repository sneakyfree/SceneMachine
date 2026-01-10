"""Input Validation and Sanitization Module.

Provides utilities for validating and sanitizing user input
to prevent security vulnerabilities.
"""

import html
import re
import unicodedata
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

# Regex patterns for validation
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)

URL_PATTERN = re.compile(
    r"^https?://"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
    r"localhost|"
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    r"(?::\d+)?"
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE
)

# Dangerous filename characters
UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Path traversal patterns
PATH_TRAVERSAL_PATTERN = re.compile(r"\.\.[\\/]|[\\/]\.\.")


def sanitize_filename(
    filename: str,
    max_length: int = 255,
    replacement: str = "_",
) -> str:
    """Sanitize a filename for safe filesystem storage.

    Args:
        filename: The original filename
        max_length: Maximum allowed length
        replacement: Character to replace unsafe chars with

    Returns:
        Sanitized filename safe for filesystem use

    Example:
        >>> sanitize_filename("../../../etc/passwd")
        '_etc_passwd'
        >>> sanitize_filename("my<file>.txt")
        'my_file_.txt'
    """
    if not filename:
        return "unnamed"

    # Normalize unicode
    filename = unicodedata.normalize("NFKD", filename)

    # Remove path separators and traversal attempts
    filename = filename.replace("..", replacement)
    filename = filename.replace("/", replacement)
    filename = filename.replace("\\", replacement)

    # Replace unsafe characters
    filename = UNSAFE_FILENAME_CHARS.sub(replacement, filename)

    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")

    # Collapse multiple replacements
    while replacement * 2 in filename:
        filename = filename.replace(replacement * 2, replacement)

    # Ensure reasonable length
    if len(filename) > max_length:
        # Preserve extension if possible
        parts = filename.rsplit(".", 1)
        if len(parts) == 2 and len(parts[1]) <= 10:
            name, ext = parts
            filename = f"{name[:max_length - len(ext) - 1]}.{ext}"
        else:
            filename = filename[:max_length]

    # Fallback if empty
    if not filename or filename == replacement:
        return "unnamed"

    return filename


def sanitize_html(
    text: str,
    allowed_tags: Optional[List[str]] = None,
) -> str:
    """Sanitize HTML to prevent XSS attacks.

    Args:
        text: The input text potentially containing HTML
        allowed_tags: Optional list of allowed HTML tags (default: none)

    Returns:
        Sanitized text with HTML entities escaped

    Example:
        >>> sanitize_html("<script>alert('xss')</script>")
        "&lt;script&gt;alert('xss')&lt;/script&gt;"
    """
    if not text:
        return ""

    # For now, we do simple HTML entity escaping
    # For more complex needs, consider using bleach library
    if allowed_tags is None:
        # Escape all HTML
        return html.escape(text)

    # If allowed_tags specified, would need bleach or similar
    # For security, default to escaping everything
    return html.escape(text)


def validate_email(email: str) -> bool:
    """Validate an email address format.

    Args:
        email: The email address to validate

    Returns:
        True if email format is valid

    Note:
        This only validates format, not deliverability.
    """
    if not email:
        return False

    # Basic length check
    if len(email) > 254:
        return False

    return bool(EMAIL_PATTERN.match(email))


def validate_url(
    url: str,
    require_https: bool = False,
    allowed_schemes: Optional[List[str]] = None,
) -> bool:
    """Validate a URL.

    Args:
        url: The URL to validate
        require_https: If True, only accept HTTPS URLs
        allowed_schemes: List of allowed URL schemes (default: http, https)

    Returns:
        True if URL is valid
    """
    if not url:
        return False

    # Basic length check
    if len(url) > 2048:
        return False

    try:
        parsed = urlparse(url)

        # Check scheme
        if allowed_schemes is None:
            allowed_schemes = ["http", "https"]

        if require_https:
            allowed_schemes = ["https"]

        if parsed.scheme.lower() not in allowed_schemes:
            return False

        # Must have a netloc (domain)
        if not parsed.netloc:
            return False

        return True

    except Exception:
        return False


def is_safe_redirect(
    url: str,
    allowed_hosts: Optional[List[str]] = None,
) -> bool:
    """Check if a URL is safe for redirect.

    Prevents open redirect vulnerabilities.

    Args:
        url: The URL to check
        allowed_hosts: List of allowed hostnames (default: only relative URLs)

    Returns:
        True if URL is safe for redirect
    """
    if not url:
        return False

    # Protocol-relative URLs are NOT safe (//evil.com)
    if url.startswith("//"):
        return False

    # Relative URLs starting with single slash are safe
    if url.startswith("/"):
        return True

    try:
        parsed = urlparse(url)

        # No scheme and no netloc means relative URL
        if not parsed.scheme and not parsed.netloc:
            return True

        # Check against allowed hosts
        if allowed_hosts:
            return parsed.netloc.lower() in [h.lower() for h in allowed_hosts]

        # Without allowed hosts, only allow relative URLs
        return False

    except Exception:
        return False


def contains_path_traversal(path: str) -> bool:
    """Check if a path contains path traversal attempts.

    Args:
        path: The path to check

    Returns:
        True if path contains traversal patterns
    """
    if not path:
        return False

    # Check for .. patterns
    if PATH_TRAVERSAL_PATTERN.search(path):
        return True

    # Check for encoded traversal
    if "%2e%2e" in path.lower() or "%252e" in path.lower():
        return True

    return False


def validate_path(
    path: str,
    base_path: Optional[str] = None,
    must_exist: bool = False,
) -> bool:
    """Validate a file path for security.

    Args:
        path: The path to validate
        base_path: Required base path (prevents traversal outside)
        must_exist: If True, path must exist

    Returns:
        True if path is valid and safe
    """
    if not path:
        return False

    # Check for traversal attempts
    if contains_path_traversal(path):
        return False

    try:
        resolved = Path(path).resolve()

        # Check if within base path
        if base_path:
            base_resolved = Path(base_path).resolve()
            try:
                resolved.relative_to(base_resolved)
            except ValueError:
                return False

        # Check existence if required
        if must_exist and not resolved.exists():
            return False

        return True

    except Exception:
        return False


def sanitize_sql_identifier(identifier: str) -> str:
    """Sanitize a SQL identifier (table/column name).

    Note: This is for edge cases only. Always use parameterized queries
    for values. This is for dynamic table/column names which can't be
    parameterized.

    Args:
        identifier: The identifier to sanitize

    Returns:
        Sanitized identifier safe for SQL

    Raises:
        ValueError: If identifier is invalid
    """
    if not identifier:
        raise ValueError("Empty identifier")

    # Only allow alphanumeric and underscore
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier}")

    # Check length
    if len(identifier) > 128:
        raise ValueError("Identifier too long")

    return identifier
