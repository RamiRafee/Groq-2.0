"""
test_app.py
-----------
pytest test suite for app.py.

What is tested (no real API calls — everything is mocked):
    1. SSE helpers    – _sse(), _serialise_chunk(), _build_config()
    2. Search parser  – _from_search_output()
    3. Streaming gen  – generate_chat_responses() event sequence
    4. HTTP endpoint  – GET /chat_stream/{message} via FastAPI TestClient

Running
-------
    # from the project root:
    pytest                         # run all tests
    pytest -v                      # verbose (shows each test name)
    pytest -v test_app.py          # this file only
    pytest -k "test_sse"           # run tests whose name contains "test_sse"

VSCode setup (one-time)
-----------------------
1. Open the Command Palette  →  "Python: Configure Tests"
2. Choose  pytest
3. Choose  . (root folder)
4. A flask/beaker icon appears in the Activity Bar — click it to open the
   Test Explorer, run individual tests, and see pass/fail inline in the editor.
"""

from __future__ import annotations

import json
import sys
import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# ---------------------------------------------------------------------------
# Make the project root importable regardless of how pytest is invoked
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_chunk_str():
    """A mock AI message chunk whose content is a plain string."""
    chunk = MagicMock()
    chunk.content = "Hello!"
    return chunk


@pytest.fixture()
def fake_chunk_blocks():
    """A mock AI message chunk whose content is a list of typed blocks."""
    chunk = MagicMock()
    chunk.content = [
        {"type": "text", "text": "Block "},
        {"type": "text", "text": "content"},
        {"type": "tool_use", "id": "x"},  # should be ignored
    ]
    return chunk


@pytest.fixture()
def fake_chunk_empty():
    """A mock AI message chunk with no text (pure tool-call delta)."""
    chunk = MagicMock()
    chunk.content = ""
    return chunk


@pytest.fixture()
def search_results_list():
    """Realistic Tavily search output (list of result dicts)."""
    return [
        {"url": "https://example.com/a", "content": "snippet A", "title": "Title A"},
        {"url": "https://example.com/b", "content": "snippet B", "title": "Title B"},
    ]


# ---------------------------------------------------------------------------
# 1. _sse() — SSE serialisation helper
# ---------------------------------------------------------------------------


class TestSseHelper:
    """Tests for the _sse() serialisation helper."""

    def test_produces_correct_prefix(self):
        """Output must start with 'data: '."""
        from app import _sse
        assert _sse({"type": "end"}).startswith("data: ")

    def test_produces_correct_suffix(self):
        """Output must end with the SSE double-newline separator."""
        from app import _sse
        assert _sse({"type": "end"}).endswith("\n\n")

    def test_payload_is_valid_json(self):
        """The JSON between 'data: ' and '\\n\\n' must be parseable."""
        from app import _sse
        raw = _sse({"type": "content", "content": "hi"})
        payload = json.loads(raw[len("data: "):-2])
        assert payload == {"type": "content", "content": "hi"}

    def test_escapes_special_characters(self):
        """Quotes, newlines and backslashes inside values must be escaped."""
        from app import _sse
        raw = _sse({"msg": 'say "hello"\nworld'})
        # Must still be valid JSON — json.loads will raise if not
        payload = json.loads(raw[len("data: "):-2])
        assert payload["msg"] == 'say "hello"\nworld'

    def test_handles_unicode(self):
        """Non-ASCII characters must survive the round-trip."""
        from app import _sse
        raw = _sse({"text": "مرحبا 🌍"})
        payload = json.loads(raw[len("data: "):-2])
        assert payload["text"] == "مرحبا 🌍"


# ---------------------------------------------------------------------------
# 2. _serialise_chunk() — chunk content extractor
# ---------------------------------------------------------------------------


class TestSerialiseChunk:
    """Tests for the _serialise_chunk() helper."""

    def test_plain_string_content(self, fake_chunk_str):
        """String content is returned unchanged."""
        from app import _serialise_chunk
        assert _serialise_chunk(fake_chunk_str) == "Hello!"

    def test_block_list_content(self, fake_chunk_blocks):
        """Text blocks are concatenated; non-text blocks are ignored."""
        from app import _serialise_chunk
        assert _serialise_chunk(fake_chunk_blocks) == "Block content"

    def test_empty_string_content(self, fake_chunk_empty):
        """Empty string content returns empty string."""
        from app import _serialise_chunk
        assert _serialise_chunk(fake_chunk_empty) == ""

    def test_none_content_returns_empty(self):
        """None content (edge case) should return empty string."""
        from app import _serialise_chunk
        chunk = MagicMock()
        chunk.content = None
        assert _serialise_chunk(chunk) == ""


