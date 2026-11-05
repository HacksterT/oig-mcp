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
    CITE_TOTALS,
    READ_ONLY_TOOL,
    UpstreamServiceError,
    build_provenance,
    fetch_object,
    paginate,
    report_urls,
    shorten_responses,
    tool_error,
)

_LOOKUP_LIMIT = 10
_MAX_RECOMMENDATIONS = 100  # the API returns only the newest 25 unless asked
_ACTION_CHARS = 300

NO_RESPONSE_NOTICE = (
    "A finding with no facility response means none was extracted from the report. "
    "Responses are extracted mainly from inspection reports, so this does not show "
    "that the facility failed to respond or that anything is overdue."
)


PAST_WINDOW_NOTICE = (
    "The estimated next window is already past. It is only the last inspection plus "
    "about three years, so this does not show that the facility is overdue."
)


def window_has_passed(profile: dict[str, Any]) -> bool:
    """True if the latest inspection's estimate is before the data's own date."""
    latest = next(
        (i for i in profile.get("inspections", []) if i.get("is_latest")), None
    )
    estimate = (latest or {}).get("next_window_estimate")
    data_as_of = profile.get("data_as_of")
    return bool(estimate and data_as_of and estimate < data_as_of)


def lacks_response(recommendations: list[dict[str, Any]]) -> bool:
    """True if any finding has no extracted corrective action."""
    return any(not record.get("corrective_action") for record in recommendations)


def _pick_station(facility: str, matches: list[dict[str, Any]]) -> str | None:
    """Return the station to open: an exact station match, or the only match."""
    wanted = facility.strip().casefold()
    for match in matches:
        if str(match.get("station_number", "")).casefold() == wanted:
            return match["station_number"]
    return matches[0].get("station_number") if len(matches) == 1 else None


async def fetch_profile(facility: str) -> dict[str, Any]:
    """Resolve a name, city, or station to its profile.

    Returns the profile, or a dict with `error` or `matches` for the caller to pass
    on when no single facility can be chosen.
    """
    lookup = await fetch_object("facilities", {"q": facility, "limit": _LOOKUP_LIMIT})
    matches = lookup.get("items", [])
    if not matches:
        return {
            "error": f"No facility matched '{facility}'.",
            "hint": (
                "Try another name or a station number. If this keeps happening, "
                "check counts.facilities in vaoig_get_dataset_status: the registry "
                "may be empty."
            ),
        }
    station = _pick_station(facility, matches)
    if station is None:
        return {
            "matches": matches,
            "total_matches": lookup.get("total"),
            "hint": "Several facilities matched. Ask which one is meant.",
            "provenance": build_provenance(
                lookup.get("data_as_of"), citation=CITE_TOTALS
            ),
        }
    return await fetch_object(
        f"facilities/{quote(str(station), safe='')}",
        {"recommendations_limit": _MAX_RECOMMENDATIONS},
    )


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
            recommendations (the newest 100, open first, paginated), notices, and
            provenance. Within recommendations, has_more means another page is
            available, and has_older_beyond_100 means older ones exist that no page
            will show. Long corrective actions are shortened and marked;
            vaoig_get_report has the full text.
        """
        try:
            profile = await fetch_profile(facility)
        except UpstreamServiceError as exc:
            raise tool_error(exc) from exc
        if "error" in profile or "matches" in profile:
            return profile

        recommendations = sorted(
            profile.get("recommendations", []),
            key=lambda record: record.get("status") != "open",
        )
        reports = profile.get("reports", [])
        page = paginate(recommendations, limit, offset)
        page["items"] = shorten_responses(page["items"], _ACTION_CHARS)
        page["has_older_beyond_100"] = bool(profile.get("recommendations_has_more"))
        rest = {k: v for k, v in profile.items() if k != "recommendations_has_more"}
        return {
            **rest,
            "recommendations": page,
            "notices": [
                *([NO_RESPONSE_NOTICE] if lacks_response(page["items"]) else []),
                *([PAST_WINDOW_NOTICE] if window_has_passed(profile) else []),
            ],
            "provenance": build_provenance(
                profile.get("data_as_of"), report_urls(reports)
            ),
        }
