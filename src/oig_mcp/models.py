"""Pydantic models and enums for tool parameters and responses.

Typed parameters give MCP clients a precise schema, which helps the LLM call
tools correctly. Enums cover closed sets of values; models cover structured
inputs and outputs shared across tools.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RecommendationStatus(str, Enum):
    """Recommendation status as VA OIG publishes it."""

    OPEN = "open"
    CLOSED_IMPLEMENTED = "closed-implemented"
    CLOSED_NOT_IMPLEMENTED = "closed-not-implemented"


class AnalysisGroup(str, Enum):
    """How the analysis tool groups a filtered set. Facilities are not a group."""

    YEAR = "year"
    OFFICE = "office"
    TOPIC = "topic"
    REPORT_TYPE = "report_type"


_ISO_DATE = r"^\d{4}-\d{2}-\d{2}$"


class RecommendationFilters(BaseModel):
    """Filters shared by the search and analysis tools.

    Unknown names are rejected rather than ignored, because a dropped filter
    would silently return numbers for a wider set than the caller asked about.
    """

    model_config = ConfigDict(extra="forbid")

    status: list[RecommendationStatus] | None = Field(
        default=None, description="Keep recommendations with any of these statuses."
    )
    action_office: str | None = Field(
        default=None,
        description="Office abbreviation such as VHA, or part of an office name.",
    )
    topic: str | None = Field(
        default=None,
        description="OIG topic label. OIG tagged only about a quarter of reports.",
    )
    report_type: str | None = Field(
        default=None,
        description=(
            "Report type slug or label, for example "
            "healthcare-facility-inspection for the current inspection program."
        ),
    )
    visn: str | None = Field(default=None, description="VISN number, for example 17.")
    state: str | None = Field(default=None, description="State name.")
    published_from: str | None = Field(
        default=None, pattern=_ISO_DATE, description="Earliest date, YYYY-MM-DD."
    )
    published_to: str | None = Field(
        default=None, pattern=_ISO_DATE, description="Latest date, YYYY-MM-DD."
    )
    report_number: str | None = Field(
        default=None, description="Exact OIG report number."
    )
    station_number: str | None = Field(
        default=None, description="Only this facility's findings."
    )
    exclude_station_number: str | None = Field(
        default=None, description="Leave this facility out, to see only its peers."
    )
    node_id: int | None = Field(default=None, description="One report's node id.")
    domain: str | None = Field(
        default=None,
        description=(
            "Inspection domain of the facility response. Usually empty on newer "
            "Healthcare Facility Inspection responses, so this misses most of them."
        ),
    )
    has_response: bool | None = Field(
        default=None,
        description="Keep only findings with, or without, a facility response.",
    )

    def to_params(self) -> dict[str, Any]:
        """Return the API query parameters for the filters that are set."""
        return self.model_dump(mode="json", exclude_none=True)


class PaginationParams(BaseModel):
    """Reusable pagination inputs for list-style tools."""

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of items to return (1–100).",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip from the start of the result set.",
    )


class Provenance(BaseModel):
    """Where a response's data came from and how fresh it is.

    Every tool response carries one of these so the assistant can cite its
    source and warn when the data may be out of date.
    """

    source: str = Field(
        default="VA Office of Inspector General public pages (vaoig.gov)",
        description="Origin of the underlying data.",
    )
    data_as_of: str | None = Field(
        default=None, description="Date the data was collected (YYYY-MM-DD)."
    )
    days_old: int | None = Field(
        default=None, description="Days between data_as_of and today."
    )
    stale: bool | None = Field(
        default=None,
        description="True when the data is older than the configured threshold.",
    )
    source_urls: list[str] = Field(
        default_factory=list, description="vaoig.gov pages backing this response."
    )
    citation: str = Field(
        default="", description="How to cite this response in an answer."
    )
    quoted_fields: list[str] = Field(
        default_factory=list,
        description="Fields anywhere in this response that quote OIG report text.",
    )
    quoted_text: str = Field(default="", description="How to treat the quoted fields.")
