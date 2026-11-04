"""Inbound auth: /mcp requires the bearer token and HTTP refuses to start open."""

from __future__ import annotations

from contextlib import asynccontextmanager

import fastmcp
import httpx
import pytest
from fastmcp import FastMCP
from pydantic import ValidationError

from oig_mcp import app as app_module
from oig_mcp.auth import SharedTokenVerifier
from oig_mcp.config import Settings
from oig_mcp.routes import register_routes

TOKEN = "t" * 64
INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0"},
    },
}
MCP_HEADERS = {"Accept": "application/json, text/event-stream"}


@asynccontextmanager
async def mcp_client():
    """Open the app inside the test's own task, as anyio cancel scopes require."""
    server = FastMCP("auth-test", auth=SharedTokenVerifier(TOKEN))
    register_routes(server)
    http_app = server.http_app()
    async with http_app.router.lifespan_context(http_app):
        transport = httpx.ASGITransport(app=http_app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as async_client:
            yield async_client


async def test_mcp_rejects_missing_token() -> None:
    async with mcp_client() as client:
        response = await client.post("/mcp", json=INITIALIZE, headers=MCP_HEADERS)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "authorization",
    ["Bearer wrong", f"Bearer {TOKEN}x", f"Bearer {TOKEN[:-1]}", f"Basic {TOKEN}"],
)
async def test_mcp_rejects_wrong_token(authorization: str) -> None:
    headers = {**MCP_HEADERS, "Authorization": authorization}
    async with mcp_client() as client:
        response = await client.post("/mcp", json=INITIALIZE, headers=headers)
    assert response.status_code == 401


async def test_mcp_accepts_correct_token() -> None:
    headers = {**MCP_HEADERS, "Authorization": f"Bearer {TOKEN}"}
    async with mcp_client() as client:
        response = await client.post("/mcp", json=INITIALIZE, headers=headers)
    assert response.status_code == 200
    assert "auth-test" in response.text


async def test_mcp_rejects_token_in_query_string() -> None:
    async with mcp_client() as client:
        response = await client.post(
            f"/mcp?token={TOKEN}&access_token={TOKEN}",
            json=INITIALIZE,
            headers=MCP_HEADERS,
        )
    assert response.status_code == 401


@pytest.mark.parametrize("path", ["/health", "/version"])
async def test_operational_routes_stay_open(path: str) -> None:
    async with mcp_client() as client:
        response = await client.get(path)
    assert response.status_code == 200


async def test_verifier_rejects_non_ascii_token_without_raising() -> None:
    assert await SharedTokenVerifier(TOKEN).verify_token("tökén") is None


def test_short_token_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least 32"):
        Settings(_env_file=None, mcp_auth_token="short")


def _capture_run(monkeypatch) -> list[dict]:
    calls: list[dict] = []
    monkeypatch.setattr(app_module.mcp, "run", lambda **kwargs: calls.append(kwargs))
    return calls


def test_platform_port_refuses_to_start_without_token(monkeypatch) -> None:
    calls = _capture_run(monkeypatch)
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setattr(app_module.settings, "mcp_auth_token", "")
    with pytest.raises(SystemExit, match="MCP_AUTH_TOKEN"):
        app_module.main()
    assert calls == []


def test_streamable_http_refuses_to_start_without_token(monkeypatch) -> None:
    calls = _capture_run(monkeypatch)
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setattr(app_module.settings, "mcp_transport", "streamable-http")
    monkeypatch.setattr(app_module.settings, "mcp_auth_token", "")
    with pytest.raises(SystemExit, match="MCP_AUTH_TOKEN"):
        app_module.main()
    assert calls == []


def test_platform_port_serves_stateless_http_with_token(monkeypatch) -> None:
    calls = _capture_run(monkeypatch)
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setattr(app_module.settings, "mcp_auth_token", TOKEN)
    app_module.main()
    assert calls == [
        {
            "transport": "http",
            "host": "0.0.0.0",
            "port": 8080,
            "stateless_http": True,
        }
    ]


def test_server_does_not_check_pypi_for_updates() -> None:
    assert fastmcp.settings.check_for_updates == "off"
    assert fastmcp.settings.show_server_banner is False


def test_stdio_starts_without_token(monkeypatch) -> None:
    calls = _capture_run(monkeypatch)
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setattr(app_module.settings, "mcp_transport", "stdio")
    monkeypatch.setattr(app_module.settings, "mcp_auth_token", "")
    app_module.main()
    assert calls == [{"transport": "stdio"}]
