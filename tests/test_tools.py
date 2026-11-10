"""Tool behavior, driven through an MCP client and the real HTTP client.

Only the network is faked, so these cover schema validation, query encoding, and
the API-to-tool mapping.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from oig_mcp import utils
from oig_mcp.app import mcp

AS_OF = {"data_as_of": "2026-11-01"}
ENVELOPE = {"total": 0, "count": 0, "offset": 0, "has_more": False, "next_offset": None}
REPEAT_BASIS = (
    "A repeat means the same issue was cited again, not that nothing was done."
)
WINDOW_BASIS = (
    "Estimated as the inspection end plus three years. OIG publishes no schedule."
)


class FakeApi:
    """Answers GET requests from a route table and records what was asked."""

    def __init__(self) -> None:
        self.routes: dict[str, Any] = {}
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        route = self.routes.get(request.url.path.removeprefix("/v1/"))
        if route is None:
            return httpx.Response(404, json={"detail": "not found"})
        if isinstance(route, int):
            return httpx.Response(route, json={"detail": "upstream detail"})
        return httpx.Response(200, json=route)

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]


@pytest.fixture
def api(monkeypatch) -> FakeApi:
    fake = FakeApi()
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        utils.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(
            transport=httpx.MockTransport(lambda r: fake.handle(r)), **kwargs
        ),
    )
    return fake


async def call(name: str, **arguments: Any) -> dict[str, Any]:
    async with Client(mcp) as client:
        return (await client.call_tool(name, arguments)).structured_content


async def call_failing(name: str, **arguments: Any) -> dict[str, Any]:
    """Call a tool expected to fail, and return its structured error body."""
    async with Client(mcp) as client:
        result = await client.call_tool(name, arguments, raise_on_error=False)
    assert result.is_error, f"{name} should report isError"
    return result.structured_content


async def test_tool_surface_is_exactly_the_agreed_list() -> None:
    """Guards the design rule: new facts become fields, not tools."""
    names = {tool.name for tool in await mcp.list_tools()}
    assert names == {
        "vaoig_get_dataset_status",
        "vaoig_search_findings",
        "vaoig_get_report",
        "vaoig_get_facility_profile",
        "vaoig_analyze_recommendations",
        "vaoig_find_systemic_clusters",
        "vaoig_get_inspection_brief",
    }


# ── Search ───────────────────────────────────────────────────────────────────


def _search_response(mode: str = "hybrid") -> dict[str, Any]:
    return {
        **AS_OF,
        **ENVELOPE,
        "total": 100,
        "count": 1,
        "has_more": True,
        "next_offset": 1,
        "search_mode": mode,
        "items": [{"rec_id": "1-1", "url": "https://www.vaoig.gov/reports/a"}],
        "page_hits": [{"page_no": 3, "url": "https://www.vaoig.gov/reports/b"}],
    }


async def test_search_has_no_mode_parameter() -> None:
    async with Client(mcp) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
    properties = tools["vaoig_search_findings"].input_schema["properties"]
    assert not {"mode", "q_mode", "search_mode", "strategy"} & set(properties)


async def test_search_never_presents_its_total_as_a_count(api: FakeApi) -> None:
    api.routes["search"] = _search_response()
    result = await call("vaoig_search_findings", question="medication carts")
    assert "total" not in result
    assert result["shortlist_size"] == 100
    assert "not a count" in " ".join(result["notices"])


async def test_search_sends_filters_and_repeats_status(api: FakeApi) -> None:
    api.routes["search"] = _search_response()
    await call(
        "vaoig_search_findings",
        question="infusion pumps",
        filters={
            "status": ["open", "closed-implemented"],
            "exclude_station_number": "528A6",
        },
    )
    params = api.last.url.params
    assert params["q"] == "infusion pumps"
    assert params.get_list("status") == ["open", "closed-implemented"]
    assert params["exclude_station_number"] == "528A6"
    assert "report_type" not in params  # unset filters are not sent as empty
    assert "q_mode" not in params


async def test_search_reports_keyword_fallback(api: FakeApi) -> None:
    api.routes["search"] = _search_response(mode="keyword_fallback")
    result = await call("vaoig_search_findings", question="biopsy tracking")
    assert result["search_mode"] == "keyword_fallback"
    assert "keyword search only" in result["notices"][0]


async def test_hybrid_search_has_no_fallback_notice(api: FakeApi) -> None:
    api.routes["search"] = _search_response()
    result = await call("vaoig_search_findings", question="biopsy tracking")
    assert "keyword search only" not in " ".join(result["notices"])


async def test_search_cites_items_and_page_hits(api: FakeApi) -> None:
    api.routes["search"] = _search_response()
    result = await call("vaoig_search_findings", question="biopsy tracking")
    assert result["provenance"]["source_urls"] == [
        "https://www.vaoig.gov/reports/a",
        "https://www.vaoig.gov/reports/b",
    ]
    assert result["provenance"]["data_as_of"] == "2026-11-01"


async def test_unknown_filter_is_rejected_not_ignored(api: FakeApi) -> None:
    with pytest.raises(ToolError):
        await call(
            "vaoig_search_findings", question="carts", filters={"past_target": True}
        )
    assert api.requests == []


async def test_upstream_failure_returns_sanitized_error(api: FakeApi) -> None:
    api.routes["search"] = 500
    result = await call_failing("vaoig_search_findings", question="carts")
    assert result["error"] == "Upstream service returned status 500."
    assert "upstream detail" not in str(result)


# Each tool with the arguments and the first API path it calls.
_FIRST_CALLS = [
    ("vaoig_get_dataset_status", {}, "meta"),
    ("vaoig_search_findings", {"question": "carts"}, "search"),
    ("vaoig_get_report", {"node_id": 1}, "reports/1"),
    ("vaoig_get_facility_profile", {"facility": "Tampa"}, "facilities"),
    ("vaoig_analyze_recommendations", {"group_by": "year"}, "metrics/counts"),
    ("vaoig_find_systemic_clusters", {}, "clusters"),
    ("vaoig_get_inspection_brief", {"facility": "Tampa"}, "facilities"),
]


@pytest.mark.parametrize(
    ("tool", "arguments", "path"), _FIRST_CALLS, ids=[c[0] for c in _FIRST_CALLS]
)
async def test_every_tool_reports_an_unreachable_api_as_an_error(
    api: FakeApi, tool: str, arguments: dict[str, Any], path: str
) -> None:
    """A dead data API must reach the client as isError, with a hint to act on."""
    api.routes[path] = 502
    result = await call_failing(tool, **arguments)
    assert result == {
        "error": "Upstream service returned status 502.",
        "hint": utils.UNREACHABLE_HINT,
    }


async def test_rejected_filter_does_not_claim_the_api_is_down(api: FakeApi) -> None:
    api.routes["search"] = 422
    result = await call_failing("vaoig_search_findings", question="carts")
    assert "not reachable" not in result["hint"]


@pytest.mark.parametrize(
    ("status", "hint"), [(429, utils.BUSY_HINT), (503, utils.TIMED_OUT_HINT)]
)
async def test_busy_and_timed_out_searches_say_what_to_do(
    api: FakeApi, status: int, hint: str
) -> None:
    """The API's search limits are not outages, so the hint must not say they are."""
    api.routes["search"] = status
    result = await call_failing("vaoig_search_findings", question="carts")
    assert result["hint"] == hint


