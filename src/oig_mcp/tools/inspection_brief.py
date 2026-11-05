"""vaoig_get_inspection_brief: one facility's inspection preparation in one call.

This lives on the server so that every MCP client gets the same facts. It adds no
data of its own: it combines the facility profile, recurring findings under the
current inspection program, and what peer facilities committed to do.

Findings are listed by how common they are, as the API orders them. Nothing here
scores severity or rates a facility.
"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from oig_mcp.tools.facility_profile import (
    NO_RESPONSE_NOTICE,
    PAST_WINDOW_NOTICE,
    fetch_profile,
    lacks_response,
    window_has_passed,
)
from oig_mcp.tools.systemic_clusters import CLUSTER_CAVEAT
from oig_mcp.utils import (
    READ_ONLY_TOOL,
    UpstreamServiceError,
    build_provenance,
    fetch_object,
    report_urls,
    tool_error,
)

_CURRENT_PROGRAM = "healthcare-facility-inspection"
_OPEN_FINDINGS_SHOWN = 10
_PEER_ACTIONS_PER_FINDING = 2
_PEER_ACTION_CHARS = 800

_ORDER_NOTICE = (
    "Peer findings are listed by how common they are, not by severity or importance, "
    "and do not predict what an inspection will find. This server does not rate "
    "facilities."
)
_PEER_ACTION_NOTICE = (
    "Peer actions are the closest matches by wording and meaning, from other "
    "facilities, and may not all belong to the listed group. Target dates are each "
    "facility's own estimate, not a measure of missed deadlines."
)
_GROUP_NOTICE = (
    "facility_in_this_group is false when none of this facility's recommendations "
    "were placed in that group. It does not mean the facility was never cited for "
    "the theme: similar findings can sit in other groups. Check own_history."
)
_FALLBACK_NOTICE = (
    "Semantic search was unavailable, so peer actions come from keyword search only."
)
_PEER_ACTIONS_FAILED = (
    "Peer actions could not be retrieved for at least one finding, so that part of "
    "this brief is incomplete."
)


async def _peer_actions(label: str, station: str) -> dict[str, Any] | None:
    """Find what other facilities committed to do about a finding, if retrievable."""
    try:
        return await fetch_object(
            "search",
            {
                "q": label,
                "report_type": _CURRENT_PROGRAM,
                "exclude_station_number": station,
                "has_response": True,
                "limit": _PEER_ACTIONS_PER_FINDING,
            },
        )
    except UpstreamServiceError:
        return None


def _peer_action(item: dict[str, Any]) -> dict[str, Any]:
    """Keep what a reader needs to use and cite one peer's commitment."""
    response = item.get("response") or {}
    action = response.get("corrective_action") or ""
    return {
        "report_number": item.get("report_number"),
        "title": item.get("title"),
        "url": item.get("url"),
        "status": item.get("status"),
        "recommendation": item.get("text"),
        "concur": response.get("concur"),
        "target_date": response.get("target_date"),
        "corrective_action": action[:_PEER_ACTION_CHARS],
        "corrective_action_truncated": len(action) > _PEER_ACTION_CHARS,
        "pdf_page": response.get("page_no"),
    }


def _next_inspection(profile: dict[str, Any]) -> dict[str, Any] | None:
    """Return the labeled estimate and the latest inspection it is based on."""
    latest = next(
        (i for i in profile.get("inspections", []) if i.get("is_latest")), None
    )
    if latest is None:
        return None
    return {
        "estimated_window": latest.get("next_window_estimate"),
        "is_estimate": latest.get("next_window_is_estimate"),
        "basis": profile.get("next_window_basis"),
        "latest_inspection": {
            "program": latest.get("program"),
            "inspection_end": latest.get("inspection_end"),
            "published_at": latest.get("published_at"),
            "next_window_based_on": latest.get("next_window_based_on"),
            "report_number": latest.get("report_number"),
            "url": latest.get("url"),
        },
    }


