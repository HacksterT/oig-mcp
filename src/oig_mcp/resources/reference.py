"""Reference lists for clients that read MCP resources.

Tool-only clients get the same filter values from vaoig_get_dataset_status.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from oig_mcp.utils import UpstreamServiceError, fetch_object, hint_for

_PAGE_SIZE = 100
# The registry has about 1,500 facilities. A cap and a forward-only offset keep a
# misbehaving upstream from looping this resource forever.
_MAX_PAGES = 50
FACETS = frozenset(
    {
        "topic",
        "state",
        "visn",
        "district",
        "mmc",
        "author_office",
        "special_project",
        "action_office",
        "report_type",
    }
)


async def _all_facilities() -> dict[str, Any]:
    """Read every page of the facility registry."""
    facilities: list[dict[str, Any]] = []
    offset = 0
    data_as_of = None
    for _ in range(_MAX_PAGES):
        page = await fetch_object("facilities", {"limit": _PAGE_SIZE, "offset": offset})
        facilities.extend(page.get("items", []))
        data_as_of = page.get("data_as_of")
        following = page.get("next_offset") if page.get("has_more") else None
        if not isinstance(following, int) or following <= offset:
            break
        offset = following
    return {"data_as_of": data_as_of, "total": len(facilities), "items": facilities}


def register(mcp: FastMCP) -> None:
    """Register the reference resources with the MCP server."""

    @mcp.resource("vaoig://taxonomy/{facet}", mime_type="application/json")
    async def taxonomy(facet: str) -> dict[str, Any]:
        """OIG's values for a facet, with counts.

        Facets: topic, state, visn, district, mmc, author_office, special_project,
        action_office, report_type.
        """
        if facet not in FACETS:
            return {"error": f"Unknown facet. Use one of: {', '.join(sorted(FACETS))}."}
        try:
            return await fetch_object(f"taxonomy/{facet}")
        except UpstreamServiceError as exc:
            return {"error": str(exc), "hint": hint_for(exc)}

    @mcp.resource("vaoig://facilities", mime_type="application/json")
    async def facilities() -> dict[str, Any]:
        """Every facility in the registry, with station number, VISN, and state."""
        try:
            return await _all_facilities()
        except UpstreamServiceError as exc:
            return {"error": str(exc), "hint": hint_for(exc)}