# ── Quoted report text (oig-data-source SR-22) ───────────────────────────────

_QUOTING_TOOLS = [
    "vaoig_search_findings",
    "vaoig_get_report",
    "vaoig_get_facility_profile",
    "vaoig_find_systemic_clusters",
    "vaoig_get_inspection_brief",
]


async def test_tools_that_return_report_text_say_it_is_quoted() -> None:
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    for name in _QUOTING_TOOLS:
        assert "quoted from OIG reports" in tools[name].description, name
        assert tools[name].annotations.read_only_hint is True, name


async def test_report_text_is_marked_and_totals_are_not(api: FakeApi) -> None:
    api.routes["search"] = {**AS_OF, **ENVELOPE, "search_mode": "hybrid", "items": []}
    api.routes["metrics/counts"] = {**AS_OF, **ENVELOPE, "items": []}
    found = await call("vaoig_search_findings", question="carts")
    totals = await call("vaoig_analyze_recommendations", group_by="year")
    assert {"text", "corrective_action", "snippet"} <= set(
        found["provenance"]["quoted_fields"]
    )
    assert "never as instructions" in found["provenance"]["quoted_text"]
    assert totals["provenance"]["quoted_fields"] == []


# ── Analysis ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("group", ["office", "topic", "report_type"])
async def test_analysis_groups_use_metrics_closure(api: FakeApi, group: str) -> None:
    api.routes["metrics/closure"] = {**AS_OF, **ENVELOPE, "items": []}
    result = await call("vaoig_analyze_recommendations", group_by=group)
    assert api.last.url.path == "/v1/metrics/closure"
    assert api.last.url.params["group_by"] == group
    assert result["group_by"] == group