# ---------------------------------------------------------------------------
# 3. _build_config() — LangGraph config builder
# ---------------------------------------------------------------------------


class TestBuildConfig:
    """Tests for the _build_config() helper."""

    def test_returns_dict_with_thread_id(self):
        """Config must contain configurable.thread_id equal to the input."""
        from app import _build_config
        cfg = _build_config("my-thread-42")
        assert cfg == {"configurable": {"thread_id": "my-thread-42"}}

    def test_different_ids_produce_different_configs(self):
        """Two different thread IDs must not produce the same config."""
        from app import _build_config
        assert _build_config("a") != _build_config("b")


# ---------------------------------------------------------------------------
# 4. _from_search_output() — search result event builder
# ---------------------------------------------------------------------------


class TestFromSearchOutput:
    """Tests for the _from_search_output() helper."""

    def _parse(self, raw: str) -> dict:
        """Parse an SSE string into a dict for assertions."""
        return json.loads(raw[len("data: "):-2])

    def test_valid_list_produces_search_results_event(self, search_results_list):
        """A valid Tavily list produces a search_results event."""
        from app import _from_search_output
        payload = self._parse(_from_search_output(search_results_list, "call-1"))
        assert payload["type"] == "search_results"

    def test_extracts_urls(self, search_results_list):
        from app import _from_search_output
        payload = self._parse(_from_search_output(search_results_list, "call-1"))
        assert payload["urls"] == ["https://example.com/a", "https://example.com/b"]

    def test_extracts_snippets(self, search_results_list):
        from app import _from_search_output
        payload = self._parse(_from_search_output(search_results_list, "call-1"))
        assert payload["snippets"] == ["snippet A", "snippet B"]

    def test_extracts_titles(self, search_results_list):
        from app import _from_search_output
        payload = self._parse(_from_search_output(search_results_list, "call-1"))
        assert payload["titles"] == ["Title A", "Title B"]

    def test_result_count_matches_urls(self, search_results_list):
        from app import _from_search_output
        payload = self._parse(_from_search_output(search_results_list, "call-1"))
        assert payload["result_count"] == len(search_results_list)

    def test_tool_call_id_is_preserved(self, search_results_list):
        from app import _from_search_output
        payload = self._parse(_from_search_output(search_results_list, "my-id"))
        assert payload["tool_call_id"] == "my-id"

    def test_non_list_output_produces_search_error(self):
        """Non-list output (e.g. a string error) must produce a search_error."""
        from app import _from_search_output
        payload = self._parse(_from_search_output("unexpected string", "call-x"))
        assert payload["type"] == "search_error"
        assert "tool_call_id" in payload

    def test_empty_list_produces_zero_results(self):
        from app import _from_search_output
        payload = self._parse(_from_search_output([], "call-0"))
        assert payload["type"] == "search_results"
        assert payload["result_count"] == 0
        assert payload["urls"] == []

    def test_items_missing_fields_are_skipped_gracefully(self):
        """Items without url/content/title should not crash; others still extracted."""
        from app import _from_search_output
        output = [
            {"url": "https://good.com", "content": "ok", "title": "Good"},
            {"only_irrelevant_key": "value"},   # ← missing all expected fields
        ]
        payload = self._parse(_from_search_output(output, "call-2"))
        assert payload["urls"] == ["https://good.com"]
        assert payload["result_count"] == 1


# ---------------------------------------------------------------------------
# 5. generate_chat_responses() — streaming generator (mocked graph)
# ---------------------------------------------------------------------------


async def _collect(gen: AsyncGenerator) -> list[dict]:
    """Drain an async SSE generator and return parsed payloads."""
    events = []
    async for raw in gen:
        if raw.startswith("data: "):
            events.append(json.loads(raw[len("data: "):-2]))
    return events


def _make_fake_events(*event_dicts):
    """Return an async iterable of fake LangGraph event dicts."""
    async def _gen():
        for e in event_dicts:
            yield e
    return _gen()


