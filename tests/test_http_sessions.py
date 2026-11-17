"""The hosted endpoint keeps sessions but still answers a call without one."""

from __future__ import annotations

import json

import pytest
from fastmcp import FastMCP
from starlette.testclient import TestClient

from oig_mcp import http_sessions
from oig_mcp.http_sessions import _opens_session

HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
    "MCP-Protocol-Version": "2025-11-25",
}
CALL = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {"name": "echo", "arguments": {"text": "hi"}},
}
INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0"},
    },
}


@pytest.fixture
def client(monkeypatch):
    from fastmcp.server import http as fastmcp_http

    monkeypatch.setattr(
        fastmcp_http,
        "FastMCPStreamableHTTPSessionManager",
        fastmcp_http.FastMCPStreamableHTTPSessionManager,
    )
    http_sessions.install()
    server = FastMCP("t")

    @server.tool
    def echo(text: str) -> str:
        return f"echo {text}"

    app = server.http_app(stateless_http=False, json_response=False)
    with TestClient(app) as test_client:
        yield test_client


def post(client: TestClient, body: dict, **headers: str):
    return client.post("/mcp", headers={**HEADERS, **headers}, content=json.dumps(body))


def test_a_call_without_a_session_is_answered(client: TestClient) -> None:
    # A bridge that never held a session ID was refused with "Missing session ID".
    response = post(client, CALL)
    assert response.status_code == 200
    assert "echo hi" in response.text
    assert "mcp-session-id" not in response.headers


def test_initialize_still_opens_a_session(client: TestClient) -> None:
    response = post(client, INITIALIZE)
    assert response.status_code == 200
    assert response.headers.get("mcp-session-id")


def test_an_expired_session_still_gets_404(client: TestClient) -> None:
    response = post(client, CALL, **{"Mcp-Session-Id": "expired"})
    assert response.status_code == 404


@pytest.mark.parametrize(
    ("body", "opens"),
    [
        (INITIALIZE, True),
        ([CALL, INITIALIZE], True),
        (CALL, False),
        ([CALL], False),
    ],
)
def test_only_initialize_opens_a_session(body, opens: bool) -> None:
    assert _opens_session(json.dumps(body).encode()) is opens


def test_an_unparsable_body_is_left_to_the_library() -> None:
    assert _opens_session(b"{not json") is True
