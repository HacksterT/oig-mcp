"""When several facilities match, a client that can ask its user gets a choice.

Three paths from one tool: protocol 2026-07-28 returns input_required and the
client calls again; an earlier protocol asks with elicitation over the session;
any other client gets the "several facilities match" answer unchanged.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest
from fastmcp import Client
from mcp_types import ClientCapabilities, ElicitResult

from oig_mcp.app import mcp
from oig_mcp.facility_choice import _can_ask, choose_station
from tests.conftest import FakeApi

AS_OF = {"data_as_of": "2026-11-01"}
DURHAM_NAME = "Durham VA Health Care System"
DURHAM = {"station_number": "558", "name": DURHAM_NAME, "state": "NC"}
DUBLIN = {"station_number": "557", "name": "Carl Vinson VAMC", "state": "GA"}
PROFILE_TOOL = "vaoig_get_facility_profile"
PROFILE = {
    **AS_OF,
    **DURHAM,
    "reports": [],
    "inspections": [],
    "recommendations": [],
}
TOOLS = [
    ("vaoig_get_facility_profile", "name"),
    ("vaoig_get_inspection_brief", "facility"),
]


@pytest.fixture
def two_matches(api: FakeApi) -> FakeApi:
    api.routes["facilities"] = {
        **AS_OF,
        "total": 2,
        "items": [DURHAM, DUBLIN],
    }
    api.routes["facilities/558"] = PROFILE
    api.routes["clusters"] = {**AS_OF, "total": 0, "items": []}
    return api


def answering(choice: Any, asked: list[dict[str, Any]]):
    """An elicitation handler that records the question and gives `choice`."""

    async def handler(message, response_type, params, context):
        asked.append({"message": message, "schema": params.requested_schema})
        return choice

    return handler


def fetched(api: FakeApi) -> set[str]:
    """Data API paths requested, without the version prefix, e.g. "facilities/558"."""
    return {r.url.path.removeprefix("/v1/") for r in api.requests}


def chose_durham(result: dict[str, Any], key: str) -> bool:
    if key == "name":
        return result.get("station_number") == "558"
    return result["facility"]["station_number"] == "558"


@pytest.mark.parametrize("mode", ["auto", "legacy"])
@pytest.mark.parametrize(("tool", "key"), TOOLS)
async def test_the_user_chooses_and_the_tool_answers_for_that_facility(
    two_matches: FakeApi, mode: str, tool: str, key: str
) -> None:
    asked: list[dict[str, Any]] = []
    client = Client(mcp, elicitation_handler=answering("558", asked), mode=mode)
    async with client:
        expected = "2026-07-28" if mode == "auto" else "2025-11-25"
        assert client.protocol_version == expected
        result = (await client.call_tool(tool, {"facility": "Du"})).structured_content
    assert chose_durham(result, key)
    assert "facilities/558" in fetched(two_matches)
    # The model never sees the form, so the result says the user chose.
    assert result["notices"][0] == (
        f'The user chose {DURHAM_NAME} (558) from 2 facilities that match "Du", '
        "in a form the server showed them. Answer for this facility only: do not "
        "look up the others or ask again unless the user asks."
    )
    assert "_user_choice" not in json.dumps(result)
    assert len(asked) == 1
    assert 'match "Du"' in asked[0]["message"]
    choices = asked[0]["schema"]["properties"]["value"]["oneOf"]
    assert {"const": "558", "title": f"{DURHAM_NAME} (558), NC"} in choices
    assert len(choices) == 2


@pytest.mark.parametrize("mode", ["auto", "legacy"])
@pytest.mark.parametrize("tool", [tool for tool, _ in TOOLS])
@pytest.mark.parametrize(
    "answer",
    [
        ElicitResult(action="decline"),
        ElicitResult(action="cancel"),
        "999",  # not one of the facilities that matched
        ElicitResult(action="accept", content={"station": "558"}),  # wrong key
        ElicitResult(action="accept", content={"value": ["558"]}),  # wrong shape
        ElicitResult(action="accept"),  # accepted with nothing
    ],
    ids=["decline", "cancel", "other-station", "wrong-key", "wrong-shape", "empty"],
)
async def test_no_valid_choice_gives_the_matches(
    two_matches: FakeApi, mode: str, tool: str, answer: Any
) -> None:
    client = Client(mcp, elicitation_handler=answering(answer, []), mode=mode)
    async with client:
        result = await client.call_tool(tool, {"facility": "Du"})
    matches = result.structured_content["matches"]
    assert [m["station_number"] for m in matches] == ["558", "557"]
    assert not {"facilities/999", "facilities/558"} & fetched(two_matches)


def _ctx(elicitation: dict[str, Any] | None) -> Any:
    """A context carrying only the client capabilities _can_ask reads, built
    from the capability JSON a host sends at initialize."""
    declared = {} if elicitation is None else {"elicitation": elicitation}
    capabilities = ClientCapabilities.model_validate(declared)
    return SimpleNamespace(session=SimpleNamespace(client_capabilities=capabilities))


class _NoSession:
    @property
    def session(self) -> Any:
        raise RuntimeError("no active session")


@pytest.mark.parametrize(
    ("elicitation", "can_ask"),
    [
        (None, False),  # no elicitation capability
        ({}, True),  # "elicitation": {} means form, as before modes existed
        ({"form": {}}, True),  # Cursor 3.26
        ({"form": {}, "url": {}}, True),  # VS Code 1.145
        ({"url": {}}, False),  # URL only: Claude Desktop 5.11
    ],
    ids=["none", "empty", "form", "form-and-url", "url-only"],
)
def test_asking_follows_the_declared_modes(
    elicitation: dict[str, Any] | None, can_ask: bool
) -> None:
    assert _can_ask(_ctx(elicitation)) is can_ask


def test_a_context_without_a_session_cannot_ask() -> None:
    assert _can_ask(_NoSession()) is False


async def test_a_url_only_client_is_never_asked() -> None:
    # If _can_ask let it through, choose_station would read ctx.request_context,
    # which this context lacks, and the test would error.
    ctx = _ctx({"url": {}})
    assert await choose_station(ctx, "Du", [DURHAM, DUBLIN]) is None


@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_a_client_that_cannot_ask_gets_the_matches(
    two_matches: FakeApi, mode: str
) -> None:
    async with Client(mcp, mode=mode) as client:
        result = await client.call_tool(PROFILE_TOOL, {"facility": "Du"})
    step = result.structured_content["next_step"]
    assert step.startswith('2 facilities match "Du". Do not choose one')
    assert "call again with that station number" in step


async def test_one_match_asks_nothing(api: FakeApi) -> None:
    api.routes["facilities"] = {**AS_OF, "total": 1, "items": [DURHAM]}
    api.routes["facilities/558"] = PROFILE
    asked: list[dict[str, Any]] = []
    async with Client(mcp, elicitation_handler=answering("557", asked)) as client:
        result = await client.call_tool(PROFILE_TOOL, {"facility": "Du"})
    assert result.structured_content["station_number"] == "558"
    assert asked == []
    assert not any("chose" in n for n in result.structured_content["notices"])


async def test_a_session_that_never_answers_gets_the_matches(
    two_matches: FakeApi, monkeypatch
) -> None:
    import asyncio

    from oig_mcp import facility_choice

    monkeypatch.setattr(facility_choice, "ANSWER_SECONDS", 0.2)

    async def silent(message, response_type, params, context):
        await asyncio.sleep(5)

    async with Client(mcp, elicitation_handler=silent, mode="legacy") as client:
        result = await client.call_tool(PROFILE_TOOL, {"facility": "Du"})
    assert "matches" in result.structured_content