def _own_history(profile: dict[str, Any]) -> dict[str, Any]:
    """Summarize the facility's own record, with its open findings in full."""
    recommendations = profile.get("recommendations", [])
    open_findings = [r for r in recommendations if r.get("status") == "open"]
    return {
        "report_count": profile.get("report_count"),
        "recommendation_count": profile.get("recommendation_count"),
        "open_count": profile.get("open_count"),
        "open_findings": open_findings[:_OPEN_FINDINGS_SHOWN],
        "repeat_findings": profile.get("repeat_findings", []),
        "repeat_findings_basis": profile.get("repeat_findings_basis"),
    }


def register(mcp: FastMCP) -> None:
    """Register the inspection brief tool with the MCP server."""

    @mcp.tool(
        name="vaoig_get_inspection_brief",
        annotations={"title": "Get an OIG inspection brief", **READ_ONLY_TOOL},
    )
    async def vaoig_get_inspection_brief(
        facility: Annotated[
            str,
            Field(
                min_length=2,
                max_length=200,
                description="Facility name, city, or station number.",
            ),
        ],
        top_findings: Annotated[
            int, Field(ge=1, le=10, description="Common peer findings to include.")
        ] = 5,
    ) -> dict[str, Any]:
        """Prepare one facility for an OIG inspection from the public record.

        Use this when someone asks for help preparing for an inspection. If several
        facilities match, returns them as matches so the user can choose.

        Always pass on the basis text and notices. The next window is an estimate and
        must be labeled as one, because OIG publishes no schedule.

        Returns:
            facility, next_inspection (the estimate and its basis), own_history (open
            findings, repeat findings, and their basis), common_peer_findings (how
            common each is, whether this facility is in that group, typical time to
            close, and what peers committed to do), notices, and provenance.
        """
        try:
            profile = await fetch_profile(facility)
            if "error" in profile or "matches" in profile:
                return profile
            clusters = await fetch_object(
                "clusters", {"report_type": _CURRENT_PROGRAM, "limit": top_findings}
            )
        except UpstreamServiceError as exc:
            raise tool_error(exc) from exc

        station = profile.get("station_number")
        items = clusters.get("items", [])
        searches = await asyncio.gather(
            *(_peer_actions(item.get("label", ""), station) for item in items)
        )
        cited_here = {
            r.get("cluster_id")
            for r in profile.get("recommendations", [])
            if r.get("cluster_id") is not None
        }
        in_scope = clusters.get("reports_in_scope")

        findings = []
        for item, search in zip(items, searches, strict=True):
            matching = item.get("matching_report_count")
            findings.append(
                {
                    "cluster_id": item.get("cluster_id"),
                    "finding": item.get("label"),
                    "how_common": f"{matching} of {in_scope} reports in scope",
                    "facility_in_this_group": item.get("cluster_id") in cited_here,
                    "open_count": item.get("open_count"),
                    "days_sample_size": item.get("days_sample_size"),
                    "median_days_to_close": item.get("median_days"),
                    "q1_days": item.get("q1_days"),
                    "q3_days": item.get("q3_days"),
                    "peer_actions": [
                        _peer_action(i) for i in (search or {}).get("items", [])
                    ],
                }
            )

        notices = [_ORDER_NOTICE, _PEER_ACTION_NOTICE, _GROUP_NOTICE, CLUSTER_CAVEAT]
        if None in searches:
            notices.insert(0, _PEER_ACTIONS_FAILED)
        if any(s and s.get("search_mode") != "hybrid" for s in searches):
            notices.insert(0, _FALLBACK_NOTICE)
        if lacks_response(_own_history(profile)["open_findings"]):
            notices.append(NO_RESPONSE_NOTICE)
        if window_has_passed(profile):
            notices.append(PAST_WINDOW_NOTICE)
        if profile.get("recommendations_has_more"):
            notices.append(
                "This facility has more recommendations than were checked, so "
                "facility_in_this_group covers only its newest 100."
            )

        peer_items = [i for s in searches if s for i in s.get("items", [])]
        return {
            "facility": {
                "station_number": station,
                "name": profile.get("name"),
                "visn": profile.get("visn"),
                "state": profile.get("state"),
            },
            "next_inspection": _next_inspection(profile),
            "own_history": _own_history(profile),
            "common_peer_findings": findings,
            "notices": notices,
            "provenance": build_provenance(
                profile.get("data_as_of"),
                report_urls(profile.get("reports", []), peer_items),
            ),
        }