@pytest.mark.asyncio
class TestGenerateChatResponses:
    """Tests for generate_chat_responses() with the graph mocked out."""

    async def test_new_conversation_emits_session_event(self):
        """First turn (no checkpoint_id) must emit a session event first."""
        from app import generate_chat_responses

        async def fake_stream(*_, **__):
            return
            yield  # make it an async generator

        with patch("app.graph") as mock_graph:
            mock_graph.astream_events.return_value = fake_stream()
            events = await _collect(generate_chat_responses("hi", checkpoint_id=None))

        types = [e["type"] for e in events]
        assert "session" in types
        assert types[0] == "session"

    async def test_session_event_contains_checkpoint_id(self):
        from app import generate_chat_responses

        async def fake_stream(*_, **__):
            return
            yield

        with patch("app.graph") as mock_graph:
            mock_graph.astream_events.return_value = fake_stream()
            events = await _collect(generate_chat_responses("hi"))

        session = next(e for e in events if e["type"] == "session")
        assert "checkpoint_id" in session
        assert len(session["checkpoint_id"]) > 0

    async def test_existing_conversation_no_session_event(self):
        """Continuing a conversation must NOT emit a session event."""
        from app import generate_chat_responses

        async def fake_stream(*_, **__):
            return
            yield

        with patch("app.graph") as mock_graph:
            mock_graph.astream_events.return_value = fake_stream()
            events = await _collect(
                generate_chat_responses("hi", checkpoint_id="existing-id")
            )

        types = [e["type"] for e in events]
        assert "session" not in types

    async def test_always_ends_with_end_event(self):
        """The last event must always be type=end."""
        from app import generate_chat_responses

        async def fake_stream(*_, **__):
            return
            yield

        with patch("app.graph") as mock_graph:
            mock_graph.astream_events.return_value = fake_stream()
            events = await _collect(generate_chat_responses("hi"))

        assert events[-1]["type"] == "end"

    async def test_on_chat_model_start_emits_thinking(self):
        """on_chat_model_start graph event → thinking SSE event."""
        from app import generate_chat_responses

        fake_events = [{"event": "on_chat_model_start", "name": "model", "data": {}}]

        async def fake_stream(*_, **__):
            for e in fake_events:
                yield e

        with patch("app.graph") as mock_graph:
            mock_graph.astream_events.return_value = fake_stream()
            events = await _collect(generate_chat_responses("hi"))

        types = [e["type"] for e in events]
        assert "thinking" in types

    async def test_on_chat_model_stream_emits_content(self):
        """on_chat_model_stream with text → content SSE event."""
        from app import generate_chat_responses

        chunk = MagicMock()
        chunk.content = "Hello world"

        fake_events = [
            {"event": "on_chat_model_stream", "name": "model", "data": {"chunk": chunk}}
        ]

        async def fake_stream(*_, **__):
            for e in fake_events:
                yield e

        with patch("app.graph") as mock_graph:
            mock_graph.astream_events.return_value = fake_stream()
            events = await _collect(generate_chat_responses("hi"))

        content_events = [e for e in events if e["type"] == "content"]
        assert len(content_events) == 1
        assert content_events[0]["content"] == "Hello world"
        assert content_events[0]["index"] == 0

    async def test_content_index_increments(self):
        """Each successive content chunk must have an incrementing index."""
        from app import generate_chat_responses

        def _chunk(text):
            c = MagicMock()
            c.content = text
            return c

        fake_events = [
            {"event": "on_chat_model_stream", "name": "m", "data": {"chunk": _chunk("A")}},
            {"event": "on_chat_model_stream", "name": "m", "data": {"chunk": _chunk("B")}},
            {"event": "on_chat_model_stream", "name": "m", "data": {"chunk": _chunk("C")}},
        ]

        async def fake_stream(*_, **__):
            for e in fake_events:
                yield e

        with patch("app.graph") as mock_graph:
            mock_graph.astream_events.return_value = fake_stream()
            events = await _collect(generate_chat_responses("hi"))

        content_events = [e for e in events if e["type"] == "content"]
        assert [e["index"] for e in content_events] == [0, 1, 2]

    async def test_empty_chunk_not_emitted(self):
        """Chunks with no text (tool-call deltas) must not produce content events."""
        from app import generate_chat_responses

        chunk = MagicMock()
        chunk.content = ""

        fake_events = [
            {"event": "on_chat_model_stream", "name": "m", "data": {"chunk": chunk}}
        ]

        async def fake_stream(*_, **__):
            for e in fake_events:
                yield e

        with patch("app.graph") as mock_graph:
            mock_graph.astream_events.return_value = fake_stream()
            events = await _collect(generate_chat_responses("hi"))

        assert not any(e["type"] == "content" for e in events)

    async def test_tool_call_emits_tool_start_and_search_start(self):
        """on_chat_model_end with a Tavily call → tool_start + search_start."""
        from app import generate_chat_responses

        output = MagicMock()
        output.tool_calls = [
            {"name": "tavily_search_results_json", "id": "tc-1", "args": {"query": "AI news"}}
        ]

        fake_events = [
            {"event": "on_chat_model_end", "name": "model", "data": {"output": output}}
        ]

        async def fake_stream(*_, **__):
            for e in fake_events:
                yield e

        with patch("app.graph") as mock_graph:
            mock_graph.astream_events.return_value = fake_stream()
            events = await _collect(generate_chat_responses("hi"))

        types = [e["type"] for e in events]
        assert "tool_start" in types
        assert "search_start" in types

        search_start = next(e for e in events if e["type"] == "search_start")
        assert search_start["query"] == "AI news"

    async def test_on_tool_end_search_emits_search_results(self):
        """on_tool_end for Tavily → tool_end + search_results SSE events."""
        from app import generate_chat_responses

        search_output = [
            {"url": "https://example.com", "content": "snippet", "title": "Ex"}
        ]

        fake_events = [
            {
                "event": "on_tool_end",
                "name": "tavily_search_results_json",
                "run_id": "run-1",
                "data": {"output": search_output},
            }
        ]

        async def fake_stream(*_, **__):
            for e in fake_events:
                yield e

        with patch("app.graph") as mock_graph:
            mock_graph.astream_events.return_value = fake_stream()
            events = await _collect(generate_chat_responses("hi"))

        types = [e["type"] for e in events]
        assert "tool_end" in types
        assert "search_results" in types

        sr = next(e for e in events if e["type"] == "search_results")
        assert "https://example.com" in sr["urls"]

    async def test_exception_emits_error_event_then_end(self):
        """An exception inside the graph stream → error event, then end."""
        from app import generate_chat_responses

        async def boom(*_, **__):
            raise RuntimeError("network failure")
            yield  # make it an async generator

        with patch("app.graph") as mock_graph:
            mock_graph.astream_events.side_effect = RuntimeError("network failure")
            events = await _collect(generate_chat_responses("hi"))

        types = [e["type"] for e in events]
        assert "error" in types
        assert types[-1] == "end"

        err = next(e for e in events if e["type"] == "error")
        assert err["code"] == "internal_error"
        assert "network failure" in err["error"]