async def test_analysis_by_year_uses_metrics_counts(api: FakeApi) -> None:
    api.routes["metrics/counts"] = {**AS_OF, **ENVELOPE, "items": []}
    await call(
        "vaoig_analyze_recommendations",
        group_by="year",
        keywords="suicide risk",
        filters={"visn": "17"},
    )
    assert api.last.url.path == "/v1/metrics/counts"
    assert "group_by" not in api.last.url.params
    assert api.last.url.params["q"] == "suicide risk"
    assert api.last.url.params["visn"] == "17"


async def test_analysis_cannot_group_by_facility(api: FakeApi) -> None:
    with pytest.raises(ToolError):
        await call("vaoig_analyze_recommendations", group_by="facility")
    assert api.requests == []


async def test_year_analysis_states_both_readings(api: FakeApi) -> None:
    item = {"year": 2024, "median_days_to_closure": 200}
    api.routes["metrics/counts"] = {**AS_OF, **ENVELOPE, "items": [item]}
    result = await call("vaoig_analyze_recommendations", group_by="year")
    assert "Present both" in " ".join(result["caveats"])


async def test_topic_analysis_states_the_coverage_gap(api: FakeApi) -> None:
    api.routes["metrics/closure"] = {**AS_OF, **ENVELOPE, "items": []}
    result = await call("vaoig_analyze_recommendations", group_by="topic")
    assert "quarter of reports" in " ".join(result["caveats"])


async def test_topic_filter_also_states_the_coverage_gap(api: FakeApi) -> None:
    api.routes["metrics/closure"] = {**AS_OF, **ENVELOPE, "items": []}
    result = await call(
        "vaoig_analyze_recommendations",
        group_by="office",
        filters={"topic": "Pharmacy"},
    )
    assert "quarter of reports" in " ".join(result["caveats"])


async def test_missing_closure_dates_are_stated_not_hidden(api: FakeApi) -> None:
    item = {"group": "VHA", "closed_count": 13000, "days_sample_size": 0}
    api.routes["metrics/closure"] = {
        **AS_OF,
        **ENVELOPE,
        "items": [{**item, "median_days": None}],
    }
    result = await call("vaoig_analyze_recommendations", group_by="office")
    caveats = " ".join(result["caveats"])
    assert "time to close cannot be stated" in caveats
    assert "6 percent" not in caveats  # that figure would understate this gap


async def test_partial_closure_dates_point_to_sample_size(api: FakeApi) -> None:
    item = {
        "group": "VHA",
        "closed_count": 100,
        "days_sample_size": 94,
        "median_days": 9,
    }
    api.routes["metrics/closure"] = {**AS_OF, **ENVELOPE, "items": [item]}
    result = await call("vaoig_analyze_recommendations", group_by="office")
    assert "days_sample_size" in " ".join(result["caveats"])


async def test_target_date_counts_stay_out_of_the_analysis(api: FakeApi) -> None:
    item = {
        "group": "VHA",
        "closed_count": 10,
        "days_sample_size": 10,
        "median_days": 9,
        "with_target_date": 8,
        "closed_by_target": 4,
        "closed_after_target": 3,
        "open_past_target": 1,
        "median_days_after_target": 20,
    }
    api.routes["metrics/closure"] = {**AS_OF, **ENVELOPE, "items": [item]}
    result = await call("vaoig_analyze_recommendations", group_by="office")
    assert result["items"] == [
        {
            "group": "VHA",
            "closed_count": 10,
            "days_sample_size": 10,
            "median_days": 9,
        }
    ]


