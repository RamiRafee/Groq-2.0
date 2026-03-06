"""
app.py
--------
A conversational AI agent built with LangGraph that supports tool use (web search)
and persistent memory across turns. The agent uses a Groq-hosted LLaMA model and
routes between a language model node and a tool execution node based on whether
the model emits tool calls.

Graph topology:
    START → model → [tool_node → model]* → END

The model node invokes the LLM; if it requests tool calls the graph routes to
tool_node, executes each tool, and feeds results back to the model.  This loop
repeats until the model produces a plain (non-tool-call) response.

Dependencies:
    pip install langgraph langchain-groq langchain-community python-dotenv
"""



from __future__ import annotations

import json
import logging
from typing import Annotated, Optional, TypedDict, AsyncGenerator
from uuid import uuid4

from dotenv import load_dotenv
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph, add_messages
from typing_extensions import TypedDict
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

load_dotenv()
"""Load API keys (GROQ_API_KEY, TAVILY_API_KEY, etc.) from a .env file.

Requires a .env file in the working directory or the variables to already be
present in the shell environment.
"""

# ---------------------------------------------------------------------------
# Constants / configuration
# ---------------------------------------------------------------------------

MODEL_NAME: str = "llama-3.3-70b-versatile"
"""Groq model identifier.  Swap this string to change the underlying LLM."""

MAX_SEARCH_RESULTS: int = 4
"""Maximum number of web-search results returned per Tavily query."""

# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------


class State(TypedDict):
    """Typed state that flows through every node in the LangGraph graph.

    Attributes:
        messages: Accumulated conversation history.  The ``add_messages``
            reducer appends new messages rather than replacing the list,
            which preserves the full dialogue context across graph steps.
    """

    messages: Annotated[list, add_messages]


# ---------------------------------------------------------------------------
# LLM & tools
# ---------------------------------------------------------------------------


def build_llm(model_name: str = MODEL_NAME) -> ChatGroq:
    """Instantiate the Groq-hosted chat model.

    Args:
        model_name: Groq model identifier string.

    Returns:
        A ``ChatGroq`` client ready for inference.
    """
    logger.info("Loading LLM: %s", model_name)
    return ChatGroq(model=model_name)


def build_search_tool(max_results: int = MAX_SEARCH_RESULTS) -> TavilySearchResults:
    """Create the Tavily web-search tool.

    Args:
        max_results: Upper bound on the number of search results per query.

    Returns:
        A configured ``TavilySearchResults`` tool instance.
    """
    logger.info("Initialising Tavily search tool (max_results=%d)", max_results)
    return TavilySearchResults(max_results=max_results)


# ---------------------------------------------------------------------------
# Node factories
# ---------------------------------------------------------------------------


def make_model_node(llm_with_tools: ChatGroq):
    """Return an async graph node that invokes the LLM with bound tools.

    The returned coroutine accepts the current graph state, calls the LLM with
    the full message history, and appends the model's response to ``messages``.

    Args:
        llm_with_tools: An LLM instance that has tools bound via
            ``model.bind_tools(tools)``.

    Returns:
        An async callable ``model_node(state: State) -> dict`` suitable for
        ``StateGraph.add_node``.
    """

    async def model_node(state: State) -> dict:
        """Invoke the LLM and return its response as a state update.

        Args:
            state: Current graph state containing the conversation history.

        Returns:
            A partial state dict ``{"messages": [ai_message]}`` that is merged
            into the graph state by the ``add_messages`` reducer.
        """
        logger.debug("model_node invoked with %d messages", len(state["messages"]))
        result = await llm_with_tools.ainvoke(state["messages"])
        logger.debug("model_node received response type: %s", type(result).__name__)
        return {"messages": [result]}

    return model_node


