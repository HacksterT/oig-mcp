"""Argument completion: the three arguments that have suggestions, and nothing else."""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp import Client
from mcp_types import PromptReference, ResourceTemplateReference

from oig_mcp.app import mcp
from tests.conftest import FakeApi

CHECKLIST = PromptReference(type="ref/prompt", name="inspection_readiness_checklist")
AGING = PromptReference(type="ref/prompt", name="open_recommendation_aging_brief")
TAXONOMY = ResourceTemplateReference(
    type="ref/resource", uri="vaoig://taxonomy/{facet}"
)
OTHER_TEMPLATE = ResourceTemplateReference(type="ref/resource", uri="vaoig://x/{facet}")
AS_OF = {"data_as_of": "2026-11-01"}


def facility(station: str, name: str, *aliases: str) -> dict[str, Any]:
    return {"station_number": station, "name": name, "aliases": [name, *aliases]}


async def complete(ref, name: str, value: str) -> list[str]:
    async with Client(mcp) as client:
        return (await client.complete(ref, {"name": name, "value": value})).values


async def test_server_advertises_completions() -> None:
    async with Client(mcp) as client:
        assert client.server_capabilities.completions is not None


async def test_facility_name_and_alias_matches_come_first_and_alone(
    api: FakeApi,
) -> None:
    api.routes["facilities"] = {
        **AS_OF,
        "items": [
            # The registry also matches report titles: "procedures" holds "dur".
            facility("358", "VA Manila Outpatient Clinic"),
            facility("668", "Mann-Grandstaff VA Medical Center", "Spokane Durango"),
            facility("558", "Durham VA Health Care System", "Durham VAMC"),
        ],
    }
    assert await complete(CHECKLIST, "facility", "dur") == [
        "Durham VA Health Care System (558)",
        "Mann-Grandstaff VA Medical Center (668)",
    ]
    assert api.last.url.params["q"] == "dur"
    assert api.last.url.path == "/v1/facilities"


async def test_facility_falls_back_to_the_registry_matches(api: FakeApi) -> None:
    """A city is often only in a linked report's title, as West Haven is."""
    api.routes["facilities"] = {
        **AS_OF,
        "items": [facility("689", "VA Connecticut Healthcare System")],
    }
    assert await complete(CHECKLIST, "facility", "west haven") == [
        "VA Connecticut Healthcare System (689)"
    ]


async def test_facility_matches_an_exact_station_number(api: FakeApi) -> None:
    api.routes["facilities"] = {
        **AS_OF,
        "items": [facility("558", "Durham VA Health Care System")],
    }
    assert await complete(CHECKLIST, "facility", "558") == [
        "Durham VA Health Care System (558)"
    ]


async def test_focus_suggests_topics_only(api: FakeApi) -> None:
    api.routes["taxonomy/topic"] = {
        **AS_OF,
        "items": [
            {"value": "Patient Safety"},
            {"value": "Suicide Prevention"},
            {"value": "Supplies and Equipment"},
        ],
    }
    assert await complete(AGING, "focus", "su") == [
        "Suicide Prevention",
        "Supplies and Equipment",
    ]
    assert await complete(AGING, "focus", "safe") == ["Patient Safety"]


async def test_facet_suggestions_need_no_upstream(api: FakeApi) -> None:
    assert await complete(TAXONOMY, "facet", "a") == [
        "action_office",
        "author_office",
        "special_project",
        "state",
    ]
    assert api.requests == []


@pytest.mark.parametrize(
    ("ref", "name"),
    [
        (CHECKLIST, "other"),
        (PromptReference(type="ref/prompt", name="unknown"), "facility"),
        (OTHER_TEMPLATE, "facet"),
    ],
)
async def test_other_arguments_get_nothing(api: FakeApi, ref, name: str) -> None:
    assert await complete(ref, name, "d") == []
    assert api.requests == []


@pytest.mark.parametrize("value", ["", "   ", "x" * 101])
async def test_empty_or_oversized_partial_reaches_no_upstream(
    api: FakeApi, value: str
) -> None:
    assert await complete(CHECKLIST, "facility", value) == []
    assert api.requests == []


async def test_hostile_partial_is_only_a_query_value(api: FakeApi) -> None:
    api.routes["facilities"] = {**AS_OF, "items": []}
    hostile = "../../meta?x=1#y"
    assert await complete(CHECKLIST, "facility", hostile) == []
    assert api.last.url.path == "/v1/facilities"
    assert api.last.url.params["q"] == hostile


@pytest.mark.parametrize("status", [500, 503, 429])
async def test_upstream_failure_gives_no_suggestions(api: FakeApi, status: int) -> None:
    api.routes["facilities"] = status
    api.routes["taxonomy/topic"] = status
    assert await complete(CHECKLIST, "facility", "dur") == []
    assert await complete(AGING, "focus", "su") == []
