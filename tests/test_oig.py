"""Tests for OIG-specific configuration, auth headers, provenance, and tools."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from oig_mcp import utils
from oig_mcp.config import Settings


@pytest.mark.parametrize(
    "url",
    [
        "http://api.example.org/v1/",  # plain http to a non-local host
        "ftp://127.0.0.1/v1/",
        "https://user:pw@api.example.org/v1/",
        "https://api.example.org/v1/?x=1",
        "not a url",
    ],
)
def test_base_url_rejects_unsafe_values(url: str) -> None:
    with pytest.raises(ValidationError):
        Settings(oig_data_api_base_url=url)


def test_base_url_accepts_local_http_and_adds_trailing_slash() -> None:
    s = Settings(oig_data_api_base_url="http://127.0.0.1:8787/v1")
    assert s.oig_data_api_base_url == "http://127.0.0.1:8787/v1/"


def test_base_url_accepts_https() -> None:
    s = Settings(oig_data_api_base_url="https://api.example.org/v1/")
    assert s.oig_data_api_base_url == "https://api.example.org/v1/"


class _CaptureClient:
    headers: dict[str, str] = {}

    def __init__(self, **kwargs: Any) -> None:
        pass

    async def __aenter__(self) -> _CaptureClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    class _Stream:
        async def __aenter__(self) -> httpx.Response:
            r = httpx.Response(200, json={"ok": True})
            r.request = httpx.Request("GET", "http://127.0.0.1/meta")
            return r

        async def __aexit__(self, *args: object) -> None:
            return None

    def stream(self, method: str, path: str, **kwargs: Any) -> _Stream:
        type(self).headers = kwargs.get("headers") or {}
        return self._Stream()


@pytest.mark.asyncio
async def test_access_headers_sent_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(utils.httpx, "AsyncClient", _CaptureClient)
    monkeypatch.setattr(utils.settings, "cf_access_client_id", "id-123")
    monkeypatch.setattr(utils.settings, "cf_access_client_secret", "secret-456")
    await utils.fetch_json("meta")
    assert _CaptureClient.headers["CF-Access-Client-Id"] == "id-123"
    assert _CaptureClient.headers["CF-Access-Client-Secret"] == "secret-456"


@pytest.mark.asyncio
async def test_access_headers_cannot_be_overridden_by_caller(monkeypatch) -> None:
    monkeypatch.setattr(utils.httpx, "AsyncClient", _CaptureClient)
    monkeypatch.setattr(utils.settings, "cf_access_client_id", "id-123")
    monkeypatch.setattr(utils.settings, "cf_access_client_secret", "secret-456")
    await utils.fetch_json("meta", headers={"CF-Access-Client-Id": "spoofed"})
    assert _CaptureClient.headers["CF-Access-Client-Id"] == "id-123"


@pytest.mark.asyncio
async def test_no_access_headers_when_unconfigured(monkeypatch) -> None:
    monkeypatch.setattr(utils.httpx, "AsyncClient", _CaptureClient)
    monkeypatch.setattr(utils.settings, "cf_access_client_id", "")
    monkeypatch.setattr(utils.settings, "cf_access_client_secret", "")
    await utils.fetch_json("meta")
    assert "CF-Access-Client-Id" not in _CaptureClient.headers


def test_provenance_flags_stale_data() -> None:
    old = (date.today() - timedelta(days=45)).isoformat()
    p = utils.build_provenance(old)
    assert p["days_old"] == 45 and p["stale"] is True


def test_provenance_fresh_and_unknown() -> None:
    assert utils.build_provenance(date.today().isoformat())["stale"] is False
    unknown = utils.build_provenance(None)
    assert unknown["stale"] is None and unknown["days_old"] is None


@pytest.mark.asyncio
async def test_dataset_status_returns_hint_when_api_unreachable(monkeypatch) -> None:
    from oig_mcp.app import mcp

    async def boom(*args: Any, **kwargs: Any) -> Any:
        raise utils.UpstreamServiceError("Upstream service request failed.")

    monkeypatch.setattr("oig_mcp.tools.dataset_status.fetch_json", boom)
    result = await mcp.call_tool("vaoig_get_dataset_status", {})
    payload = result.structured_content
    assert payload["error"] == "Upstream service request failed."
    assert "oig-data-source" in payload["hint"]


@pytest.mark.asyncio
async def test_dataset_status_shapes_meta(monkeypatch) -> None:
    from oig_mcp.app import mcp

    async def fake_meta(*args: Any, **kwargs: Any) -> Any:
        return {
            "data_as_of": date.today().isoformat(),
            "counts": {"reports": 5000, "recommendations": 20000},
            "reconciliation": {"open_matches_dashboard": True},
        }

    monkeypatch.setattr("oig_mcp.tools.dataset_status.fetch_json", fake_meta)
    result = await mcp.call_tool("vaoig_get_dataset_status", {})
    payload = result.structured_content
    assert payload["counts"]["recommendations"] == 20000
    assert payload["provenance"]["stale"] is False