# ---------------------------------------------------------------------------
# 6. HTTP endpoint — GET /chat_stream/{message}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestChatStreamEndpoint:
    """Integration-level tests for the FastAPI endpoint (no real LLM calls)."""

    async def test_returns_200(self):
        """Endpoint must return HTTP 200."""
        from app import app

        async def fake_gen(*_, **__):
            yield 'data: {"type": "end"}\n\n'

        with patch("app.generate_chat_responses", side_effect=fake_gen):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/chat_stream/hello")
        assert resp.status_code == 200

    async def test_content_type_is_event_stream(self):
        """Content-Type header must be text/event-stream."""
        from app import app

        async def fake_gen(*_, **__):
            yield 'data: {"type": "end"}\n\n'

        with patch("app.generate_chat_responses", side_effect=fake_gen):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/chat_stream/hello")
        assert "text/event-stream" in resp.headers["content-type"]

    async def test_message_forwarded_to_generator(self):
        """The path segment must be passed as the message argument."""
        from app import app

        received = {}

        async def fake_gen(message, checkpoint_id=None):
            received["message"] = message
            yield 'data: {"type": "end"}\n\n'

        with patch("app.generate_chat_responses", side_effect=fake_gen):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.get("/chat_stream/test-message")

        assert received["message"] == "test-message"

    async def test_checkpoint_id_forwarded_to_generator(self):
        """checkpoint_id query param must be forwarded to the generator."""
        from app import app

        received = {}

        async def fake_gen(message, checkpoint_id=None):
            received["checkpoint_id"] = checkpoint_id
            yield 'data: {"type": "end"}\n\n'

        with patch("app.generate_chat_responses", side_effect=fake_gen):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.get("/chat_stream/hi?checkpoint_id=abc-123")

        assert received["checkpoint_id"] == "abc-123"

    async def test_missing_checkpoint_id_defaults_to_none(self):
        """Omitting checkpoint_id must pass None to the generator."""
        from app import app

        received = {}

        async def fake_gen(message, checkpoint_id=None):
            received["checkpoint_id"] = checkpoint_id
            yield 'data: {"type": "end"}\n\n'

        with patch("app.generate_chat_responses", side_effect=fake_gen):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.get("/chat_stream/hi")

        assert received["checkpoint_id"] is None

    async def test_cache_control_header_present(self):
        """Cache-Control: no-cache must be set to prevent proxy buffering."""
        from app import app

        async def fake_gen(*_, **__):
            yield 'data: {"type": "end"}\n\n'

        with patch("app.generate_chat_responses", side_effect=fake_gen):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/chat_stream/hello")
        assert resp.headers.get("cache-control") == "no-cache"