def make_tool_node(tool_registry: dict[str, TavilySearchResults]):
    """Return an async graph node that dispatches tool calls to their handlers.

    The returned coroutine reads the tool calls embedded in the last AI message,
    executes each one using the appropriate tool from *tool_registry*, and
    returns a list of ``ToolMessage`` objects for the LLM to continue from.

    Args:
        tool_registry: Mapping of tool name → tool instance.  Any tool name
            that appears in an AI tool-call must have an entry here.

    Returns:
        An async callable ``tool_node(state: State) -> dict`` suitable for
        ``StateGraph.add_node``.

    Raises:
        KeyError: (at runtime) if the LLM requests a tool that is not
            present in *tool_registry*.
    """

    async def tool_node(state: State) -> dict:
        """Execute all pending tool calls and return their results.

        Iterates over every tool call in the last AI message, looks up the
        matching tool in the registry, executes it asynchronously, and wraps
        the result in a ``ToolMessage`` so the LLM can consume it.

        Args:
            state: Current graph state.  The last message must be an
                ``AIMessage`` with one or more ``tool_calls``.

        Returns:
            A partial state dict ``{"messages": [tool_message, ...]}`` that
            is merged into the graph state by the ``add_messages`` reducer.
        """
        last_message = state["messages"][-1]
        tool_calls = last_message.tool_calls  # list of {name, args, id}

        logger.info("tool_node processing %d tool call(s)", len(tool_calls))

        tool_messages: list[ToolMessage] = []

        for tool_call in tool_calls:
            tool_name: str = tool_call["name"]
            tool_args: dict = tool_call["args"]
            tool_id: str = tool_call["id"]

            logger.debug("Executing tool '%s' with args: %s", tool_name, tool_args)

            if tool_name not in tool_registry:
                # Surface unknown tool calls as error messages so the LLM can
                # recover gracefully instead of raising an unhandled exception.
                error_content = (
                    f"Tool '{tool_name}' is not available.  "
                    f"Available tools: {list(tool_registry.keys())}"
                )
                logger.warning("Unknown tool requested: %s", tool_name)
                tool_messages.append(
                    ToolMessage(
                        content=error_content,
                        tool_call_id=tool_id,
                        name=tool_name,
                    )
                )
                continue

            # Execute the tool and capture its output
            tool_instance = tool_registry[tool_name]
            search_results = await tool_instance.ainvoke(tool_args)

            logger.debug(
                "Tool '%s' returned %d result(s)",
                tool_name,
                len(search_results) if isinstance(search_results, list) else 1,
            )

            tool_messages.append(
                ToolMessage(
                    content=str(search_results),
                    tool_call_id=tool_id,
                    name=tool_name,
                )
            )

        return {"messages": tool_messages}

    return tool_node


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


async def tools_router(state: State) -> str:
    """Conditional edge: decide whether to call tools or finish the turn.

    Inspects the last message in the state.  If it contains unresolved tool
    calls the graph routes to ``tool_node``; otherwise the conversation ends.

    Args:
        state: Current graph state.

    Returns:
        ``"tool_node"`` when the model has emitted tool calls that must be
        resolved, or ``END`` when the model's response requires no further
        action.
    """
    last_message = state["messages"][-1]
    has_tool_calls = hasattr(last_message, "tool_calls") and bool(last_message.tool_calls)

    if has_tool_calls:
        logger.debug("tools_router → tool_node (%d call(s))", len(last_message.tool_calls))
        return "tool_node"

    logger.debug("tools_router → END")
    return END


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_graph(
    model_name: str = MODEL_NAME,
    max_search_results: int = MAX_SEARCH_RESULTS,
) -> StateGraph:
    """Assemble and compile the LangGraph agent graph.

    Creates all components (LLM, tools, nodes, edges) and wires them together
    into a compiled graph with in-memory checkpointing so conversation history
    persists across invocations within the same process.

    Args:
        model_name: Groq model identifier to use for the LLM node.
        max_search_results: Maximum Tavily search results per query.

    Returns:
        A compiled ``StateGraph`` ready to be invoked or streamed.

    Graph structure::

        START → model ──(no tool calls)──→ END
                  ↑                         
                  └──── tool_node ←─────────┘
                              (tool calls present)
    """
    # --- Instantiate components ---
    llm = build_llm(model_name)
    search_tool = build_search_tool(max_search_results)

    tools = [search_tool]

    # Bind tools to the LLM so it knows their schemas and can emit tool calls
    llm_with_tools = llm.bind_tools(tools)

    # Registry maps tool names (as the LLM knows them) to callable instances
    tool_registry: dict[str, TavilySearchResults] = {
        search_tool.name: search_tool,  # e.g. "tavily_search_results_json"
    }

    # Persistent, in-process memory so the graph can recall prior turns
    memory = MemorySaver()

    # --- Build node callables ---
    model_node = make_model_node(llm_with_tools)
    tool_node = make_tool_node(tool_registry)

    # --- Wire the graph ---
    builder = StateGraph(State)

    builder.add_node("model", model_node)
    builder.add_node("tool_node", tool_node)

    # Entry point: always start at the model
    builder.set_entry_point("model")

    # After the model runs, route based on whether tool calls were emitted
    builder.add_conditional_edges(
        "model",
        tools_router,
        {
            "tool_node": "tool_node",
            END: END,
        },
    )

    # After tools execute, always return to the model to process results
    builder.add_edge("tool_node", "model")

    logger.info("Compiling agent graph")
    return builder.compile(checkpointer=memory)


