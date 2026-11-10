"""Guided starting points for clients that show MCP prompts.

These only arrange existing tools. Everything they produce is also reachable
through the tools directly, so no client depends on prompt support.
"""

from __future__ import annotations

from fastmcp import FastMCP

_RULES = (
    "Cite the report number and link for every finding, state the data date, and "
    "pass on every entry in notices and each *_basis field a tool returns. Do not "
    "rate or rank "
    "facilities or individuals."
)


def register(mcp: FastMCP) -> None:
    """Register the workflow prompts with the MCP server."""

    @mcp.prompt(name="inspection_readiness_checklist")
    def inspection_readiness_checklist(facility: str) -> str:
        """Turn one facility's OIG record into an inspection preparation checklist."""
        return (
            f"Prepare an inspection readiness checklist for {facility}.\n\n"
            "Call vaoig_get_inspection_brief. If several facilities match, ask which "
            "one is meant. Then write a checklist with four parts: this facility's "
            "open and repeat findings; the most common findings at peers and how "
            "common each is; what peers committed to do; and the estimated next "
            "inspection window, labeled as an estimate.\n\n"
            f"{_RULES}"
        )

    @mcp.prompt(name="open_recommendation_aging_brief")
    def open_recommendation_aging_brief(focus: str | None = None) -> str:
        """Summarize how old open recommendations are, for leadership."""
        scope = f" about {focus}" if focus else ""
        return (
            f"Write a one-page leadership brief on open OIG recommendations{scope}.\n\n"
            "Call vaoig_get_dataset_status for the data date. Call "
            "vaoig_analyze_recommendations grouped by office and by report type, "
            "with filters.status set to open"
            + (f" and keywords set to {focus}" if focus else "")
            + ". Report open counts, typical and oldest age, and how many have been "
            "open more than a year. Do not treat target dates as missed deadlines.\n\n"
            f"{_RULES}"
        )
