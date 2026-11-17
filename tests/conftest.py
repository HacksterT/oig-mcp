"""Shared fixtures: a fake data API behind the real HTTP client."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from oig_mcp import upstream


class FakeApi:
    """Answers GET requests from a route table and records what was asked."""

    def __init__(self) -> None:
        self.routes: dict[str, Any] = {}
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        route = self.routes.get(request.url.path.removeprefix("/v1/"))
        if callable(route):
            route = route(request)
        if route is None:
            return httpx.Response(404, json={"detail": "not found"})
        if isinstance(route, int):
            return httpx.Response(route, json={"detail": "upstream detail"})
        return httpx.Response(200, json=route)

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]


@pytest.fixture
def api(monkeypatch) -> FakeApi:
    fake = FakeApi()
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        upstream.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(
            transport=httpx.MockTransport(lambda r: fake.handle(r)), **kwargs
        ),
    )
    return fake
