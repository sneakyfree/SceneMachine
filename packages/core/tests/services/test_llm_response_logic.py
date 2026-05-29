"""
Pure-logic tests for the LLM service's response parsing + MockBackend.

No real API calls — LLMResponse.parse_json is pure, and MockBackend is the
project's own testing backend (canned + keyword-generated responses).
"""

import pytest

from scenemachine.services.llm.service import LLMProvider, LLMResponse, MockBackend


def _resp(content):
    return LLMResponse(content=content, model="m", provider=LLMProvider.MOCK)


def test_parse_json_bare_object():
    assert _resp('{"a": 1, "b": [2, 3]}').parse_json() == {"a": 1, "b": [2, 3]}


def test_parse_json_markdown_fenced():
    assert _resp('```json\n{"x": true}\n```').parse_json() == {"x": True}
    assert _resp('```\n{"y": 5}\n```').parse_json() == {"y": 5}


def test_parse_json_bare_array():
    assert _resp("[1, 2, 3]").parse_json() == [1, 2, 3]


def test_parse_json_prose_prefixed_object():
    # Prose before the object (no trailing text) → extracted from first '{'.
    assert _resp('Sure, here it is: {"ok": 1}').parse_json() == {"ok": 1}


def test_parse_json_invalid_returns_none():
    assert _resp("not json at all").parse_json() is None
    assert _resp('{"trailing": 1} and extra prose').parse_json() is None


async def test_mock_backend_custom_response_and_history():
    backend = MockBackend(responses={"hello": '{"greeting": "hi"}'})
    resp = await backend.complete(
        messages=[{"role": "user", "content": "say HELLO please"}],
        system="be brief",
        temperature=0.5,
    )
    assert resp.parse_json() == {"greeting": "hi"}
    assert resp.provider == LLMProvider.MOCK
    # call_history records the invocation
    assert len(backend.call_history) == 1
    assert backend.call_history[0]["system"] == "be brief"
    assert backend.call_history[0]["temperature"] == 0.5


async def test_mock_backend_default_analyze_response_is_parseable():
    backend = MockBackend()
    resp = await backend.complete(
        messages=[{"role": "user", "content": "Please analyze this scene"}]
    )
    # The default mock generates JSON for analyze-type prompts.
    assert resp.parse_json() is not None


async def test_mock_backend_picks_last_user_message():
    backend = MockBackend(responses={"target": "matched"})
    resp = await backend.complete(
        messages=[
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "ignored"},
            {"role": "user", "content": "the TARGET one"},
        ]
    )
    assert resp.content == "matched"


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
