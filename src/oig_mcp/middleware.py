"""Per-client request limits and a usage log for the MCP endpoint.

Each client has its own limit, so one runaway agent can't use up the shared Mac.
The usage log records who called which tool and how it ended. It never records
tool arguments, because those hold what people are searching for.
"""

from __future__ import annotations

import logging
import re
import sys
import time
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.middleware.middleware import CallNext
from fastmcp.server.middleware.rate_limiting import (
    RateLimitError,
    RateLimitingMiddleware,
)

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
) -> None:
    """Attach logging outside the limit, so refused calls are logged too."""
    server.add_middleware(UsageLogMiddleware())
    server.add_middleware(
        ClientRateLimitMiddleware(
            max_requests_per_second=requests_per_second,
            burst_capacity=burst,
            get_client_id=_client_name,
        )
    )
