"""Pydantic models and enums for tool parameters and responses.

Typed parameters give MCP clients a precise schema, which helps the LLM call
tools correctly. Enums cover closed sets of values; models cover structured
inputs and outputs shared across tools.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, Any, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator


class RecommendationStatus(str, Enum):
    """Recommendation status as VA OIG publishes it."""

    OPEN = "open"
    CLOSED_IMPLEMENTED = "closed-implemented"
    CLOSED_NOT_IMPLEMENTED = "closed-not-implemented"


# Paging bounds shared by every tool that pages. Each tool adds its own description
# with Annotated[PageLimit, Field(description=...)]; Pydantic merges the two.
MAX_OFFSET = 10_000
PageLimit = Annotated[int, Field(ge=1, le=100)]
PageOffset = Annotated[int, Field(ge=0, le=MAX_OFFSET)]


class AnalysisGroup(str, Enum):
    """How the analysis tool groups a filtered set. Facilities are not a group."""

    YEAR = "year"
    OFFICE = "office"
    TOPIC = "topic"
    REPORT_TYPE = "report_type"


_ISO_DATE = r"^\d{4}-\d{2}-\d{2}$"


# Postal codes for the state filter. The API stores and matches full names.
STATE_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "PR": "Puerto Rico",
    "GU": "Guam",
    "VI": "Virgin Islands",
    "AS": "American Samoa",
    "MP": "Northern Mariana Islands",
}


# OIG's action offices by abbreviation, named as the data names them. A model often
# writes an office's full name ("Office of Information and Technology"), which the
# API's substring match misses, so a known name is sent as its abbreviation.
OFFICE_NAMES = {
    "VHA": "Veterans Health Administration",
    "VBA": "Veterans Benefits Administration",
    "OIT": "Information and Technology",
    "OALC": "Acquisitions, Logistics, and Construction",
    "OM": "Office of Management",
    "SVA": "Office of the Secretary",
    "HRA": "Human Resources and Administration Office",
    "OSP": "Operations, Security, and Preparedness",
    "EHRM IO": "Electronic Health Record Modernization Integration Office",
    "NCA": "National Cemetery Administration",
    "OGC": "General Counsel",
    "OAWP": "Accountability and Whistleblower Protection",
    "OAEM": "Asset Enterprise Management",
    "OEI": "Office of Enterprise Integration",
    "OPIA": "Public and Intergovernmental Affairs",
}
_OFFICE_ALIASES = {"OI&T": "OIT", "EHRM": "EHRM IO", "EHRMIO": "EHRM IO"}
_FILLER = {"office", "of", "the", "and", "va", "department", "affairs", "u"}


def _office_key(name: str) -> tuple[str, ...]:
    """Words that identify an office, ignoring filler, punctuation, and plurals."""
    words = re.sub(r"[^a-z0-9]+", " ", name.casefold()).split()
    return tuple(sorted({w.rstrip("s") for w in words if w not in _FILLER}))


_OFFICE_KEYS = {_office_key(name): abbr for abbr, name in OFFICE_NAMES.items()}
_OFFICE_KEYS[_office_key("Information Technology")] = "OIT"
_OFFICE_KEYS[_office_key("Office of Acquisition, Logistics, and Construction")] = "OALC"


def office_abbreviation(value: str) -> str | None:
    """The abbreviation for a known office name or abbreviation, else None."""
    text = value.strip()
    upper = text.upper()
    if upper in OFFICE_NAMES:
        return upper
    if upper in _OFFICE_ALIASES:
        return _OFFICE_ALIASES[upper]
    labelled = re.search(r"\(([^)]+)\)\s*$", text)
    if labelled and labelled.group(1).upper() in OFFICE_NAMES:
        return labelled.group(1).upper()
    return _OFFICE_KEYS.get(_office_key(text))


class RecommendationFilters(BaseModel):
    """Filters shared by the search and analysis tools.

    Unknown names are rejected rather than ignored, because a dropped filter
    would silently return numbers for a wider set than the caller asked about.
    """

    model_config = ConfigDict(extra="forbid")

    status: list[RecommendationStatus] | None = Field(
        default=None,
        max_length=len(RecommendationStatus),
        description="Keep recommendations with any of these statuses.",
    )
    action_office: str | None = Field(
        default=None,
        max_length=100,
        description=(
            "Office abbreviation such as VHA, VBA, or OIT. A full office name also "
            "works."
        ),
    )
    topic: str | None = Field(
        default=None,
        max_length=100,
        description="OIG topic label. OIG tagged only about a quarter of reports.",
    )
    report_type: str | None = Field(
        default=None,
        max_length=100,
        description=(
            "Report type slug or label, for example "
            "healthcare-facility-inspection for the current inspection program."
        ),
    )
    visn: str | None = Field(
        default=None,
        max_length=10,
        description=(
            "VISN label as OIG tagged the report. Before August 2026 these are VA's "
            "former 18 networks; from August 2026, the five new networks, so 1, 2, "
            "4, and 5 mean different regions in each. Use state to follow a region "
            "across the change."
        ),
    )
    state: str | None = Field(
        default=None,
        max_length=50,
        description="State or territory name, such as New York. Codes such as NY work.",
    )
    published_from: str | None = Field(
        default=None, pattern=_ISO_DATE, description="Earliest date, YYYY-MM-DD."
    )
    published_to: str | None = Field(
        default=None, pattern=_ISO_DATE, description="Latest date, YYYY-MM-DD."
    )
    # OIG report numbers have no single format (15-00071-158, 7AF-G10-073,
    # 2012-03740-HI-0422), so they are bounded by length, not a pattern.
    report_number: str | None = Field(
        default=None, max_length=30, description="Exact OIG report number."
    )
    station_number: str | None = Field(
        default=None,
        max_length=20,
        description=(
            "Only this facility's findings, by station number such as 528A6. Look a "
            "station number up with vaoig_get_facility_profile; never guess one."
        ),
    )
    exclude_station_number: str | None = Field(
        default=None,
        max_length=20,
        description="Leave this facility out, to see only its peers.",
    )
    node_id: int | None = Field(default=None, ge=1, description="One report's node id.")
    domain: str | None = Field(
        default=None,
        max_length=100,
        description=(
            "Inspection domain of the facility response. Usually empty on newer "
            "Healthcare Facility Inspection responses, so this misses most of them."
        ),
    )
    has_response: bool | None = Field(
        default=None,
        description="Keep only findings with, or without, a facility response.",
    )

    @field_validator("action_office")
    @classmethod
    def _office(cls, value: str | None) -> str | None:
        """Send a known office as its abbreviation, which the API matches exactly."""
        if value is None:
            return None
        return office_abbreviation(value) or value.strip()

    @field_validator("domain")
    @classmethod
    def _domain_is_not_an_office(cls, value: str | None) -> str | None:
        """An office in the domain filter matches nothing; say where it belongs."""
        if value is not None and (abbr := office_abbreviation(value)):
            raise ValueError(
                f"'{value}' is a VA office, not an inspection domain. "
                f"Use action_office='{abbr}' instead."
            )
        return value

    @field_validator("state")
    @classmethod
    def _state_name(cls, value: str | None) -> str | None:
        """The API matches full names only, so expand a postal code to one."""
        if value is None:
            return None
        return STATE_NAMES.get(value.strip().upper(), value.strip())

    def to_params(self) -> dict[str, Any]:
        """Return the API query parameters for the filters that are set."""
        return self.model_dump(mode="json", exclude_none=True)


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


# ── Tool results ─────────────────────────────────────────────────────────────
# Each tool declares one of these as its output schema, so clients see the shape
# in tools/list and MCP clients check every result against it. Fields the server
# writes are typed exactly. Records passed through from the data API allow extra
# fields and null values, so the API can add a field without breaking a client.

Notices = Annotated[
    list[str],
    Field(description="Text the server adds for the user. Pass every entry on."),
]


class _Record(BaseModel):
    """A record from the data API. Unlisted fields pass through unchanged."""

    model_config = ConfigDict(extra="allow")


class NotFound(BaseModel):
    """Nothing matched. This is an answer, not a failed call."""

    error: str = Field(description="What was not found.")
    hint: str = Field(description="What to try next.")


class Page(_Record):
    """One page of a longer list."""

    total: int | None = None
    count: int | None = None
    offset: int | None = None
    has_more: bool | None = None
    next_offset: int | None = Field(
        default=None, description="Pass as offset for the next page; null at the end."
    )
    items: list[dict[str, Any]] = Field(default_factory=list)


class DatasetStatus(BaseModel):
    """Coverage and freshness of the data."""

    data_as_of: str | None
    counts: dict[str, Any]
    reconciliation: dict[str, Any] = Field(
        description="Open counts in this data compared with OIG's dashboard."
    )
    filter_values: dict[str, list[str]] = Field(
        description="Valid values for each filter, by filter name."
    )
    notices: Notices
    provenance: Provenance


class Finding(_Record):
    """One recommendation, with the facility's response when one was extracted."""

    rec_id: str | None = None
    report_number: str | None = None
    title: str | None = None
    url: str | None = None
    citation: str | None = Field(
        default=None, description="Report number and link, ready to copy."
    )
    status: str | None = None
    text: str | None = Field(default=None, description="The recommendation, quoted.")
    response: dict[str, Any] | None = Field(
        default=None, description="Concurrence, target date, and corrective action."
    )
    matched_by: list[str] | None = Field(
        default=None, description="Which keyword and semantic searches found it."
    )


