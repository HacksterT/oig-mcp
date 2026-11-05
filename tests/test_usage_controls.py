"""The usage log names the client and never the arguments; limits are per client."""

from __future__ import annotations

import logging
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest
from fastmcp import FastMCP

from oig_mcp.auth import BearerTokenVerifier
from oig_mcp.middleware import add_usage_controls, configure_usage_log, usage_log

ALICE = "a" * 64
BOB = "b" * 64
PRIVATE_QUERY = "private-search-words"
SCRIPT = Path(__file__).parent.parent / "deploy" / "mcp_clients.py"


@asynccontextmanager
async def mcp_client(burst: int = 100):
    server = FastMCP(
        "usage-test", auth=BearerTokenVerifier({"alice": ALICE, "bob": BOB})
    )

    @server.tool
    def echo(query: str) -> str:
        return query

    @server.tool
    def fail(query: str) -> str:
        raise ValueError(query)

    add_usage_controls(server, requests_per_second=0.001, burst=burst)
    http_app = server.http_app(stateless_http=True, json_response=True)
    async with http_app.router.lifespan_context(http_app):
        transport = httpx.ASGITransport(app=http_app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            yield client


async def call(client: httpx.AsyncClient, token: str, tool: str = "echo") -> dict:
    response = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool, "arguments": {"query": PRIVATE_QUERY}},
        },
        headers={
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {token}",
        },
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def usage_lines():
    """Collect formatted usage lines, whatever handlers are configured."""
    lines: list[str] = []

    class Collect(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            lines.append(record.getMessage())

    handler = Collect()
    configure_usage_log()
    usage_log.addHandler(handler)
    yield lines
    usage_log.removeHandler(handler)


async def test_log_names_client_and_tool_but_not_arguments(usage_lines) -> None:
    async with mcp_client() as client:
        await call(client, ALICE)
        await call(client, BOB)
    assert len(usage_lines) == 2
    assert "client=alice tool=echo outcome=ok" in usage_lines[0]
    assert "client=bob tool=echo outcome=ok" in usage_lines[1]
    assert not any(PRIVATE_QUERY in line or ALICE in line for line in usage_lines)


async def test_failed_tool_is_logged_as_an_error(usage_lines) -> None:
    async with mcp_client() as client:
        await call(client, ALICE, tool="fail")
    assert "tool=fail outcome=error" in usage_lines[0]
    assert PRIVATE_QUERY not in usage_lines[0]


async def test_unsafe_tool_name_does_not_reach_the_log(usage_lines) -> None:
    async with mcp_client() as client:
        await call(client, ALICE, tool="bad\nclient=forged")
    assert "tool=invalid" in usage_lines[0]
    assert "forged" not in usage_lines[0]


async def test_limit_applies_to_each_client_alone(usage_lines) -> None:
    async with mcp_client(burst=2) as client:
        assert "result" in await call(client, ALICE)
        assert "result" in await call(client, ALICE)
        refused = await call(client, ALICE)
        assert "error" in refused
        assert PRIVATE_QUERY not in str(refused)
        assert "result" in await call(client, BOB)
    assert "client=alice tool=echo outcome=rate_limited" in usage_lines[2]
    assert "client=bob tool=echo outcome=ok" in usage_lines[3]


def test_unwritable_log_file_does_not_stop_the_server(tmp_path: Path) -> None:
    configure_usage_log(str(tmp_path / "missing" / "usage.log"))
    assert len(usage_log.handlers) == 1
    configure_usage_log()


def test_log_file_receives_lines(tmp_path: Path) -> None:
    path = tmp_path / "usage.log"
    configure_usage_log(str(path))
    usage_log.info("client=alice tool=echo outcome=ok ms=1")
    for handler in usage_log.handlers:
        handler.flush()
    configure_usage_log()
    assert "client=alice tool=echo outcome=ok ms=1" in path.read_text()


def test_usage_summary_counts_each_client(tmp_path: Path) -> None:
    log_file = tmp_path / "usage.log"
    log_file.write_text(
        "2026-11-05T10:00:00Z client=alice tool=echo outcome=ok ms=5\n"
        "2026-11-05T10:01:00Z client=alice tool=echo outcome=error ms=5\n"
        "2026-11-05T10:02:00Z client=bob tool=echo outcome=ok ms=5\n"
        "not a usage line\n"
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "usage", "--log-file", str(log_file)],
        capture_output=True,
        text=True,
        check=True,
    )
    lines = result.stdout.splitlines()
    assert lines[1].split() == ["alice", "2", "1", "2026-11-05T10:01:00Z"]
    assert lines[2].split() == ["bob", "1", "0", "2026-11-05T10:02:00Z"]
