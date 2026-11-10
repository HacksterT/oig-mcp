"""vaoig_analyze_recommendations: filter a set and group it.

The one analysis tool. It replaces separate theme trend and closure performance
tools, which had the same shape. Time to close and target dates are fields in
its results. Facilities are deliberately not a grouping, because the server does
not rate them.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from oig_mcp.models import Analysis, AnalysisGroup, RecommendationFilters, output_schema
from oig_mcp.utils import (
    CITE_TOTALS,
    READ_ONLY_TOOL,
    UpstreamServiceError,
    build_provenance,
    fetch_object,
    tool_error,
)

_SOURCE_URLS = ["https://www.vaoig.gov/recommendations-all"]

_YEAR_READINGS = (
    "A change over time has more than one reading: a falling count can mean the "
    "problem improved, or that inspection protocols, report volume, or OIG's "
    "attention changed. Present both."
)
_YEAR_REPORT_COUNT = (
    "report_count includes reports with no recommendations when only report "
    "filters are set. With keywords, status, action_office, or node_id it counts "
    "only reports with a matching recommendation."
)
_GROUP_OVERLAP = (
    "A recommendation naming two offices counts for both, and a report with two "
    "topics counts for both, so group sizes can sum to more than the filtered total."
)
_TOPIC_COVERAGE = (
    "OIG tagged only about a quarter of reports with a topic, so topic results "
    "cover only those reports."
)
_NO_GEOGRAPHY = (
    "A VISN or state filter leaves out recommendations that carry no VISN or state, "
    "such as those from national reviews and from reports covering more than one "
    "VISN. Results added up across every VISN or state can fall well short of the "
    "total; run the same analysis without that filter to see the full count."
)
_TOPIC_CO_TAGS = (
    "Grouping by topic with a topic filter also returns the other topics those "
    "reports carry. The row for the filtered topic is its count. To count one topic, "
    "group by year instead: each recommendation has one year, so recommendation_total "
    "is exact."
)
_NO_CLOSURE_DATES = (
    "No closure dates are available for this set, so time to close cannot be "
    "stated from it."
)
_PARTIAL_CLOSURE_DATES = (
    "Read day statistics with days_sample_size, which is smaller than closed_count "
    "for some groups. About 6 percent of closed recommendations, mostly from 2013 "
    "to 2016, show no closure date on OIG's site."
)
# The API also compares closure dates with facilities' target dates. Those counts stay
# out of this tool: a target is the facility's estimate and a closure date appears to
# record OIG's closure, so they would invite a miss rate the data cannot support.
_TARGET_FIELDS = (
    "with_target_date",
    "closed_by_target",
    "closed_after_target",
    "open_past_target",
    "median_days_after_target",
)
_YEAR_MEDIAN_ZERO = (
    "A median of 0 days means at least half of that year's closed recommendations "
    "closed the day the report came out, presumably fixed beforehand. It is not a "
    "typical time to close."
)
_PUBLICATION_DAY = (
    "closed_on_publication_day counts recommendations closed the day the report came "
    "out, presumably fixed beforehand. They can pull a small group's median to 0."
)


def _closure_notices(items: list[dict[str, Any]], median_field: str) -> list[str]:
    """Describe the closure dates behind this result, from the result itself."""
    if not any(item.get(median_field) is not None for item in items):
        return [_NO_CLOSURE_DATES] if items else []
    short = any(
        item.get("days_sample_size", 0) < item.get("closed_count", 0) for item in items
    )
    return [_PARTIAL_CLOSURE_DATES] if short else []


def _notices(
    group_by: AnalysisGroup,
    filters: RecommendationFilters | None,
    items: list[dict[str, Any]],
) -> list[str]:
    """Return the data limits that apply to this particular result."""
    notices: list[str] = []
    if group_by is AnalysisGroup.YEAR:
        notices += [_YEAR_READINGS, _YEAR_REPORT_COUNT]
        notices += _closure_notices(items, "median_days_to_closure")
        if any(item.get("median_days_to_closure") == 0 for item in items):
            notices.append(_YEAR_MEDIAN_ZERO)
    else:
        notices.append(_GROUP_OVERLAP)
        notices += _closure_notices(items, "median_days")
        if any(item.get("closed_on_publication_day") for item in items):
            notices.append(_PUBLICATION_DAY)
    if group_by is AnalysisGroup.TOPIC or (filters and filters.topic):
        notices.append(_TOPIC_COVERAGE)
    if group_by is AnalysisGroup.TOPIC and filters and filters.topic:
        notices.append(_TOPIC_CO_TAGS)
    if filters and (filters.visn or filters.state):
        notices.append(_NO_GEOGRAPHY)
    return notices


def register(mcp: FastMCP) -> None:
    """Register the analysis tool with the MCP server."""

    @mcp.tool(
        name="vaoig_analyze_recommendations",
        output_schema=output_schema(Analysis),
        annotations={"title": "Analyze OIG recommendations", **READ_ONLY_TOOL},
    )
    async def vaoig_analyze_recommendations(
        group_by: Annotated[
            AnalysisGroup,
            Field(
                description=(
                    "year for counts over time, and for an exact total of one set: "
                    "each recommendation has one year. office, topic, or report_type "
                    "for time to close, not-implemented rate, and open-item aging; "
                    "their groups overlap, so do not add them up."
                )
            ),
        ],
        keywords: Annotated[
            str | None,
            Field(
                max_length=200,
                description=(
                    "Limit to recommendations containing all of these words. Use a "
                    "few words, not a sentence, which usually matches nothing."
                ),
            ),
        ] = None,
        filters: Annotated[
            RecommendationFilters | None,
            Field(description="Limit the set before grouping, for example by status."),
        ] = None,
    ) -> dict[str, Any]:
        """Count and measure a filtered set of recommendations by a chosen grouping.

        Use this for exact counts, trends over time, how long recommendations take
        to close, not-implemented rates, and how old open items are. It does not
        measure whether target dates were met, because the data cannot establish
        that; see target_basis. Group by year for a trend, or to count one topic or
        theme exactly. Group by office, topic, or report_type for closure and aging
        measures. Facilities cannot be a grouping, because this server reports
        records and does not rate or rank facilities. To compare places, filter by
        one VISN or state at a time; the result names the filters it used.

        Always pass on every entry in notices, and target_basis when discussing
        target dates.

        Returns:
            group_by, keywords, and filters (echoed, so each result names what
            produced it), items (one per group), total_groups, recommendation_total
            (by year only), notices, target_basis, and provenance. By year:
            report, recommendation, open, and closed counts and median days to
            closure. Otherwise: those counts with median and quartile days to
            closure, not-implemented rate, and open-item aging.
        """
        params: dict[str, Any] = {
            "q": keywords,
            **(filters.to_params() if filters else {}),
        }
        if group_by is AnalysisGroup.YEAR:
            path = "metrics/counts"
        else:
            path = "metrics/closure"
            params["group_by"] = group_by.value
        try:
            result = await fetch_object(path, params)
        except UpstreamServiceError as exc:
            raise tool_error(exc) from exc

        items = [
            {key: value for key, value in item.items() if key not in _TARGET_FIELDS}
            for item in result.get("items", [])
        ]
        return {
            "group_by": group_by.value,
            "keywords": keywords,
            "filters": filters.to_params() if filters else {},
            "total_groups": result.get("total"),
            "recommendation_total": (
                sum(item.get("recommendation_count") or 0 for item in items)
                if group_by is AnalysisGroup.YEAR
                else None
            ),
            "items": items,
            "notices": _notices(group_by, filters, items),
            "target_basis": result.get("target_basis"),
            "provenance": build_provenance(
                result.get("data_as_of"),
                _SOURCE_URLS,
                citation=CITE_TOTALS,
                quoted=False,
            ),
        }
