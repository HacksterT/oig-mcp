"""Tool-call traces: complete, linked to the API, never fatal, and capped."""

from __future__ import annotations

import json
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest
from fastmcp import FastMCP

from oig_mcp import tracing, utils
from oig_mcp.auth import BearerTokenVerifier
from oig_mcp.middleware import add_usage_controls
from oig_mcp.tracing import TraceStore

ALICE = "a" * 64
SCRIPT = Path(__file__).parent.parent / "deploy" / "traces.py"


def fake_api(
    monkeypatch, status: int = 200, body: object = None
) -> list[httpx.Request]:
    """Answer the data API's requests locally, and keep them for inspection."""
    seen: list[httpx.Request] = []
    real = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json=body if body is not None else {})

    def client(*args, **kwargs):
        if "transport" in kwargs:  # the test's own client to the MCP app
            return real(*args, **kwargs)
        return real(*args, transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(utils.httpx, "AsyncClient", client)
    return seen


@asynccontextmanager
async def mcp_client(store: TraceStore | None):
    server = FastMCP("trace-test", auth=BearerTokenVerifier({"alice": ALICE}))

    @server.tool
    async def lookup(question: str) -> dict:
        return {"answer": await utils.fetch_json("meta", params={"q": question})}

    add_usage_controls(server, trace_store=store)
    http_app = server.http_app(stateless_http=True, json_response=True)
    async with http_app.router.lifespan_context(http_app):
        transport = httpx.ASGITransport(app=http_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            yield c


async def call(client: httpx.AsyncClient) -> dict:
    response = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "lookup", "arguments": {"question": "carts"}},
        },
        headers={
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {ALICE}",
        },
    )
    return response.json()


def records(directory: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(directory.glob("*/*.json"))]


async def test_call_is_traced_and_linked_to_the_api(tmp_path, monkeypatch) -> None:
    seen = fake_api(monkeypatch, body={"n": 1})
    async with mcp_client(TraceStore(tmp_path, 10_000_000)) as client:
        await call(client)
    [record] = records(tmp_path)
    sent = seen[-1].headers
    assert sent["X-Trace-Id"] == record["trace_id"]
    assert sent["X-OIG-Client"] == "alice"
    assert sent["X-OIG-Tool"] == "lookup"
    assert record["arguments"] == {"question": "carts"}
    assert record["outcome"] == "ok"
    assert record["result"] == {"answer": {"n": 1}}
    [api_call] = record["api_calls"]
    assert api_call["path"] == "meta"
    assert api_call["status"] == 200
    assert ALICE not in json.dumps(record)


async def test_failed_api_call_is_recorded(tmp_path, monkeypatch) -> None:
    fake_api(monkeypatch, status=503)
    async with mcp_client(TraceStore(tmp_path, 10_000_000)) as client:
        await call(client)
    [record] = records(tmp_path)
    assert record["outcome"] == "error"
    assert record["api_calls"][0]["status"] == 503


async def test_headers_are_sent_even_when_traces_are_off(tmp_path, monkeypatch) -> None:
    seen = fake_api(monkeypatch)
    async with mcp_client(None) as client:
        await call(client)
    assert seen[-1].headers["X-OIG-Client"] == "alice"
    assert not any(tmp_path.iterdir())


async def test_write_failure_does_not_fail_the_call(tmp_path, monkeypatch) -> None:
    fake_api(monkeypatch, body={"n": 1})

    def broken(*_args):
        raise OSError("disk full")

    monkeypatch.setattr(TraceStore, "write", broken)
    async with mcp_client(TraceStore(tmp_path, 10_000_000)) as client:
        body = await call(client)
    assert body["result"]["structuredContent"] == {"answer": {"n": 1}}


def test_no_headers_outside_a_tool_call() -> None:
    assert tracing.headers() == {}


def test_store_removes_oldest_past_the_cap(tmp_path: Path) -> None:
    store = TraceStore(tmp_path, max_bytes=3_000)
    for n in range(10):
        store.write(
            {
                "time": f"2026-11-05T10:00:{n:02d}.000+00:00",
                "trace_id": f"id{n}",
                "tool": "t",
                "pad": "x" * 500,
            }
        )
    files = sorted(tmp_path.glob("*/*.json"))
    assert sum(p.stat().st_size for p in files) <= 3_000
    assert "id9" in files[-1].name
    assert not any("id0-" in p.name for p in files)


def test_reader_joins_the_call_and_the_api_side(tmp_path: Path) -> None:
    mcp_dir, api_dir = tmp_path / "mcp", tmp_path / "api"
    TraceStore(mcp_dir, 10_000_000).write(
        {
            "time": "2026-11-05T10:00:00.000+00:00",
            "trace_id": "abc123",
            "client": "alice",
            "tool": "lookup",
            "arguments": {"question": "carts"},
            "api_calls": [{"path": "search", "status": 200, "ms": 5, "bytes": 9}],
            "outcome": "ok",
            "ms": 9,
            "result": {"answer": 1},
        }
    )
    (api_dir / "2026-11-05").mkdir(parents=True)
    (api_dir / "2026-11-05" / "100000-000001-abc123-search_findings.json").write_text(
        json.dumps(
            {
                "time": "2026-11-05T10:00:00.001+00:00",
                "trace_id": "abc123",
                "path": "/v1/search",
                "handler": "oig_data.api.search.search_findings",
                "status": 200,
                "ms": 4,
                "response_bytes": 9,
                "query": [["q", "carts"]],
                "steps": {
                    "query": {
                        "embedded": True,
                        "embed_ms": 2,
                        "keyword_match": "carts",
                    },
                    "fusion": {
                        "lists": {
                            "keyword:recommendation": {"count": 1, "top": ["r1"]}
                        },
                        "merged_count": 1,
                        "merged_top": [{"rec_id": "r1", "score": 0.016, "ranks": {}}],
                    },
                },
                "sql": ["SELECT 1"],
                "response": {},
            }
        )
    )
    run = [
        sys.executable,
        str(SCRIPT),
        "--mcp-dir",
        str(mcp_dir),
        "--api-dir",
        str(api_dir),
    ]
    listed = subprocess.run([*run, "list"], capture_output=True, text=True, check=True)
    assert "abc123" in listed.stdout and "lookup" in listed.stdout
    shown = subprocess.run(
        [*run, "show", "abc"], capture_output=True, text=True, check=True
    )
    assert "search_findings" in shown.stdout
    assert "keyword:recommendation: 1 hits" in shown.stdout
    assert "r1  score 0.016" in shown.stdout


@pytest.mark.parametrize("command", [["list"], ["api"], ["show"]])
def test_reader_handles_no_traces(tmp_path: Path, command: list[str]) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--mcp-dir",
            str(tmp_path),
            "--api-dir",
            str(tmp_path),
            *command,
        ],
        capture_output=True,
        text=True,
    )
    assert "No" in result.stdout + result.stderr
