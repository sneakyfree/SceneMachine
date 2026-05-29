"""
Final coverage batch — settings crypto edge cases, parsers package import,
and the CircuitBreaker open-state status branch.
"""

from scenemachine.models.settings import decrypt_value, encrypt_value
from scenemachine.utils.circuit_breaker import CircuitBreaker, CircuitState


def test_settings_encrypt_decrypt_roundtrip():
    token = encrypt_value("super-secret")
    assert token != "super-secret"
    assert decrypt_value(token) == "super-secret"


def test_settings_decrypt_invalid_returns_empty():
    assert decrypt_value("") == ""
    assert decrypt_value("not-a-valid-fernet-token") == ""


def test_parsers_package_exports():
    import scenemachine.parsers as parsers

    for sym in ("FountainParser", "parse_fountain", "PDFParser", "FDXParser"):
        assert hasattr(parsers, sym)


def test_circuit_breaker_get_status_open_branch():
    cb = CircuitBreaker(name="test-cb")
    cb._transition_to(CircuitState.OPEN)  # sets _opened_at
    status = cb.get_status()
    assert status["name"] == "test-cb"
    assert status["state"] == "open"
    assert "stats" in status


def test_circuit_breaker_state_helpers():
    cb = CircuitBreaker(name="cb2")
    assert cb.is_closed is True
    cb._transition_to(CircuitState.OPEN)
    assert cb.is_open is True
    cb._transition_to(CircuitState.HALF_OPEN)
    assert cb.is_half_open is True