# ---------------------------------------------------------------------------
# Module-level graph instance (convenience)
# ---------------------------------------------------------------------------

graph = build_graph()
"""Pre-built, compiled agent graph.

Import this object directly for quick usage::

    from agent import graph

    config = {"configurable": {"thread_id": "my-session"}}
    result = await graph.ainvoke({"messages": [("user", "Hello!")]}, config)
"""

# ---------------------------------------------------------------------------
# CLI entry-point (optional)
# ---------------------------------------------------------------------------

app = FastAPI()

# Add CORS middleware with settings that match frontend requirements
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://devoted-mercy-production-366f.up.railway.app",],  
    allow_credentials=False,
    allow_methods=["*"],  
    allow_headers=["*"], 
    expose_headers=["Content-Type"], 
)





"""
streaming.py
------------
Server-Sent Events (SSE) generator for the LangGraph conversational agent.

Every yielded line follows the SSE spec:  ``data: <json>\\n\\n``
Clients read the ``type`` field to dispatch the event to the correct handler.

Event catalogue
---------------
+-------------------+----------------------------------------------------------+
| type              | Payload fields                                           |
+===================+==========================================================+
| session           | checkpoint_id                                            |
+-------------------+----------------------------------------------------------+
| content           | content (str), index (int)                               |
+-------------------+----------------------------------------------------------+
| search_start      | query (str), tool_call_id (str)                          |
+-------------------+----------------------------------------------------------+
| search_results    | urls ([str]), snippets ([str]),                          |
|                   | tool_call_id (str), result_count (int)                   |
+-------------------+----------------------------------------------------------+
| search_error      | error (str), tool_call_id (str)                          |
+-------------------+----------------------------------------------------------+
| tool_start        | tool_name (str), tool_call_id (str), args (dict)         |
+-------------------+----------------------------------------------------------+
| tool_end          | tool_name (str), tool_call_id (str)                      |
+-------------------+----------------------------------------------------------+
| thinking          | stage (str)                                              |
+-------------------+----------------------------------------------------------+
| error             | error (str), code (str)                                  |
+-------------------+----------------------------------------------------------+
| end               | (no extra fields)                                        |
+-------------------+----------------------------------------------------------+
"""





logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Name of the Tavily search tool as registered in the tool registry
_SEARCH_TOOL_NAME = "tavily_search_results_json"


def _sse(payload: dict) -> str:
    """Serialise *payload* to a valid SSE data line.

    Uses ``json.dumps`` for all serialisation so special characters
    (quotes, newlines, backslashes, unicode) are always escaped correctly —
    no manual ``.replace()`` chains required.

    Args:
        payload: Arbitrary JSON-serialisable dict.

    Returns:
        A string of the form ``"data: {...}\\n\\n"`` ready to be yielded to
        an SSE-capable HTTP response.
    """
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _serialise_chunk(chunk) -> str:
    """Extract the text content from an AI message chunk.

    Handles both plain ``str`` content and the structured list-of-blocks
    format that some models return.

    Args:
        chunk: A ``BaseMessageChunk`` (or compatible) object.

    Returns:
        The text portion of the chunk, or an empty string when no text is
        present (e.g. a pure tool-call chunk).
    """
    content = chunk.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Content blocks: [{"type": "text", "text": "..."}, ...]
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


