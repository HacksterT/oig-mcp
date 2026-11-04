"""vaoig_get_facility_profile: everything OIG has reported about one facility.

Repeat findings and the next-window estimate are fields here, not separate tools.
The API's basis text travels with them because it states what they do not show.
"""

from __future__ import annotations

from typing import Annotated, Any
from urllib.parse import quote

from fastmcp import FastMCP
from pydantic import Field

from oig_mcp.utils import (
    READ_ONLY_TOOL,
    UpstreamServiceError,
    build_provenance,
    fetch_object,
    paginate,
    report_urls,
    tool_error,
)

_LOOKUP_LIMIT = 10


def _pick_station(facility: str, matches: list[dict[str, Any]]) -> str | None:
    """Return the station to open: an exact station match, or the only match."""
    wanted = facility.strip().casefold()
    for match in matches:
        if str(match.get("station_number", "")).casefold() == wanted:
            return match["station_number"]
    return matches[0].get("station_number") if len(matches) == 1 else None


def register(mcp: FastMCP) -> None:
    """Register the facility profile tool with the MCP server."""

    @mcp.tool(
        name="vaoig_get_facility_profile",
        annotations={"title": "Get an OIG facility profile", **READ_ONLY_TOOL},
    )
    async def vaoig_get_facility_profile(
        facility: Annotated[
            str,
            Field(
                min_length=2,
                max_length=200,
                description="Facility name, city, or station number.",
            ),
        ],
        limit: Annotated[
            int, Field(ge=1, le=100, description="Recommendations to return.")
        ] = 25,
        offset: Annotated[int, Field(ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get one facility's reports, inspections, findings, and repeat findings.

        If several facilities match, returns them as matches so the user can choose.
        This server reports records and does not rate facilities.

        Always pass on repeat_findings_basis when discussing repeat findings and
        next_window_basis when discussing the next inspection window. The next
        window is an estimate, must be labeled as one, and OIG publishes no schedule.

        Returns:
            Facility fields, reports, inspections, repeat_findings, the basis text,
            recommendations (open first, paginated), and provenance.
        """
        try:
            lookup = await fetch_object(
                "facilities", {"q": facility, "limit": _LOOKUP_LIMIT}
            )
            matches = lookup.get("items", [])
            if not matches:
                return {
                    "error": f"No facility matched '{facility}'.",
                    "hint": (
                        "Try another name or a station number. If this keeps "
                        "happening, check counts.facilities in "
                        "vaoig_get_dataset_status: the registry may be empty."
                    ),
                }
            station = _pick_station(facility, matches)
            if station is None:
                return {
                    "matches": matches,
                    "total_matches": lookup.get("total"),
                    "hint": "Several facilities matched. Ask which one is meant.",
                    "provenance": build_provenance(lookup.get("data_as_of")),
                }
            profile = await fetch_object(f"facilities/{quote(str(station), safe='')}")
        except UpstreamServiceError as exc:
            return tool_error(exc)

        recommendations = sorted(
            profile.get("recommendations", []),
            key=lambda record: record.get("status") != "open",
        )
        reports = profile.get("reports", [])
        return {
            **profile,
            "recommendations": paginate(recommendations, limit, offset),
            "provenance": build_provenance(
                profile.get("data_as_of"), report_urls(reports)
            ),
        }