class PageHit(_Record):
    """A report PDF page matching the question."""

    node_id: int | None = None
    page_no: int | None = None
    snippet: str | None = None
    report_number: str | None = None
    url: str | None = None
    citation: str | None = Field(
        default=None, description="Report number and link, ready to copy."
    )
    pdf_url: str | None = None


class SearchResult(BaseModel):
    """A ranked shortlist of findings. Not a count."""

    search_mode: str | None = Field(
        description="hybrid, or keyword_fallback when semantic search was unavailable."
    )
    shortlist_size: int | None = Field(
        description="Length of the ranked shortlist, at most 100. Not a count."
    )
    count: int | None
    offset: int | None
    has_more: bool | None
    next_offset: int | None
    items: list[Finding]
    page_hits: list[PageHit]
    notices: Notices
    provenance: Provenance


class Report(_Record):
    """One report with its recommendations, or its listing if it has none."""

    node_id: int | None = None
    report_number: str | None = None
    title: str | None = None
    url: str | None = None
    citation: str | None = Field(
        default=None, description="Report number and link, ready to copy."
    )
    summary: str | None = None
    pdf_url: str | None = None
    recommendations: list[dict[str, Any]] | None = None
    notices: Notices
    provenance: Provenance


class FacilityMatches(BaseModel):
    """Several facilities matched. Ask the user which one is meant."""

    matches: list[dict[str, Any]]
    total_matches: int | None
    hint: str
    provenance: Provenance


