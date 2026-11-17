"""Asking the user which facility is meant, in clients that can ask.

When a facility name matches several facilities, the facility tools would
otherwise answer "several facilities match" and leave the assistant to ask, and
weaker models guess a station instead. A client that advertises form
elicitation can put the choice to the user directly:
- on protocol 2026-07-28, the tool returns an `input_required` result (SEP-2322)
  and the client calls again with the answer. Each round is a whole request, so
  this works on the stateless hosted endpoint;
- on earlier protocols, over a live session such as stdio, the tool asks with
  `ctx.elicit` and waits.

Any other client, including watsonx Orchestrate unless it advertises
elicitation, gets the "several facilities match" answer exactly as before. A
declined or cancelled choice gets it too. The answer is checked against the
facilities that matched, so a client cannot steer the tool to another station.
"""

from __future__ import annotations

from typing import Any

import anyio
from fastmcp import Context
from fastmcp.server.elicitation import (
    AcceptedElicitation,
    handle_elicit_accept,
    parse_elicit_response_type,
)
from mcp_types import (
    ElicitRequest,
    ElicitRequestFormParams,
    ElicitResult,
    InputRequiredResult,
)
from mcp_types.version import MODERN_PROTOCOL_VERSIONS

# The key of the one question this server asks, in input_requests and responses.
QUESTION = "facility"
# How long a live session may take to answer before the tool gives the matches
# instead, so a client that advertises elicitation but never answers cannot hold
# the call open. Long enough for a person to read ten names and choose.
ANSWER_SECONDS = 120


def _choices(matches: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """One titled choice per matching station: "Name (station), state"."""
    choices = {}
    for match in matches:
        if station := match.get("station_number"):
            title = f"{match.get('name')} ({station})"
            state = match.get("state")
            choices[str(station)] = {"title": f"{title}, {state}" if state else title}
    return choices


def _can_ask(ctx: Context) -> bool:
    """True if the client advertised form elicitation. An empty elicitation
    capability means form mode, as it did before modes existed."""
    try:
        capabilities = ctx.session.client_capabilities
    except RuntimeError:
        return False
    elicitation = capabilities.elicitation if capabilities else None
    return elicitation is not None and (
        elicitation.form is not None or elicitation.url is None
    )


def _is_modern(ctx: Context) -> bool:
    request = ctx.request_context
    return request is not None and request.protocol_version in MODERN_PROTOCOL_VERSIONS


def _chosen(answer: Any, matches: list[dict[str, Any]]) -> str | None:
    """The chosen station, if it is one of the facilities that matched."""
    allowed = {str(m.get("station_number")) for m in matches}
    if isinstance(answer, AcceptedElicitation) and str(answer.data) in allowed:
        return str(answer.data)
    return None


async def choose_station(
    ctx: Context | None, facility: str, matches: list[dict[str, Any]]
) -> str | InputRequiredResult | None:
    """Ask the user to pick one of several matching facilities, if the client can.

    Returns the chosen station, an InputRequiredResult for the tool to return as
    is (2026-07-28: the client asks and calls again), or None when the client
    cannot ask or the user did not choose, so the tool answers with the matches.
    """
    if ctx is None or not _can_ask(ctx):
        return None
    message = f'Several VA facilities match "{facility}". Which one do you mean?'
    choices = _choices(matches)
    config = parse_elicit_response_type(choices, response_title="Facility")
    if _is_modern(ctx):
        response = (ctx.input_responses or {}).get(QUESTION)
        if response is None:
            ask = ElicitRequest(
                params=ElicitRequestFormParams(
                    message=message, requested_schema=config.schema
                )
            )
            return InputRequiredResult(input_requests={QUESTION: ask})
        if not isinstance(response, ElicitResult) or response.action != "accept":
            return None
        try:
            return _chosen(handle_elicit_accept(config, response.content), matches)
        except (ValueError, TypeError):
            return None
    try:
        with anyio.fail_after(ANSWER_SECONDS):
            answer = await ctx.elicit(message, choices, response_title="Facility")
    except Exception:  # Advertised but failed or timed out: answer as before.
        return None
    return _chosen(answer, matches)
