"""vaoig_get_dataset_status: what the data covers and how fresh it is.

The first call an assistant should make in a session that depends on current
status: it reports the collection date, coverage, and whether the last refresh
reconciled with VA OIG's own published open-recommendation counts.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from oig_mcp.models import ResponseFormat
from oig_mcp.utils import UpstreamServiceError, build_provenance, fetch_json

_UNREACHABLE_HINT = (
    "The OIG data API is not reachable. Start the oig-data-source API locally "
    "(docker compose up -d) or check OIG_DATA_API_BASE_URL and the Cloudflare Access "
    "service token in the server's environment."
)


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
    async def vaoig_get_dataset_status(
        response_format: ResponseFormat = ResponseFormat.JSON,
    ) -> dict[str, Any] | str:
        """Report the coverage and freshness of the VA OIG recommendations data.

        Use this before answering questions about current recommendation status,
        or when a user asks how up to date the data is. The data is a structured
        copy of VA OIG's public reports, recommendations, and report PDFs,
        refreshed on a schedule.

        Returns:
            data_as_of (collection date), counts of reports and recommendations,
            open-recommendation reconciliation against the OIG dashboard, and a
            provenance block with a stale flag. On failure, an error with a hint.
        """
        try:
            meta = await fetch_json("meta")
        except UpstreamServiceError as exc:
            return {"error": str(exc), "hint": _UNREACHABLE_HINT}

        if not isinstance(meta, dict):
            return {
                "error": "The data API returned an unexpected shape for meta.",
                "hint": "Check that the API and this server versions match.",
            }

        provenance = build_provenance(
            meta.get("data_as_of"), ["https://www.vaoig.gov/reports/data-dashboard"]
        )
        result = {
            "data_as_of": meta.get("data_as_of"),
            "counts": meta.get("counts", {}),
            "reconciliation": meta.get("reconciliation", {}),
            "provenance": provenance,
        }

        if response_format is ResponseFormat.MARKDOWN:
            counts = result["counts"] or {}
            lines = [
                "# VA OIG recommendations data",
                "",
                f"- Data as of: {result['data_as_of'] or 'unknown'}",
            ]
            lines += [f"- {k.replace('_', ' ')}: {v}" for k, v in counts.items()]
            if provenance["stale"]:
                lines.append(
                    f"- Warning: data is {provenance['days_old']} days old; "
                    "statuses may have changed."
                )
            return "\n".join(lines)

        return result
