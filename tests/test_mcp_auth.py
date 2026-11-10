"""Inbound auth: /mcp requires the bearer token and HTTP refuses to start open."""

from __future__ import annotations

import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import fastmcp
import httpx
import pytest
from fastmcp import FastMCP
from pydantic import ValidationError

from oig_mcp import app as app_module
from oig_mcp.auth import BearerTokenVerifier
from oig_mcp.config import Settings
from oig_mcp.routes import register_routes

TOKEN = "t" * 64
OTHER_TOKEN = "o" * 64
MCP_CLIENTS_SCRIPT = Path(__file__).parent.parent / "deploy" / "mcp_clients.py"
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
    server = FastMCP("auth-test", auth=BearerTokenVerifier({"mcp-client": TOKEN}))
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
    verifier = BearerTokenVerifier({"mcp-client": TOKEN})
    assert await verifier.verify_token("tökén") is None


async def test_verifier_names_the_client_for_each_token() -> None:
    verifier = BearerTokenVerifier({"mcp-client": TOKEN, "alice": OTHER_TOKEN})
    assert (await verifier.verify_token(TOKEN)).client_id == "mcp-client"
    assert (await verifier.verify_token(OTHER_TOKEN)).client_id == "alice"
    assert await verifier.verify_token("x" * 64) is None


def test_short_token_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least 32"):
        Settings(_env_file=None, mcp_auth_token="short")


def test_client_tokens_are_added_to_the_primary_token() -> None:
    settings = Settings(
        _env_file=None,
        mcp_auth_token=TOKEN,
        mcp_client_tokens=f"alice:{OTHER_TOKEN},",
    )
    assert settings.inbound_tokens() == {"mcp-client": TOKEN, "alice": OTHER_TOKEN}


def test_no_client_tokens_leaves_only_the_primary_token() -> None:
    settings = Settings(_env_file=None, mcp_auth_token=TOKEN)
    assert settings.inbound_tokens() == {"mcp-client": TOKEN}


@pytest.mark.parametrize(
    "value",
    [
        "alice:short",
        f"Alice:{OTHER_TOKEN}",
        OTHER_TOKEN,
        f"mcp-client:{OTHER_TOKEN}",
        f"alice:{OTHER_TOKEN},alice:{'p' * 64}",
        f"alice:{OTHER_TOKEN},bob:{OTHER_TOKEN}",
        f"alice:{TOKEN}",
    ],
)
def test_bad_client_tokens_are_rejected_without_showing_them(value: str) -> None:
    with pytest.raises(ValidationError) as caught:
        Settings(_env_file=None, mcp_auth_token=TOKEN, mcp_client_tokens=value)
    assert OTHER_TOKEN not in str(caught.value)
    assert TOKEN not in str(caught.value)


def _run_clients_script(env_file: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(MCP_CLIENTS_SCRIPT),
            *args,
            "--env-file",
            str(env_file),
            "--no-restart",
        ],
        capture_output=True,
        text=True,
    )


def test_clients_script_adds_lists_and_removes(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    # No final newline, as a hand-edited file may have.
    env_file.write_text(f"MCP_AUTH_TOKEN={TOKEN}\nOTHER=value")

    added = _run_clients_script(env_file, "add", "alice")
    assert added.returncode == 0
    alice_token = added.stdout.strip()
    settings = Settings(_env_file=env_file)
    assert settings.inbound_tokens() == {"mcp-client": TOKEN, "alice": alice_token}
    assert env_file.stat().st_mode & 0o777 == 0o600

    bob_token = _run_clients_script(env_file, "add", "bob").stdout.strip()
    assert bob_token != alice_token

    listed = _run_clients_script(env_file, "list")
    assert listed.stdout.split() == ["alice", "bob"]

    assert _run_clients_script(env_file, "remove", "alice").returncode == 0
    settings = Settings(_env_file=env_file)
    assert settings.inbound_tokens() == {"mcp-client": TOKEN, "bob": bob_token}

    assert _run_clients_script(env_file, "remove", "bob").returncode == 0
    assert env_file.read_text() == f"MCP_AUTH_TOKEN={TOKEN}\nOTHER=value\n"


@pytest.mark.parametrize(
    "args",
    [
        ("add", "mcp-client"),
        ("add", "Not A Name"),
        ("add",),
        ("remove", "nobody"),
    ],
)
def test_clients_script_refuses_bad_requests(tmp_path: Path, args: tuple) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(f"MCP_AUTH_TOKEN={TOKEN}\n")
    assert _run_clients_script(env_file, *args).returncode != 0
    assert env_file.read_text() == f"MCP_AUTH_TOKEN={TOKEN}\n"


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
            "transport": "streamable-http",
            "host": "0.0.0.0",
            "port": 8080,
            "stateless_http": True,
            "json_response": True,
            "host_origin_protection": False,
        }
    ]


def test_platform_port_wins_over_mcp_transport(monkeypatch) -> None:
    calls = _capture_run(monkeypatch)
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setattr(app_module.settings, "mcp_transport", "stdio")
    monkeypatch.setattr(app_module.settings, "mcp_auth_token", TOKEN)
    app_module.main()
    assert calls[0]["transport"] == "streamable-http"


def test_local_http_binds_loopback_and_checks_host(monkeypatch) -> None:
    calls = _capture_run(monkeypatch)
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("MCP_HOST", raising=False)
    monkeypatch.setattr(app_module.settings, "mcp_transport", "streamable-http")
    monkeypatch.setattr(app_module.settings, "mcp_auth_token", TOKEN)
    monkeypatch.setattr(
        app_module.settings, "mcp_host", Settings.model_fields["mcp_host"].default
    )
    app_module.main()
    assert calls == [
        {
            "transport": "streamable-http",
            "host": "127.0.0.1",
            "port": app_module.settings.mcp_port,
            "stateless_http": True,
            "json_response": True,
            "host_origin_protection": "auto",
        }
    ]


@pytest.mark.parametrize("value", ["streamable_http", "http", "sse", ""])
def test_unknown_transport_stops_at_startup(value: str) -> None:
    with pytest.raises(ValidationError, match="mcp_transport"):
        Settings(_env_file=None, mcp_transport=value)


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