async def test_target_basis_is_passed_through_verbatim(api: FakeApi) -> None:
    api.routes["metrics/closure"] = {
        **AS_OF,
        **ENVELOPE,
        "target_basis": "A target is the facility's estimate.",
        "items": [],
    }
    result = await call("vaoig_analyze_recommendations", group_by="office")
    assert result["target_basis"] == "A target is the facility's estimate."


async def test_publication_day_closures_are_explained(api: FakeApi) -> None:
    item = {"group": "VHA", "median_days": 0, "closed_on_publication_day": 9}
    api.routes["metrics/closure"] = {**AS_OF, **ENVELOPE, "items": [item]}
    result = await call("vaoig_analyze_recommendations", group_by="office")
    assert "closed the day the report came out" in " ".join(result["caveats"])


# ── Facility profile ─────────────────────────────────────────────────────────


def _facility(station: str = "528A6") -> dict[str, Any]:
    return {"station_number": station, "name": f"Facility {station}"}


def _profile() -> dict[str, Any]:
    return {
        **AS_OF,
        **_facility(),
        "reports": [{"report_number": "1", "url": "https://www.vaoig.gov/reports/a"}],
        "inspections": [{"next_window_estimate": "2027-01-01"}],
        "next_window_basis": WINDOW_BASIS,
        "repeat_findings": [{"cluster_id": 7, "report_count": 2}],
        "repeat_findings_basis": REPEAT_BASIS,
        "recommendations": [
            {"rec_id": "1-1", "status": "closed-implemented"},
            {"rec_id": "1-2", "status": "open"},
        ],
    }


def _lookup(*facilities: dict[str, Any]) -> dict[str, Any]:
    return {**AS_OF, **ENVELOPE, "total": len(facilities), "items": list(facilities)}


async def test_profile_passes_basis_text_verbatim(api: FakeApi) -> None:
    api.routes["facilities"] = _lookup(_facility())
    api.routes["facilities/528A6"] = _profile()
    result = await call("vaoig_get_facility_profile", facility="West Haven")
    assert result["repeat_findings_basis"] == REPEAT_BASIS
    assert result["next_window_basis"] == WINDOW_BASIS
    assert result["repeat_findings"] == [{"cluster_id": 7, "report_count": 2}]


async def test_profile_asks_for_more_than_the_api_default(api: FakeApi) -> None:
    api.routes["facilities"] = _lookup(_facility())
    api.routes["facilities/528A6"] = {**_profile(), "recommendations_has_more": True}
    result = await call("vaoig_get_facility_profile", facility="West Haven")
    assert api.last.url.params["recommendations_limit"] == "100"
    assert result["recommendations"]["has_older_beyond_100"] is True
    assert "recommendations_has_more" not in result


async def test_profile_page_flags_do_not_conflict(api: FakeApi) -> None:
    api.routes["facilities"] = _lookup(_facility())
    api.routes["facilities/528A6"] = {**_profile(), "recommendations_has_more": False}
    result = await call("vaoig_get_facility_profile", facility="West Haven", limit=1)
    assert result["recommendations"]["has_more"] is True
    assert result["recommendations"]["has_older_beyond_100"] is False
    assert "recommendations_has_more" not in result


async def test_profile_shortens_corrective_actions(api: FakeApi) -> None:
    profile = _profile()
    profile["recommendations"][1]["corrective_action"] = "x" * 2000
    api.routes["facilities"] = _lookup(_facility())
    api.routes["facilities/528A6"] = profile
    result = await call("vaoig_get_facility_profile", facility="West Haven")
    finding = result["recommendations"]["items"][0]
    assert len(finding["corrective_action"]) == 300
    assert finding["corrective_action_truncated"] is True


