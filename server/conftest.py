"""
conftest.py
-----------
Shared pytest fixtures for the project.

WHY in-process (ASGITransport) instead of subprocess uvicorn
-------------------------------------------------------------
The subprocess approach had one fundamental flaw: ``unittest.mock.patch``
only affects the **current process**.  When the server runs as a separate
subprocess, patches applied in the test process have zero effect on the
server's memory — so ``generate_chat_responses`` was never replaced, the
real LLM code ran, and every test timed out waiting for a real API response.

The correct approach for testing FastAPI + SSE is ``httpx.ASGITransport``:
it wraps the FastAPI ``app`` object and dispatches requests through the
full ASGI middleware/routing stack **inside the test process**.  Because
everything is in-process, ``patch("app.generate_chat_responses")`` works
exactly as expected.

What ASGITransport tests that pure unit tests (test_app.py) don't
-----------------------------------------------------------------
- Real FastAPI routing resolves path segments and query params
- Real CORS middleware adds the ``Access-Control-Allow-Origin`` header
- Real ``StreamingResponse`` sets ``Content-Type: text/event-stream``
- Real response headers (Cache-Control, X-Accel-Buffering) are verified
- URL decoding of the ``{message}`` path segment is exercised
- The full request/response lifecycle runs through every middleware layer
"""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

# Import the compiled FastAPI app from app.py.
# ``graph`` is built at module level when app.py is imported; that's fine
# because our tests patch ``generate_chat_responses`` (not the graph itself),
# so no real LLM calls are ever made.
from app import app as fastapi_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def client():
    """Async HTTP client that talks to the FastAPI app in-process.

    Uses ``httpx.ASGITransport`` to route requests directly through the
    ASGI app — no TCP socket, no subprocess, no port binding required.
    All middleware (CORS, routing) runs exactly as in production.

    Because this is in-process, ``unittest.mock.patch("app.xyz")`` works
    correctly in every test that uses this fixture.

    Yields:
        httpx.AsyncClient: Configured client for the test.
    """
    transport = httpx.ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",   # dummy base URL required by httpx
        timeout=httpx.Timeout(30.0),    # generous timeout for SSE streams
    ) as c:
        yield c