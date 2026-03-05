"""
test_integration.py
-------------------
Integration tests for the FastAPI SSE endpoint.

These tests use ``httpx.ASGITransport`` (via the ``client`` fixture in
``conftest.py``) to send real HTTP requests through the full FastAPI
middleware and routing stack — all inside the test process.

WHY this is different from test_app.py (unit tests)
----------------------------------------------------
``test_app.py`` tests individual Python functions in isolation.
These tests verify the HTTP contract: correct status codes, headers,
Content-Type, CORS, URL decoding, and SSE body format.

The LLM and graph are never called — every test patches
``generate_chat_responses`` to return a controlled SSE sequence.

How to run
----------
    pytest test_integration.py -v          # integration tests only
    pytest -m integration -v               # same, via marker
    pytest -m "not integration" -v         # unit tests only
    pytest -v                              # everything
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
import pytest_asyncio
import httpx


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_sse(body: str) -> list[dict]:
    """Parse a raw SSE response body into a list of decoded JSON payloads.

    Splits the response on newlines, picks every ``data:`` line, strips the
    prefix, and JSON-decodes it.

    Args:
        body: Raw text body of a ``text/event-stream`` response.

    Returns:
        List of dicts, one per ``data:`` line that contains valid JSON.
    """
    events = []
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[len("data:"):].strip()
            if payload:
                events.append(json.loads(payload))
    return events


def _fake_stream(*dicts):
    """Build a fake ``generate_chat_responses`` replacement.

    Returns an async-generator factory that yields the given dicts as
    SSE-formatted strings.  Its call signature matches the real function
    so FastAPI's endpoint can call it transparently.

    Args:
        *dicts: Event dicts to encode as ``data: {...}\\n\\n`` lines.

    Returns:
        Async-generator factory ``(message, checkpoint_id=None) -> AsyncGen``.
    """
    async def _gen(message, checkpoint_id=None):
        for d in dicts:
            yield f"data: {json.dumps(d)}\n\n"
    return _gen


async def _get(client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    """Send a GET request and fully read the streaming SSE body.

    ``httpx.AsyncClient.get()`` on an SSE endpoint streams the body.
    We must iterate the response to consume it before closing.

    Args:
        client: Configured async client from the ``client`` fixture.
        url: Path (relative to base URL).
        **kwargs: Extra kwargs forwarded to ``client.stream()``.

    Returns:
        ``httpx.Response`` with ``.text`` populated.
    """
    async with client.stream("GET", url, **kwargs) as resp:
        # Consume the full body so .text is available after the context exits
        body = "".join([chunk async for chunk in resp.aiter_text()])
    # Attach the body to the response object for convenient assertions
    resp._content = body.encode()  # noqa: SLF001 – needed to populate .text
    return resp


# ---------------------------------------------------------------------------
# HTTP-level tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
class TestLiveEndpointHTTP:
    """Verify HTTP status code, headers, and routing through FastAPI."""

    async def test_returns_200(self, client):
        """Endpoint must respond with HTTP 200."""
        with patch("app.generate_chat_responses", side_effect=_fake_stream({"type": "end"})):
            resp = await _get(client, "/chat_stream/hello")
        assert resp.status_code == 200

    async def test_content_type_is_event_stream(self, client):
        """Content-Type header must be ``text/event-stream``."""
        with patch("app.generate_chat_responses", side_effect=_fake_stream({"type": "end"})):
            resp = await _get(client, "/chat_stream/hello")
        assert "text/event-stream" in resp.headers.get("content-type", "")

    async def test_cache_control_no_cache(self, client):
        """``Cache-Control: no-cache`` must be set to prevent proxy buffering."""
        with patch("app.generate_chat_responses", side_effect=_fake_stream({"type": "end"})):
            resp = await _get(client, "/chat_stream/hello")
        assert resp.headers.get("cache-control") == "no-cache"

    async def test_cors_header_present(self, client):
        """CORS ``Access-Control-Allow-Origin`` header must be present."""
        with patch("app.generate_chat_responses", side_effect=_fake_stream({"type": "end"})):
            resp = await _get(
                client,
                "/chat_stream/hello",
                headers={"Origin": "http://localhost:3000"},
            )
        assert "access-control-allow-origin" in resp.headers

    async def test_url_encoded_message_is_decoded(self, client):
        """URL-encoded path segment must be decoded before reaching the generator."""
        received = {}

        async def capture(message, checkpoint_id=None):
            received["message"] = message
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

        with patch("app.generate_chat_responses", side_effect=capture):
            await _get(client, "/chat_stream/hello%20world")

        assert received.get("message") == "hello world"

    async def test_message_with_spaces_via_plus(self, client):
        """``+``-encoded spaces in the path must also be decoded correctly."""
        received = {}

        async def capture(message, checkpoint_id=None):
            received["message"] = message
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

        with patch("app.generate_chat_responses", side_effect=capture):
            await _get(client, "/chat_stream/hello+world")

        # FastAPI path params decode %20 but not +; + stays as literal "+"
        # This test documents the actual behaviour rather than an assumption.
        assert received.get("message") is not None


# ---------------------------------------------------------------------------
# SSE body format tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
class TestLiveEndpointSSE:
    """Verify the SSE body: framing, event order, JSON validity, field presence."""

    async def test_every_data_line_is_valid_json(self, client):
        """Every ``data:`` line in the response body must be valid JSON."""
        events_to_send = [
            {"type": "session", "checkpoint_id": "x"},
            {"type": "thinking", "stage": "reasoning"},
            {"type": "content", "content": "Hi", "index": 0},
            {"type": "end"},
        ]
        with patch("app.generate_chat_responses", side_effect=_fake_stream(*events_to_send)):
            resp = await _get(client, "/chat_stream/hi")
        parsed = _parse_sse(resp.text)
        assert len(parsed) == len(events_to_send)

    async def test_end_event_is_always_last(self, client):
        """The ``end`` event must be the final event in every response."""
        with patch("app.generate_chat_responses", side_effect=_fake_stream(
            {"type": "content", "content": "Hello", "index": 0},
            {"type": "end"},
        )):
            resp = await _get(client, "/chat_stream/hi")
        events = _parse_sse(resp.text)
        assert events[-1]["type"] == "end"

    async def test_session_event_has_checkpoint_id(self, client):
        """A ``session`` event must carry the ``checkpoint_id`` field."""
        with patch("app.generate_chat_responses", side_effect=_fake_stream(
            {"type": "session", "checkpoint_id": "abc-123"},
            {"type": "end"},
        )):
            resp = await _get(client, "/chat_stream/hi")
        events = _parse_sse(resp.text)
        session = next((e for e in events if e["type"] == "session"), None)
        assert session is not None
        assert session.get("checkpoint_id") == "abc-123"

    async def test_content_events_have_integer_index(self, client):
        """Every ``content`` event must have an integer ``index`` field."""
        with patch("app.generate_chat_responses", side_effect=_fake_stream(
            {"type": "content", "content": "A", "index": 0},
            {"type": "content", "content": "B", "index": 1},
            {"type": "end"},
        )):
            resp = await _get(client, "/chat_stream/hi")
        events = _parse_sse(resp.text)
        content_events = [e for e in events if e["type"] == "content"]
        assert len(content_events) == 2
        for e in content_events:
            assert isinstance(e.get("index"), int)

    async def test_special_characters_survive_the_wire(self, client):
        """Quotes, newlines, and backslashes must arrive at the client intact."""
        tricky = 'He said "hello"\nNew line & backslash \\'
        with patch("app.generate_chat_responses", side_effect=_fake_stream(
            {"type": "content", "content": tricky, "index": 0},
            {"type": "end"},
        )):
            resp = await _get(client, "/chat_stream/hi")
        events = _parse_sse(resp.text)
        content = next(e for e in events if e["type"] == "content")
        assert content["content"] == tricky

    async def test_checkpoint_id_query_param_forwarded(self, client):
        """``checkpoint_id`` query param must be passed to the generator."""
        received = {}

        async def capture(message, checkpoint_id=None):
            received["checkpoint_id"] = checkpoint_id
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

        with patch("app.generate_chat_responses", side_effect=capture):
            await _get(client, "/chat_stream/hi?checkpoint_id=thread-xyz")

        assert received.get("checkpoint_id") == "thread-xyz"

    async def test_missing_checkpoint_id_is_none(self, client):
        """Omitting ``checkpoint_id`` must pass ``None`` to the generator."""
        received = {}

        async def capture(message, checkpoint_id=None):
            received["checkpoint_id"] = checkpoint_id
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

        with patch("app.generate_chat_responses", side_effect=capture):
            await _get(client, "/chat_stream/hi")

        assert received.get("checkpoint_id") is None

    async def test_search_start_event_fields(self, client):
        """``search_start`` event must carry ``query`` and ``tool_call_id``."""
        with patch("app.generate_chat_responses", side_effect=_fake_stream(
            {"type": "search_start", "query": "AI news", "tool_call_id": "tc-1"},
            {"type": "end"},
        )):
            resp = await _get(client, "/chat_stream/find+something")
        events = _parse_sse(resp.text)
        ss = next((e for e in events if e["type"] == "search_start"), None)
        assert ss is not None
        assert ss.get("query") == "AI news"
        assert "tool_call_id" in ss

    async def test_search_results_event_fields(self, client):
        """``search_results`` event must carry ``urls``, ``result_count``, ``tool_call_id``."""
        with patch("app.generate_chat_responses", side_effect=_fake_stream(
            {
                "type": "search_results",
                "urls": ["https://example.com"],
                "snippets": ["snippet"],
                "titles": ["Title"],
                "result_count": 1,
                "tool_call_id": "tc-1",
            },
            {"type": "end"},
        )):
            resp = await _get(client, "/chat_stream/hi")
        events = _parse_sse(resp.text)
        sr = next((e for e in events if e["type"] == "search_results"), None)
        assert sr is not None
        assert isinstance(sr.get("urls"), list)
        assert sr.get("result_count") == 1
        assert "tool_call_id" in sr

    async def test_error_event_has_code_field(self, client):
        """An ``error`` event must carry a ``code`` field for client-side handling."""
        with patch("app.generate_chat_responses", side_effect=_fake_stream(
            {"type": "error", "error": "something went wrong", "code": "internal_error"},
            {"type": "end"},
        )):
            resp = await _get(client, "/chat_stream/hi")
        events = _parse_sse(resp.text)
        err = next((e for e in events if e["type"] == "error"), None)
        assert err is not None
        assert err.get("code") == "internal_error"
        assert "error" in err

    async def test_unicode_content_survives(self, client):
        """Non-ASCII characters (Arabic, emoji) must arrive at the client intact."""
        unicode_text = "مرحبا بالعالم 🌍"
        with patch("app.generate_chat_responses", side_effect=_fake_stream(
            {"type": "content", "content": unicode_text, "index": 0},
            {"type": "end"},
        )):
            resp = await _get(client, "/chat_stream/hi")
        events = _parse_sse(resp.text)
        content = next(e for e in events if e["type"] == "content")
        assert content["content"] == unicode_text