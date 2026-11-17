"""Hardening from the security review: bounded traces, private files, bounded input."""

from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Any

import httpx
import pytest

from oig_mcp import failures, tracing, upstream
from oig_mcp.resources import reference


def test_traced_arguments_are_bounded() -> None:
    record, token = tracing.start(
        "client", "tool", {"question": "x" * 3_000_000, "ids": list(range(5000))}
    )
    tracing.finish(token)
    question = record["arguments"]["question"]
    assert len(question) < tracing.MAX_TRACED_STRING + 50
    assert question.endswith("[3000000 chars]")
    assert len(record["arguments"]["ids"]) == tracing.MAX_TRACED_ITEMS + 1


def test_an_oversized_trace_keeps_the_call_but_drops_the_result(tmp_path: Path) -> None:
    store = tracing.TraceStore(tmp_path, max_bytes=10_000_000)
    record, token = tracing.start("client", "tool", {"question": "carts"})
    tracing.finish(token)
    record["result"] = {"items": ["y" * 1000] * 1000}
    store.write(record)
    written = next(tmp_path.glob("*/*.json"))
    assert written.stat().st_size < tracing.MAX_RECORD_BYTES
    saved = json.loads(written.read_text())
    assert saved["arguments"] == {"question": "carts"}
    assert saved["result"].startswith("[omitted:")


def test_trace_files_are_private(tmp_path: Path) -> None:
    store = tracing.TraceStore(tmp_path, max_bytes=10_000_000)
    record, token = tracing.start("client", "tool", {})
    tracing.finish(token)
    store.write(record)
    written = next(tmp_path.glob("*/*.json"))
    assert stat.S_IMODE(written.stat().st_mode) == 0o600
    assert stat.S_IMODE(written.parent.stat().st_mode) == 0o700


async def test_status_list_is_bounded() -> None:
    from oig_mcp.app import mcp

    with pytest.raises(Exception, match="at most 3 items"):
        await mcp.call_tool(
            "vaoig_analyze_recommendations",
            {"group_by": "year", "filters": {"status": ["open"] * 8000}},
        )


async def test_an_invalid_request_becomes_a_clean_error(monkeypatch) -> None:
    class Broken:
        def stream(self, *args: Any, **kwargs: Any) -> Any:
            raise httpx.InvalidURL("URL component 'query' too long")

    monkeypatch.setattr(upstream, "_shared_client", Broken())
    with pytest.raises(failures.UpstreamServiceError) as caught:
        await upstream.fetch_json("metrics/counts", {"q": "x"})
    assert caught.value.status_code == 400
    assert "too large or malformed" in str(caught.value)


async def test_unknown_facet_is_refused_without_a_request(monkeypatch) -> None:
    async def never(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("no request should be made")

    monkeypatch.setattr(reference, "fetch_object", never)
    from oig_mcp.app import mcp

    contents = await mcp.read_resource("vaoig://taxonomy/meta-secrets")
    assert "Unknown facet" in str(contents)


async def test_facility_paging_stops_when_the_offset_does_not_advance(
    monkeypatch,
) -> None:
    calls = []

    async def stuck(path: str, params: dict[str, Any]) -> dict[str, Any]:
        calls.append(params["offset"])
        return {"items": [{"station_number": "1"}], "has_more": True, "next_offset": 0}

    monkeypatch.setattr(reference, "fetch_object", stuck)
    result = await reference._all_facilities()
    assert calls == [0]
    assert result["total"] == 1


def test_usage_log_files_stay_private_after_rotation(tmp_path: Path) -> None:
    import logging

    from oig_mcp.middleware import _PrivateRotatingFileHandler

    path = tmp_path / "usage.log"
    path.write_text("")
    path.chmod(0o644)  # a file left from before must be tightened too
    handler = _PrivateRotatingFileHandler(path, maxBytes=200, backupCount=2)
    log = logging.getLogger("test.rotation")
    log.addHandler(handler)
    try:
        for _ in range(20):
            log.warning("x" * 50)
    finally:
        log.removeHandler(handler)
        handler.close()
    files = sorted(tmp_path.glob("usage.log*"))
    assert len(files) == 3
    assert all(stat.S_IMODE(f.stat().st_mode) == 0o600 for f in files)


@pytest.mark.asyncio
async def test_facet_lists_agree() -> None:
    from fastmcp import Client

    from oig_mcp.app import mcp
    from oig_mcp.tools.dataset_status import _FILTER_FACETS

    assert set(_FILTER_FACETS) <= reference.FACETS
    # The resource's description lists the facets for clients by hand.
    async with Client(mcp) as client:
        templates = await client.list_resource_templates()
    (taxonomy,) = [t for t in templates if "taxonomy" in t.uri_template]
    assert all(facet in taxonomy.description for facet in reference.FACETS)