class FacilityProfile(_Record):
    """One facility's reports, inspections, findings, and repeat findings."""

    station_number: str | None = None
    name: str | None = None
    reports: list[dict[str, Any]] | None = Field(
        default=None,
        description="Each report once: number, type, date, link, and citation.",
    )
    inspections: list[dict[str, Any]] | None = None
    repeat_findings: list[dict[str, Any]] | None = None
    repeat_findings_basis: str | None = Field(
        default=None, description="What a repeat finding does and does not show."
    )
    next_window_basis: str | None = Field(
        default=None, description="Why the next inspection window is an estimate."
    )
    recommendations: Page
    notices: Notices
    provenance: Provenance


class Analysis(BaseModel):
    """Counts and closure measures for a filtered set, one item per group."""

    group_by: str
    keywords: str | None = Field(description="The keywords used, echoed back.")
    filters: dict[str, Any] = Field(
        description="The filters used, echoed back, so the result names its scope."
    )
    total_groups: int | None
    recommendation_total: int | None = Field(
        description=(
            "Distinct recommendations in the set, the sum over years. Null for other "
            "groupings, whose groups overlap."
        )
    )
    peak_year: dict[str, Any] | None = Field(
        default=None,
        description=(
            "By year only: the year with the most recommendations, with its counts."
        ),
    )
    items: list[dict[str, Any]]
    notices: Notices
    target_basis: str | None = Field(
        description="Why target dates cannot measure missed deadlines."
    )
    provenance: Provenance


class Cluster(_Record):
    """Recommendations with matching wording or meaning, across reports."""

    cluster_id: int | None = None
    label: str | None = Field(default=None, description="One member's text, quoted.")
    method: str | None = None
    matching_report_count: int | None = None
    prevalence: str | None = Field(
        default=None, description="Matching reports out of the reports in scope."
    )


class ClusterList(BaseModel):
    """Clusters ordered by how many reports they span."""

    total: int | None
    count: int | None
    offset: int | None
    has_more: bool | None
    next_offset: int | None
    reports_in_scope: int | None
    items: list[Cluster]
    notices: Notices
    provenance: Provenance


class ClusterDetail(Cluster):
    """One cluster with its members."""

    status_counts: dict[str, Any] | None = None
    members: Page
    notices: Notices
    provenance: Provenance


class PeerAction(BaseModel):
    """What another facility committed to do about a similar finding."""

    report_number: str | None
    title: str | None
    url: str | None
    citation: str | None = Field(
        default=None, description="Report number and link, ready to copy."
    )
    status: str | None
    recommendation: str | None
    concur: Any = None
    target_date: str | None
    corrective_action: str
    corrective_action_truncated: bool = Field(
        description="True when shortened; vaoig_get_report has the full text."
    )
    pdf_page: int | None


class PeerFinding(BaseModel):
    """A finding common at peer facilities under the current program."""

    cluster_id: int | None
    finding: str | None
    how_common: str
    facility_in_this_group: bool
    open_count: int | None
    days_sample_size: int | None
    median_days_to_close: float | None
    q1_days: float | None
    q3_days: float | None
    peer_actions: list[PeerAction]


class NextInspection(BaseModel):
    """The estimated next inspection window. OIG publishes no schedule."""

    estimated_window: str | None
    is_estimate: bool | None
    next_window_basis: str | None
    latest_inspection: dict[str, Any]


class OwnHistory(BaseModel):
    """The facility's own record."""

    report_count: int | None
    recommendation_count: int | None
    open_count: int | None
    open_findings: list[dict[str, Any]]
    repeat_findings: list[dict[str, Any]]
    repeat_findings_basis: str | None


class InspectionBrief(BaseModel):
    """One facility's inspection preparation from the public record."""

    facility: dict[str, Any]
    next_inspection: NextInspection | None
    own_history: OwnHistory
    common_peer_findings: list[PeerFinding]
    notices: Notices
    provenance: Provenance


def output_schema(*shapes: type[BaseModel]) -> dict[str, Any]:
    """The output schema a tool declares: one result shape, or any of several.

    Declared explicitly because FastMCP would otherwise wrap a union return type
    as {"result": ...}, which changes the shape every client reads.
    """
    shape = shapes[0] if len(shapes) == 1 else Union[shapes]  # noqa: UP007
    return {"type": "object", **TypeAdapter(shape).json_schema()}