async def test_profile_explains_a_missing_response(api: FakeApi) -> None:
    api.routes["facilities"] = _lookup(_facility())
    api.routes["facilities/528A6"] = _profile()
    result = await call("vaoig_get_facility_profile", facility="West Haven")
    assert "does not show" in " ".join(result["notices"])


async def test_profile_omits_the_notice_when_every_response_exists(
    api: FakeApi,
) -> None:
    profile = _profile()
    for record in profile["recommendations"]:
        record["corrective_action"] = "Trained staff."
    api.routes["facilities"] = _lookup(_facility())
    api.routes["facilities/528A6"] = profile
    result = await call("vaoig_get_facility_profile", facility="West Haven")
    assert result["notices"] == []


async def test_search_shortens_only_long_corrective_actions(api: FakeApi) -> None:
    api.routes["search"] = {
        **AS_OF,
        **ENVELOPE,
        "search_mode": "hybrid",
        "items": [
            {"response": {"corrective_action": "x" * 2000}},
            {"response": {"corrective_action": "short"}},
            {"response": None},
        ],
    }
    result = await call("vaoig_search_findings", question="carts")
    first, second, third = result["items"]
    assert len(first["response"]["corrective_action"]) == 800
    assert first["response"]["corrective_action_truncated"] is True
    assert second["response"] == {"corrective_action": "short"}
    assert third["response"] is None


async def test_findings_and_totals_carry_different_citation_rules(
    api: FakeApi,
) -> None:
    api.routes["search"] = {**AS_OF, **ENVELOPE, "search_mode": "hybrid", "items": []}
    api.routes["metrics/counts"] = {**AS_OF, **ENVELOPE, "items": []}
    found = await call("vaoig_search_findings", question="carts")
    totals = await call("vaoig_analyze_recommendations", group_by="year")
    assert "report number and link" in found["provenance"]["citation"]
    assert "no single report" in totals["provenance"]["citation"]


async def test_year_median_of_zero_is_explained(api: FakeApi) -> None:
    api.routes["metrics/counts"] = {
        **AS_OF,
        **ENVELOPE,
        "items": [{"year": 2026, "median_days_to_closure": 0}],
    }
    result = await call("vaoig_analyze_recommendations", group_by="year")
    assert "not a typical time to close" in " ".join(result["caveats"])


async def test_status_explains_oig_open_total(api: FakeApi) -> None:
    api.routes["meta"] = {
        **AS_OF,
        "reconciliation": {
            "open": {"database": 567, "oig": 586},
            "open_set": {"oig_blank_rows": 19},
        },
    }
    result = await call("vaoig_get_dataset_status")
    assert "19 blank rows" in result["reconciliation"]["note"]


async def test_past_estimate_is_not_called_overdue(api: FakeApi) -> None:
    profile = _profile()
    profile["inspections"] = [{"is_latest": True, "next_window_estimate": "2025-04-15"}]
    api.routes["facilities"] = _lookup(_facility())
    api.routes["facilities/528A6"] = profile
    result = await call("vaoig_get_facility_profile", facility="West Haven")
    assert "does not show that the facility is overdue" in " ".join(result["notices"])


async def test_future_estimate_has_no_past_window_notice(api: FakeApi) -> None:
    profile = _profile()
    profile["inspections"] = [{"is_latest": True, "next_window_estimate": "2029-10-08"}]
    api.routes["facilities"] = _lookup(_facility())
    api.routes["facilities/528A6"] = profile
    result = await call("vaoig_get_facility_profile", facility="West Haven")
    assert "already past" not in " ".join(result["notices"])


async def test_profile_lists_open_findings_first(api: FakeApi) -> None:
    api.routes["facilities"] = _lookup(_facility())
    api.routes["facilities/528A6"] = _profile()
    result = await call("vaoig_get_facility_profile", facility="West Haven", limit=1)
    page = result["recommendations"]
    assert [r["rec_id"] for r in page["items"]] == ["1-2"]
    assert page["total"] == 2
    assert page["has_more"] is True


async def test_profile_asks_when_several_facilities_match(api: FakeApi) -> None:
    api.routes["facilities"] = _lookup(_facility("528A6"), _facility("528A7"))
    result = await call("vaoig_get_facility_profile", facility="New York")
    assert [m["station_number"] for m in result["matches"]] == ["528A6", "528A7"]
    assert api.last.url.path == "/v1/facilities"


