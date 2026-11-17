"""Per-client request limits, a usage log, and traces for the MCP endpoint.

Each client has its own limit, so one runaway agent can't use up the shared Mac.
The usage log records who called which tool or read which resource, how it ended,
and the trace ID, never the arguments. Traces (tracing.py) record everything,
including arguments and results, and are
written only while MCP_TRACE_DIR is set. They stay on through the hackathon,
including judging, to see what people ask; users are told in vaoig://about.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from collections.abc import Callable
from logging.handlers import RotatingFileHandler
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
_RESOURCE_URI = re.compile(r"vaoig://[A-Za-z0-9_./%-]{1,100}")

usage_log = logging.getLogger("oig_mcp.usage")


def _client_name(_context: MiddlewareContext | None = None) -> str:
    token = get_access_token()
    return token.client_id if token else "local"


def _safe(name: str, pattern: re.Pattern[str]) -> str:
    """The caller chooses this name, so don't let it write into the log."""
    return name if pattern.fullmatch(name) else "invalid"


class UsageLogMiddleware(Middleware):
    """Log one line per tool call or resource read: client, name, outcome, time."""

    async def on_read_resource(
        self, context: MiddlewareContext, call_next: CallNext
    ) -> Any:
        uri = _safe(str(context.message.uri), _RESOURCE_URI)
        return await self._logged("resource", uri, context, call_next)

    async def on_call_tool(
        self, context: MiddlewareContext, call_next: CallNext
    ) -> Any:
        tool = _safe(str(context.message.name), _TOOL_NAME)
        return await self._logged("tool", tool, context, call_next)

    @staticmethod
    async def _logged(
        kind: str, name: str, context: MiddlewareContext, call_next: CallNext
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
            usage_log.info(
                "client=%s %s=%s outcome=%s ms=%d trace=%s",
                _client_name(),
                kind,
                name,
                outcome,
                round((time.monotonic() - started) * 1000),
                tracing.current_id() or "-",
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


def _resource_data(result: Any) -> Any:
    """What a resource read returned: parsed JSON where it is JSON."""
    data = []
    for item in getattr(result, "contents", None) or []:
        content = item.content
        if isinstance(content, bytes):
            data.append(f"[{len(content)} bytes]")
            continue
        try:
            data.append(json.loads(content))
        except (TypeError, ValueError):
            data.append(content)
    return data


class TraceMiddleware(Middleware):
    """Trace each tool call and resource read; write it when a store is given.

    It runs outermost, so the usage log can stamp each line with the trace ID, and
    a resource read's data API requests carry trace headers like a tool call's.
    """

    def __init__(self, store: tracing.TraceStore | None) -> None:
        self.store = store

    async def on_call_tool(
        self, context: MiddlewareContext, call_next: CallNext
    ) -> Any:
        name = _safe(str(context.message.name), _TOOL_NAME)
        return await self._traced(
            name, context.message.arguments, _result_data, context, call_next
        )

    async def on_read_resource(
        self, context: MiddlewareContext, call_next: CallNext
    ) -> Any:
        arguments = {"uri": str(context.message.uri)}
        return await self._traced(
            "read_resource", arguments, _resource_data, context, call_next
        )

    async def _traced(
        self,
        name: str,
        arguments: Any,
        result_data: Callable[[Any], Any],
        context: MiddlewareContext,
        call_next: CallNext,
    ) -> Any:
        record, token = tracing.start(_client_name(), name, arguments)
        started = time.monotonic()
        try:
            result = await call_next(context)
            record["outcome"] = "error" if getattr(result, "is_error", False) else "ok"
            record["result"] = result_data(result)
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
    """Limit callers with a token. Stdio has no token and only one local user.

    It counts every MCP request a token makes, including tool listing, not only
    tool calls. Buckets live in this process's memory, so they reset on restart
    and each instance keeps its own: with N instances a client can reach N times
    the limit. Everything else here is stateless; a shared store would fix this
    and is not justified for a few trusted testers.
    """

    async def on_request(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        if get_access_token() is None:
            return await call_next(context)
        return await super().on_request(context, call_next)


class _PrivateRotatingFileHandler(RotatingFileHandler):
    """Rotated so it cannot fill the disk; every file it opens is private, like
    the traces, including the fresh one after each rollover."""

    def _open(self) -> Any:
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        descriptor = os.open(self.baseFilename, flags, 0o600)
        os.fchmod(descriptor, 0o600)  # a file that already existed, too
        return os.fdopen(descriptor, "a", encoding=self.encoding, errors=self.errors)


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
            handlers.append(
                _PrivateRotatingFileHandler(path, maxBytes=10_000_000, backupCount=3)
            )
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
    """Attach tracing and logging outside the limit, so refused calls appear too.

    The first middleware added is the outermost. Tracing comes first so each usage
    line carries the trace ID. ToolFailureMiddleware goes last, nearest the tool,
    so every layer above it sees a failed call as isError.
    """
    server.add_middleware(TraceMiddleware(trace_store))
    server.add_middleware(UsageLogMiddleware())
    server.add_middleware(
        ClientRateLimitMiddleware(
            max_requests_per_second=requests_per_second,
            burst_capacity=burst,
            get_client_id=_client_name,
        )
    )
    server.add_middleware(ToolFailureMiddleware())
