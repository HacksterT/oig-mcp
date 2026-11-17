"""HTTP sessions that are optional: a request without one is still answered.

The hosted endpoint keeps a session per client, so it can ask the user a question
mid-call on every protocol version. Some bridges never hold a session ID: one
connected while the endpoint was stateless and then sent every call without
one, and the MCP library refused each with "400 Missing session ID". So a POST
with no session ID that is not the opening `initialize` is served the stateless
way, as one self-contained request, instead of refused. Such a client cannot be
asked mid-call on 2025-11-25 and earlier, and gets the matches with a next step
instead, as before sessions. A request naming an expired session still gets 404,
which tells a client that follows the spec to start a new one.
"""

from __future__ import annotations

import json
from typing import Any

from fastmcp.server import http as fastmcp_http
from mcp.server.streamable_http import MCP_SESSION_ID_HEADER
from mcp.server.transport_security import DEFAULT_MAX_REQUEST_BODY_SIZE
from mcp.shared.inbound import MCP_PROTOCOL_VERSION_HEADER
from starlette.types import Message, Receive, Scope, Send

_SESSION = MCP_SESSION_ID_HEADER.lower().encode("ascii")
_VERSION = MCP_PROTOCOL_VERSION_HEADER.lower().encode("ascii")


def _opens_session(body: bytes) -> bool:
    """True if the body is, or a batch contains, an initialize request. A body that
    does not parse is left to the library, which answers it as it always has."""
    try:
        message = json.loads(body)
    except ValueError:
        return True
    messages = message if isinstance(message, list) else [message]
    return any(
        isinstance(m, dict) and m.get("method") == "initialize" for m in messages
    )


async def _read_body(receive: Receive) -> bytes:
    """The request body, up to the library's size limit; past it, the library's
    own handling refuses the request as it would have."""
    chunks, size = [], 0
    while size <= DEFAULT_MAX_REQUEST_BODY_SIZE:
        message = await receive()
        if message["type"] != "http.request":
            break
        chunks.append(message.get("body", b""))
        size += len(chunks[-1])
        if not message.get("more_body", False):
            break
    return b"".join(chunks)


def _replay(body: bytes, receive: Receive) -> Receive:
    """A receive that gives the body already read, then defers to the original."""
    sent = False

    async def replayed() -> Message:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return await receive()

    return replayed


class SessionOptionalManager(fastmcp_http.FastMCPStreamableHTTPSessionManager):
    """FastMCP's session manager, serving sessionless calls instead of refusing them."""

    async def _handle_stateful_request(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        headers = dict(scope.get("headers", []))
        if scope.get("method") == "POST" and _SESSION not in headers:
            body = await _read_body(receive)
            receive = _replay(body, receive)
            if len(body) <= DEFAULT_MAX_REQUEST_BODY_SIZE and not _opens_session(body):
                version = headers.get(_VERSION)
                await self._handle_stateless_request(
                    version.decode("latin-1") if version else None, scope, receive, send
                )
                return
        await super()._handle_stateful_request(scope, receive, send)


def install() -> Any:
    """Make FastMCP build its HTTP apps with the session-optional manager."""
    fastmcp_http.FastMCPStreamableHTTPSessionManager = SessionOptionalManager
    return SessionOptionalManager