async def test_profile_prefers_an_exact_station_match(api: FakeApi) -> None:
    api.routes["facilities"] = _lookup(_facility("528A6"), _facility("528A7"))
    api.routes["facilities/528A7"] = _profile()
    await call("vaoig_get_facility_profile", facility="528a7")
    assert api.last.url.path == "/v1/facilities/528A7"


async def test_profile_with_no_match_points_at_the_registry(api: FakeApi) -> None:
    api.routes["facilities"] = _lookup()
    result = await call("vaoig_get_facility_profile", facility="Nowhere")
    assert "No facility matched" in result["error"]
    assert "counts.facilities" in result["hint"]


# ── Clusters ─────────────────────────────────────────────────────────────────


async def test_clusters_state_prevalence_against_reports_in_scope(api: FakeApi) -> None:
    item = {"cluster_id": 7, "matching_report_count": 40, "median_days": 120}
    api.routes["clusters"] = {
        **AS_OF,
        **ENVELOPE,
        "reports_in_scope": 200,
        "items": [item],
    }
    result = await call(
        "vaoig_find_systemic_clusters", report_type="healthcare-facility-inspection"
    )
    assert result["items"][0]["prevalence"] == "40 of 200 reports in scope"
    assert result["items"][0]["median_days"] == 120
    assert "does not prove a common cause" in result["caveat"]
    assert api.last.url.params["report_type"] == "healthcare-facility-inspection"
    assert "min_reports" not in api.last.url.params


async def test_cluster_detail_paginates_members(api: FakeApi) -> None:
    api.routes["clusters/7"] = {
        **AS_OF,
        "cluster_id": 7,
        "status_counts": {"open": 1},
        "members": [
            {"rec_id": "1-1", "url": "https://www.vaoig.gov/reports/a"},
            {"rec_id": "2-1", "url": "https://www.vaoig.gov/reports/b"},
        ],
    }
    result = await call("vaoig_find_systemic_clusters", cluster_id=7, limit=1)
    assert result["status_counts"] == {"open": 1}
    assert result["members"]["total"] == 2
    assert len(result["members"]["items"]) == 1
    assert "does not prove a common cause" in result["caveat"]


async def test_unknown_cluster_is_reported_as_not_found(api: FakeApi) -> None:
    result = await call("vaoig_find_systemic_clusters", cluster_id=99)
    assert result["error"] == "No cluster has the id 99."


# ── Inspection brief ─────────────────────────────────────────────────────────


def _brief_api(api: FakeApi) -> None:
    api.routes["facilities"] = _lookup(_facility())
    profile = _profile()
    profile["inspections"] = [
        {
            "is_latest": True,
            "program": "HFI",
            "next_window_estimate": "2028-01-16",
            "next_window_is_estimate": True,
            "report_number": "1",
        }
    ]
    profile["recommendations"][1]["cluster_id"] = 7
    api.routes["facilities/528A6"] = profile
    api.routes["clusters"] = {
        **AS_OF,
        **ENVELOPE,
        "reports_in_scope": 112,
        "items": [
            {
                "cluster_id": 7,
                "label": "Develop test result workflows",
                "matching_report_count": 21,
                "median_days": 120,
            },
            {"cluster_id": 8, "label": "Keep areas clean", "matching_report_count": 9},
        ],
    }
    api.routes["search"] = {
        **_search_response(),
        "items": [
            {
                "report_number": "2",
                "text": "Peer finding",
                "url": "https://www.vaoig.gov/reports/peer",
                "response": {
                    "corrective_action": "Peer plan",
                    "target_date": "2027-01",
                },
            }
        ],
    }


async def test_brief_combines_the_facility_and_its_peers(api: FakeApi) -> None:
    _brief_api(api)
    result = await call("vaoig_get_inspection_brief", facility="West Haven")
    assert result["facility"]["station_number"] == "528A6"
    assert [r["rec_id"] for r in result["own_history"]["open_findings"]] == ["1-2"]
    first = result["common_peer_findings"][0]
    assert first["how_common"] == "21 of 112 reports in scope"
    assert first["median_days_to_close"] == 120
    assert first["peer_actions"][0]["corrective_action"] == "Peer plan"


