"""vaoig_get_dataset_status: what the data covers and how fresh it is.

The first call an assistant should make in a session that depends on current
status: it reports the collection date, coverage, and whether the last refresh
reconciled with VA OIG's own published open-recommendation counts.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from oig_mcp.utils import (
    CITE_TOTALS,
    UNREACHABLE_HINT,
    UpstreamServiceError,
    build_provenance,
    fetch_json,
)

_FILTER_FACETS = ("report_type", "topic", "action_office", "state", "visn")


async def _filter_values() -> dict[str, list[str]]:
    """Return valid filter values per facet, leaving out any that cannot be read.

    Status matters more than this convenience, so a failure here never fails the tool.
    """
    values: dict[str, list[str]] = {}
    for facet in _FILTER_FACETS:
        try:
            result = await fetch_json(f"taxonomy/{facet}")
        except UpstreamServiceError:
            continue
        items = result.get("items", []) if isinstance(result, dict) else []
        values[facet] = [
            str(item.get("abbreviation") or item["value"])
            for item in items
            if item.get("value") is not None
        ]
    return values


def _explain_reconciliation(reconciliation: dict[str, Any]) -> dict[str, Any]:
    """Say why OIG's open total differs, so its age bands are not read as ours."""
    open_counts = reconciliation.get("open") or {}
    blank_rows = (reconciliation.get("open_set") or {}).get("oig_blank_rows")
    if not blank_rows or open_counts.get("oig") == open_counts.get("database"):
        return reconciliation
    return {
        **reconciliation,
        "note": (
            f"OIG's dashboard shows {open_counts.get('oig')} open and this data has "
            f"{open_counts.get('database')}. A row-by-row comparison found the same "
            f"recommendations in both; the difference is {blank_rows} blank rows on "
            "OIG's pages. oig_open_by_age follows OIG's total, so it does not add up "
            "to this data's open count."
        ),
    }


def register(mcp: FastMCP) -> None:
    """Register the dataset status tool with the MCP server."""

    @mcp.tool(
        name="vaoig_get_dataset_status",
        annotations={
            "title": "Get OIG dataset status",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def vaoig_get_dataset_status() -> dict[str, Any]:
        """Report the coverage and freshness of the VA OIG recommendations data.

        Use this before answering questions about current recommendation status,
        or when a user asks how up to date the data is. The data is a structured
        copy of VA OIG's public reports, recommendations, and report PDFs,
        refreshed on a schedule.

        Returns:
            data_as_of (collection date), counts of reports and recommendations,
            open-recommendation reconciliation against the OIG dashboard,
            filter_values (valid values for search and analysis filters), and a
            provenance block with a stale flag and how to cite. On failure, an error
            with a hint.
        """
        try:
            meta = await fetch_json("meta")
        except UpstreamServiceError as exc:
            return {"error": str(exc), "hint": UNREACHABLE_HINT}

        if not isinstance(meta, dict):
            return {
                "error": "The data API returned an unexpected shape for meta.",
                "hint": "Check that the API and this server versions match.",
            }

        provenance = build_provenance(
            meta.get("data_as_of"),
            ["https://www.vaoig.gov/reports/data-dashboard"],
            citation=CITE_TOTALS,
        )
        result = {
            "data_as_of": meta.get("data_as_of"),
            "counts": meta.get("counts", {}),
            "reconciliation": _explain_reconciliation(meta.get("reconciliation", {})),
            "filter_values": await _filter_values(),
            "provenance": provenance,
        }

        return result
