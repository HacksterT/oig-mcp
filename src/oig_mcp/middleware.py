"""Per-client request limits, a usage log, and tool-call traces for the MCP endpoint.

Each client has its own limit, so one runaway agent can't use up the shared Mac.
The usage log records who called which tool and how it ended, never the arguments.
Traces (tracing.py) record everything, including arguments and results, and are
written only while MCP_TRACE_DIR is set, for closed testing.
"""

from __future__ import annotations

import logging
import re
import sys
import time
from typing import Any

import anyio
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.middleware.middleware import CallNext
from fastmcp.server.middleware.rate_limiting import (
    RateLimitError,
    RateLimitingMiddleware,
)
from fastmcp.tools import ToolResult

from oig_mcp import tracing
from oig_mcp.utils import ToolFailure

# An agent can fan out several searches at once, so allow a burst. A steady two
# requests a second is still far beyond a person working with an agent.
REQUESTS_PER_SECOND = 2.0
BURST = 30

_TOOL_NAME = re.compile(r"[A-Za-z0-9_.-]{1,100}")

usage_log = logging.getLogger("oig_mcp.usage")


def _client_name(_context: MiddlewareContext | None = None) -> str:
    token = get_access_token()
    return token.client_id if token else "local"


class UsageLogMiddleware(Middleware):
    """Log one line per tool call: client, tool, outcome, and duration."""

    async def on_call_tool(
        self, context: MiddlewareContext, call_next: CallNext
    ) -> Any:
        started = time.monotonic()
        outcome = "error"
        try:
            result = await call_next(context)
            outcome = "error" if getattr(result, "is_error", False) else "ok"
            return result
        except RateLimitError:
            outcome = "rate_limited"
            raise
        finally:
            # The caller chooses this name, so don't let it write into the log.
            name = str(context.message.name)
            tool = name if _TOOL_NAME.fullmatch(name) else "invalid"
            milliseconds = round((time.monotonic() - started) * 1000)
            usage_log.info(
                "client=%s tool=%s outcome=%s ms=%d",
                _client_name(),
                tool,
                outcome,
                milliseconds,
            )


def _result_data(result: Any) -> Any:
    """The structured result if there is one, otherwise the content blocks."""
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return structured
    return [
        block.model_dump(mode="json") if hasattr(block, "model_dump") else str(block)
        for block in getattr(result, "content", None) or []
    ]


class ToolTraceMiddleware(Middleware):
    """Trace each tool call, and write the trace when a store is given."""

    def __init__(self, store: tracing.TraceStore | None) -> None:
        self.store = store

    async def on_call_tool(
        self, context: MiddlewareContext, call_next: CallNext
    ) -> Any:
        name = str(context.message.name)
        record, token = tracing.start(
            _client_name(),
            name if _TOOL_NAME.fullmatch(name) else "invalid",
            context.message.arguments,
        )
        started = time.monotonic()
        try:
            result = await call_next(context)
            record["outcome"] = "error" if getattr(result, "is_error", False) else "ok"
            record["result"] = _result_data(result)
            return result
        except Exception as exc:
            limited = isinstance(exc, RateLimitError)
            record["outcome"] = "rate_limited" if limited else "error"
            record["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            tracing.finish(token)
            record["ms"] = round((time.monotonic() - started) * 1000)
            if self.store is not None:
                try:
                    await anyio.to_thread.run_sync(self.store.write, record)
                except Exception:  # a trace is never worth a failed call
                    usage_log.warning("could not write trace")


class ToolFailureMiddleware(Middleware):
    """Return a ToolFailure as an isError result that keeps its error and hint.

    A plain ToolError reaches the client as text only. This keeps the structured
    body, so the assistant still gets a separate hint field. It runs innermost, so
    the usage log and traces see the isError result.
    """

    async def on_call_tool(
        self, context: MiddlewareContext, call_next: CallNext
    ) -> Any:
        try:
            return await call_next(context)
        except ToolFailure as failure:
            return ToolResult(structured_content=failure.body, is_error=True)


class ClientRateLimitMiddleware(RateLimitingMiddleware):
    """Limit callers with a token. Stdio has no token and only one local user."""

    async def on_request(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        if get_access_token() is None:
            return await call_next(context)
        return await super().on_request(context, call_next)


def configure_usage_log(path: str = "") -> None:
    """Log to stderr, and to a file if set. A bad path must not stop the server."""
    formatter = logging.Formatter(
        "%(asctime)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%SZ"
    )
    formatter.converter = time.gmtime
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    failed = False
    if path:
        try:
            handlers.append(logging.FileHandler(path))
        except OSError:
            failed = True
    usage_log.handlers.clear()
    for handler in handlers:
        handler.setFormatter(formatter)
        usage_log.addHandler(handler)
    usage_log.setLevel(logging.INFO)
    usage_log.propagate = False
    if failed:
        usage_log.warning("usage log file could not be opened; using stderr only")


def add_usage_controls(
    server: FastMCP,
    requests_per_second: float = REQUESTS_PER_SECOND,
    burst: int = BURST,
    trace_store: tracing.TraceStore | None = None,
) -> None:
    """Attach logging and tracing outside the limit, so refused calls appear too.

    The first middleware added is the outermost. ToolFailureMiddleware goes last,
    nearest the tool, so every layer above it sees a failed call as isError.
    """
    server.add_middleware(UsageLogMiddleware())
    server.add_middleware(ToolTraceMiddleware(trace_store))
    server.add_middleware(
        ClientRateLimitMiddleware(
            max_requests_per_second=requests_per_second,
            burst_capacity=burst,
            get_client_id=_client_name,
        )
    )
    server.add_middleware(ToolFailureMiddleware())