async def test_brief_marks_groups_this_facility_is_in(api: FakeApi) -> None:
    _brief_api(api)
    result = await call("vaoig_get_inspection_brief", facility="West Haven")
    assert [f["facility_in_this_group"] for f in result["common_peer_findings"]] == [
        True,
        False,
    ]


async def test_brief_passes_basis_text_and_labels_the_estimate(api: FakeApi) -> None:
    _brief_api(api)
    result = await call("vaoig_get_inspection_brief", facility="West Haven")
    assert result["next_inspection"]["basis"] == WINDOW_BASIS
    assert result["next_inspection"]["is_estimate"] is True
    assert result["own_history"]["repeat_findings_basis"] == REPEAT_BASIS


async def test_brief_searches_only_peers_in_the_current_program(api: FakeApi) -> None:
    _brief_api(api)
    await call("vaoig_get_inspection_brief", facility="West Haven")
    searches = [r for r in api.requests if r.url.path == "/v1/search"]
    assert len(searches) == 2
    for request in searches:
        assert request.url.params["exclude_station_number"] == "528A6"
        assert request.url.params["report_type"] == "healthcare-facility-inspection"
        assert request.url.params["has_response"] == "true"


async def test_brief_clips_long_peer_actions(api: FakeApi) -> None:
    _brief_api(api)
    response = {"corrective_action": "x" * 2000}
    api.routes["search"]["items"][0]["response"] = response
    result = await call("vaoig_get_inspection_brief", facility="West Haven")
    action = result["common_peer_findings"][0]["peer_actions"][0]
    assert len(action["corrective_action"]) == 800
    assert action["corrective_action_truncated"] is True


async def test_brief_explains_what_group_membership_means(api: FakeApi) -> None:
    _brief_api(api)
    result = await call("vaoig_get_inspection_brief", facility="West Haven")
    assert "never cited" in " ".join(result["notices"])


async def test_brief_does_not_rank_by_severity(api: FakeApi) -> None:
    _brief_api(api)
    result = await call("vaoig_get_inspection_brief", facility="West Haven")
    assert "not by severity" in " ".join(result["notices"])


async def test_brief_survives_a_failed_peer_search(api: FakeApi) -> None:
    _brief_api(api)
    api.routes["search"] = 500
    result = await call("vaoig_get_inspection_brief", facility="West Haven")
    assert result["common_peer_findings"][0]["peer_actions"] == []
    assert "incomplete" in result["notices"][0]


async def test_brief_reports_keyword_fallback(api: FakeApi) -> None:
    _brief_api(api)
    api.routes["search"]["search_mode"] = "keyword_fallback"
    result = await call("vaoig_get_inspection_brief", facility="West Haven")
    assert "keyword search only" in result["notices"][0]


async def test_brief_asks_when_several_facilities_match(api: FakeApi) -> None:
    api.routes["facilities"] = _lookup(_facility("528A6"), _facility("528A7"))
    result = await call("vaoig_get_inspection_brief", facility="New York")
    assert len(result["matches"]) == 2
    assert not [r for r in api.requests if r.url.path == "/v1/clusters"]


async def test_brief_without_an_inspection_says_so(api: FakeApi) -> None:
    _brief_api(api)
    api.routes["facilities/528A6"]["inspections"] = []
    result = await call("vaoig_get_inspection_brief", facility="West Haven")
    assert result["next_inspection"] is None


# ── Filter values, resources, and prompts ───────────────────────────────────


async def test_status_lists_filter_values_for_tool_only_clients(api: FakeApi) -> None:
    api.routes["meta"] = {**AS_OF, "counts": {}}
    api.routes["taxonomy/report_type"] = {
        "items": [{"value": "audit", "label": "Audit", "report_count": 3}]
    }
    api.routes["taxonomy/action_office"] = {
        "items": [{"value": "Veterans Health Administration", "abbreviation": "VHA"}]
    }
    async with Client(mcp) as client:
        result = await client.call_tool("vaoig_get_dataset_status", {})
    values = result.structured_content["filter_values"]
    assert values["report_type"] == ["audit"]
    assert values["action_office"] == ["VHA"]
    assert "topic" not in values  # a facet that cannot be read is left out