def _build_config(thread_id: str) -> dict:
    """Build the LangGraph run config for a given thread.

    Args:
        thread_id: Persistent conversation identifier used by the checkpointer.

    Returns:
        A config dict accepted by ``graph.astream_events``.
    """
    return {"configurable": {"thread_id": thread_id}}


# ---------------------------------------------------------------------------
# Public generator
# ---------------------------------------------------------------------------


async def generate_chat_responses(
    message: str,
    checkpoint_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Stream agent responses as Server-Sent Events.

    Starts or continues a conversation with the LangGraph agent.  Each
    significant moment in the agent's reasoning — token emission, tool
    invocation, search results, errors — is surfaced as a typed SSE event so
    clients can render a rich, real-time UI.

    Args:
        message: The user's latest message text.
        checkpoint_id: Opaque conversation ID returned by a previous
            ``session`` event.  Pass ``None`` to start a new conversation;
            the generator will emit a ``session`` event with the new ID that
            the client must persist.

    Yields:
        SSE-formatted strings (``"data: {...}\\n\\n"``).  The final event is
        always ``{"type": "end"}`` unless an unrecoverable error occurs, in
        which case ``{"type": "error", ...}`` is emitted instead.

    Example SSE sequence for a search-augmented turn::

        data: {"type": "session",       "checkpoint_id": "abc-123"}
        data: {"type": "thinking",      "stage": "reasoning"}
        data: {"type": "search_start",  "query": "Python GIL", "tool_call_id": "…"}
        data: {"type": "tool_start",    "tool_name": "tavily…",  "tool_call_id": "…", "args": {…}}
        data: {"type": "tool_end",      "tool_name": "tavily…",  "tool_call_id": "…"}
        data: {"type": "search_results","urls": […], "snippets": […], …}
        data: {"type": "content",       "content": "The GIL is…", "index": 0}
        data: {"type": "content",       "content": " a mutex…",   "index": 1}
        data: {"type": "end"}
    """
    # ------------------------------------------------------------------
    # Resolve / create conversation thread
    # ------------------------------------------------------------------
    is_new_conversation = checkpoint_id is None
    thread_id = str(uuid4()) if is_new_conversation else checkpoint_id
    config = _build_config(thread_id)

    logger.info(
        "generate_chat_responses: thread_id=%s new=%s", thread_id, is_new_conversation
    )

    # Announce the session ID to the client so it can persist it
    if is_new_conversation:
        yield _sse({"type": "session", "checkpoint_id": thread_id})

    # ------------------------------------------------------------------
    # Stream events from the graph
    # ------------------------------------------------------------------
    try:
        events = graph.astream_events(
            {"messages": [HumanMessage(content=message)]},
            version="v2",
            config=config,
        )

        content_index = 0  # monotonically increasing token-chunk counter

        async for event in events:
            event_type: str = event["event"]
            event_name: str = event.get("name", "")
            data: dict = event.get("data", {})

            # --------------------------------------------------------------
            # 1. LLM starts generating (first sign-of-life after user sends)
            # --------------------------------------------------------------
            if event_type == "on_chat_model_start":
                yield _sse({"type": "thinking", "stage": "reasoning"})

            # --------------------------------------------------------------
            # 2. Streaming token chunks from the LLM
            # --------------------------------------------------------------
            elif event_type == "on_chat_model_stream":
                chunk = data.get("chunk")
                if chunk is None:
                    continue

                text = _serialise_chunk(chunk)
                if not text:
                    # Pure tool-call delta — nothing to show the user
                    continue

                yield _sse({"type": "content", "content": text, "index": content_index})
                content_index += 1

            # --------------------------------------------------------------
            # 3. LLM finished one generation step — inspect for tool calls
            # --------------------------------------------------------------
            elif event_type == "on_chat_model_end":
                output = data.get("output")
                if output is None:
                    continue

                tool_calls = getattr(output, "tool_calls", []) or []

                for call in tool_calls:
                    tool_name = call.get("name", "")
                    tool_call_id = call.get("id", "")
                    args = call.get("args", {})

                    # Emit a generic tool-start for every tool call …
                    yield _sse(
                        {
                            "type": "tool_start",
                            "tool_name": tool_name,
                            "tool_call_id": tool_call_id,
                            "args": args,
                        }
                    )

                    # … and a richer search-specific event for Tavily
                    if tool_name == _SEARCH_TOOL_NAME:
                        query = args.get("query", "")
                        yield _sse(
                            {
                                "type": "search_start",
                                "query": query,
                                "tool_call_id": tool_call_id,
                            }
                        )

            # --------------------------------------------------------------
            # 4. Any tool finished executing
            # --------------------------------------------------------------
            elif event_type == "on_tool_end":
                tool_call_id = event.get("run_id", "")  # best proxy available

                # Generic tool-end acknowledgement
                yield _sse(
                    {
                        "type": "tool_end",
                        "tool_name": event_name,
                        "tool_call_id": tool_call_id,
                    }
                )

                # Richer payload for search results
                if event_name == _SEARCH_TOOL_NAME:
                    output = data.get("output")
                    yield _from_search_output(output, tool_call_id)

            # --------------------------------------------------------------
            # 5. Tool raised an exception
            # --------------------------------------------------------------
            elif event_type == "on_tool_error":
                error_msg = str(data.get("error", "Unknown tool error"))
                tool_call_id = event.get("run_id", "")
                logger.warning("Tool error [%s]: %s", event_name, error_msg)

                if event_name == _SEARCH_TOOL_NAME:
                    yield _sse(
                        {
                            "type": "search_error",
                            "error": error_msg,
                            "tool_call_id": tool_call_id,
                        }
                    )
                else:
                    yield _sse(
                        {
                            "type": "error",
                            "error": error_msg,
                            "code": "tool_error",
                        }
                    )

    except Exception as exc:  # noqa: BLE001
        logger.exception("Unhandled error in generate_chat_responses: %s", exc)
        yield _sse({"type": "error", "error": str(exc), "code": "internal_error"})

    finally:
        # Always close the stream so clients know the turn is complete
        yield _sse({"type": "end"})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _from_search_output(output, tool_call_id: str) -> str:
    """Build a ``search_results`` SSE event from raw Tavily output.

    Tavily returns a list of result dicts, each potentially containing
    ``url``, ``content``, and ``title`` fields.  This helper extracts the
    most useful subset for the client.

    Args:
        output: Raw return value from ``TavilySearchResults.ainvoke``.
        tool_call_id: Identifier linking this result to the originating call.

    Returns:
        An SSE-formatted string for a ``search_results`` or ``search_error``
        event.
    """
    if not isinstance(output, list):
        return _sse(
            {
                "type": "search_error",
                "error": f"Unexpected search output type: {type(output).__name__}",
                "tool_call_id": tool_call_id,
            }
        )

    urls: list[str] = []
    snippets: list[str] = []
    titles: list[str] = []

    for item in output:
        if not isinstance(item, dict):
            continue
        if url := item.get("url"):
            urls.append(url)
        if snippet := item.get("content"):
            snippets.append(snippet)
        if title := item.get("title"):
            titles.append(title)

    return _sse(
        {
            "type": "search_results",
            "urls": urls,
            "snippets": snippets,
            "titles": titles,
            "result_count": len(urls),
            "tool_call_id": tool_call_id,
        }
    )





def serialise_ai_message_chunk(chunk): 
    if(isinstance(chunk, AIMessageChunk)):
        return chunk.content
    else:
        raise TypeError(
            f"Object of type {type(chunk).__name__} is not correctly formatted for serialisation"
        )


""" async def generate_chat_responses(message: str, checkpoint_id: Optional[str] = None):
    is_new_conversation = checkpoint_id is None
    
    if is_new_conversation:
        # Generate new checkpoint ID for first message in conversation
        new_checkpoint_id = str(uuid4())

        config = {
            "configurable": {
                "thread_id": new_checkpoint_id
            }
        }
        
        # Initialize with first message
        events = graph.astream_events(
            {"messages": [HumanMessage(content=message)]},
            version="v2",
            config=config
        )
        
        # First send the checkpoint ID
        yield f"data: {{\"type\": \"checkpoint\", \"checkpoint_id\": \"{new_checkpoint_id}\"}}\n\n"
    else:
        config = {
            "configurable": {
                "thread_id": checkpoint_id
            }
        }
        # Continue existing conversation
        events = graph.astream_events(
            {"messages": [HumanMessage(content=message)]},
            version="v2",
            config=config
        )

    async for event in events:
        event_type = event["event"]
        
        if event_type == "on_chat_model_stream":
            chunk_content = serialise_ai_message_chunk(event["data"]["chunk"])
            # Escape single quotes and newlines for safe JSON parsing
            safe_content = chunk_content.replace("'", "\\'").replace("\n", "\\n")
            
            yield f"data: {{\"type\": \"content\", \"content\": \"{safe_content}\"}}\n\n"
            
        elif event_type == "on_chat_model_end":
            # Check if there are tool calls for search
            tool_calls = event["data"]["output"].tool_calls if hasattr(event["data"]["output"], "tool_calls") else []
            search_calls = [call for call in tool_calls if call["name"] == "tavily_search_results_json"]
            
            if search_calls:
                # Signal that a search is starting
                search_query = search_calls[0]["args"].get("query", "")
                # Escape quotes and special characters
                safe_query = search_query.replace('"', '\\"').replace("'", "\\'").replace("\n", "\\n")
                yield f"data: {{\"type\": \"search_start\", \"query\": \"{safe_query}\"}}\n\n"
                
        elif event_type == "on_tool_end" and event["name"] == "tavily_search_results_json":
            # Search completed - send results or error
            output = event["data"]["output"]
            
            # Check if output is a list 
            if isinstance(output, list):
                # Extract URLs from list of search results
                urls = []
                for item in output:
                    if isinstance(item, dict) and "url" in item:
                        urls.append(item["url"])
                
                # Convert URLs to JSON and yield them
                urls_json = json.dumps(urls)
                yield f"data: {{\"type\": \"search_results\", \"urls\": {urls_json}}}\n\n"
    
    # Send an end event
    yield f"data: {{\"type\": \"end\"}}\n\n"
 """
@app.get("/chat_stream/{message}")
async def chat_stream(message: str, checkpoint_id: Optional[str] = Query(None)):
    """Stream agent responses as Server-Sent Events.

    Args:
        message: The user's message, provided as a URL path segment.
        checkpoint_id: Optional query parameter.  Omit on the first turn;
            pass the value received in the ``session`` event on all subsequent
            turns to continue the same conversation thread.

    Returns:
        A ``StreamingResponse`` with ``Content-Type: text/event-stream``.
        Each chunk is a JSON-encoded SSE event.  See ``generate_chat_responses``
        for the full event catalogue.

    Example:
        First turn (new conversation)::

            GET /chat_stream/Hello

            data: {"type": "session", "checkpoint_id": "abc-123"}
            data: {"type": "thinking", "stage": "reasoning"}
            data: {"type": "content", "content": "Hi!", "index": 0}
            data: {"type": "end"}

        Follow-up turn (existing conversation)::

            GET /chat_stream/How%20are%20you?checkpoint_id=abc-123

            data: {"type": "thinking", "stage": "reasoning"}
            data: {"type": "content", "content": "I'm doing well.", "index": 0}
            data: {"type": "end"}
    """
    return StreamingResponse(
        generate_chat_responses(message, checkpoint_id),
        media_type="text/event-stream",
        headers={
            # Prevent proxies / nginx from buffering the stream
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            # Allow the client to read the checkpoint_id header directly
            # (useful if you later choose to surface it as a response header)
            "Access-Control-Expose-Headers": "Content-Type",
        },
    )



if __name__ == "__main__":
    import asyncio

    async def _chat_loop() -> None:
        """Simple interactive REPL that drives the agent from the command line."""
        thread_id = str(uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        print(f"Agent started  (thread_id={thread_id})  — type 'quit' to exit.\n")

        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in {"quit", "exit", "q"}:
                print("Goodbye!")
                break
            if not user_input:
                continue

            state = {"messages": [HumanMessage(content=user_input)]}
            result = await graph.ainvoke(state, config=config)

            # The last message is always the final AI response
            final_message = result["messages"][-1]
            print(f"Agent: {final_message.content}\n")

    asyncio.run(_chat_loop())