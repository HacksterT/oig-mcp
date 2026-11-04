"""Reference lists for clients that read MCP resources.

Tool-only clients get the same filter values from vaoig_get_dataset_status.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastmcp import FastMCP

from oig_mcp.utils import UNREACHABLE_HINT, UpstreamServiceError, fetch_object

_PAGE_SIZE = 100


async def _all_facilities() -> dict[str, Any]:
    """Read every page of the facility registry."""
    facilities: list[dict[str, Any]] = []
    offset: int | None = 0
    data_as_of = None
    while offset is not None:
        page = await fetch_object("facilities", {"limit": _PAGE_SIZE, "offset": offset})
        facilities.extend(page.get("items", []))
        data_as_of = page.get("data_as_of")
        offset = page.get("next_offset") if page.get("has_more") else None
    return {"data_as_of": data_as_of, "total": len(facilities), "items": facilities}


def register(mcp: FastMCP) -> None:
    """Register the reference resources with the MCP server."""

    @mcp.resource("vaoig://taxonomy/{facet}", mime_type="application/json")
    async def taxonomy(facet: str) -> dict[str, Any]:
        """OIG's values for a facet, with counts.

        Facets: topic, state, visn, district, mmc, author_office, special_project,
        action_office, report_type.
        """
        try:
            return await fetch_object(f"taxonomy/{quote(facet, safe='')}")
        except UpstreamServiceError as exc:
            if exc.status_code == 404:
                return {"error": f"Unknown facet '{facet}'."}
            return {"error": str(exc), "hint": UNREACHABLE_HINT}

    @mcp.resource("vaoig://facilities", mime_type="application/json")
    async def facilities() -> dict[str, Any]:
        """Every facility in the registry, with station number, VISN, and state."""
        try:
            return await _all_facilities()
        except UpstreamServiceError as exc:
            return {"error": str(exc), "hint": UNREACHABLE_HINT}