async def test_taxonomy_resource_reads_a_facet(api: FakeApi) -> None:
    api.routes["taxonomy/topic"] = {"facet": "topic", "items": [{"value": "Safety"}]}
    async with Client(mcp) as client:
        contents = await client.read_resource("vaoig://taxonomy/topic")
    assert json.loads(contents[0].text)["items"] == [{"value": "Safety"}]


async def test_taxonomy_resource_reports_an_unknown_facet(api: FakeApi) -> None:
    async with Client(mcp) as client:
        contents = await client.read_resource("vaoig://taxonomy/nope")
    assert "Unknown facet" in json.loads(contents[0].text)["error"]


async def test_facilities_resource_reads_every_page(api: FakeApi) -> None:
    pages = [
        {**AS_OF, "items": [_facility("1")], "has_more": True, "next_offset": 1},
        {**AS_OF, "items": [_facility("2")], "has_more": False, "next_offset": None},
    ]

    def facilities(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=pages[int(request.url.params["offset"])])

    api.handle = facilities  # type: ignore[method-assign]
    async with Client(mcp) as client:
        contents = await client.read_resource("vaoig://facilities")
    body = json.loads(contents[0].text)
    assert body["total"] == 2
    assert [f["station_number"] for f in body["items"]] == ["1", "2"]


async def test_prompts_arrange_existing_tools() -> None:
    tool_names = {tool.name for tool in await mcp.list_tools()}
    async with Client(mcp) as client:
        names = {prompt.name for prompt in await client.list_prompts()}
        brief = await client.get_prompt(
            "inspection_readiness_checklist", {"facility": "El Paso"}
        )
        aging = await client.get_prompt(
            "open_recommendation_aging_brief", {"focus": "test results"}
        )
    assert names == {
        "inspection_readiness_checklist",
        "open_recommendation_aging_brief",
    }
    for result in (brief, aging):
        text = result.messages[0].content.text
        assert set(re.findall(r"vaoig_\w+", text)) <= tool_names
    assert "El Paso" in brief.messages[0].content.text
    assert "test results" in aging.messages[0].content.text


# ── Report ───────────────────────────────────────────────────────────────────


async def test_report_by_number_resolves_to_detail(api: FakeApi) -> None:
    api.routes["reports"] = {**AS_OF, **ENVELOPE, "items": [{"node_id": 4569}]}
    api.routes["reports/4569"] = {
        **AS_OF,
        "node_id": 4569,
        "url": "https://www.vaoig.gov/reports/a",
        "recommendations": [{"rec_id": "4569-1"}],
    }
    result = await call("vaoig_get_report", report_number="15-00071-158")
    assert result["recommendations"] == [{"rec_id": "4569-1"}]
    assert result["provenance"]["source_urls"] == ["https://www.vaoig.gov/reports/a"]


async def test_report_without_node_id_returns_its_listing(api: FakeApi) -> None:
    listing = {"node_id": None, "report_number": "9", "url": "https://x.gov/r"}
    api.routes["reports"] = {**AS_OF, **ENVELOPE, "items": [listing]}
    result = await call("vaoig_get_report", report_number="9")
    assert result["report_number"] == "9"
    assert "no recommendations" in result["note"]


@pytest.mark.parametrize(
    "arguments", [{}, {"report_number": "1", "node_id": 1}], ids=["none", "both"]
)
async def test_report_requires_exactly_one_identifier(
    api: FakeApi, arguments: dict[str, Any]
) -> None:
    result = await call_failing("vaoig_get_report", **arguments)
    assert "exactly one" in result["error"]
    assert api.requests == []


async def test_unknown_report_is_reported_as_not_found(api: FakeApi) -> None:
    """Not found is an answer, not a failure, so it is not marked isError."""
    result = await call("vaoig_get_report", node_id=1)
    assert result["error"] == "No report has the node id 1."
