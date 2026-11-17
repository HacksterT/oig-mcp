"""Argument completion for the prompts and the taxonomy resource.

Clients that show completions suggest values as a person types:
- `facility` in the inspection_readiness_checklist prompt, from the facility
  registry, as "Name (station)" so the prompt names one facility;
- `focus` in the open_recommendation_aging_brief prompt, from OIG's topics. The
  prompt passes focus on as search keywords, so office abbreviations, which are
  filters and not words in the text, are not offered;
- `facet` in vaoig://taxonomy/{facet}, from the fixed facet list.

Completion is a convenience: a failure or an unknown argument yields no
suggestions, never an error. Tools and their results do not depend on it.
"""

from __future__ import annotations

from fastmcp import FastMCP
from mcp_types import (
    CompletionArgument,
    CompletionContext,
    PromptReference,
    ResourceTemplateReference,
)

from oig_mcp.failures import UpstreamServiceError
from oig_mcp.resources.reference import FACETS
from oig_mcp.upstream import fetch_object

MAX_SUGGESTIONS = 10
# Longer than any facility name or topic; a longer value is not a partial name.
MAX_PARTIAL = 100
_NO_MATCH = 3
# The registry ranks its own matches; read past the first ten to find name matches.
_CANDIDATES = 25


def _rank(value: str, typed: str) -> int:
    """0 if the value starts with the typed text, 1 if one of its words does, 2 if
    it contains it anywhere, and _NO_MATCH otherwise. `typed` is casefolded."""
    folded = value.casefold()
    if folded.startswith(typed):
        return 0
    if any(word.startswith(typed) for word in folded.split()):
        return 1
    return 2 if typed in folded else _NO_MATCH


def _matching(values: list[str], partial: str) -> list[str]:
    """The values that contain the partial text, best matches first."""
    typed = partial.casefold()
    ranked = sorted(values, key=lambda value: _rank(value, typed))
    return [v for v in ranked if _rank(v, typed) < _NO_MATCH][:MAX_SUGGESTIONS]


async def _facilities(partial: str) -> list[str]:
    """Facilities the registry finds for the partial text, as "Name (station)".

    The registry's search also matches linked report titles, which is how a city
    such as West Haven finds its system, but also brings in unrelated facilities.
    So facilities whose name, alias, or station number matches come first and
    alone; the title matches are offered only when nothing else matches.
    """
    if not partial:
        return []
    page = await fetch_object("facilities", {"q": partial, "limit": _CANDIDATES})
    typed = partial.casefold()
    ranked: list[tuple[int, str]] = []
    for item in page.get("items", []):
        name, station = item.get("name"), item.get("station_number")
        if not name or not station:
            continue
        names = [name, *(item.get("aliases") or [])]
        rank = 0 if station == partial else min(_rank(str(n), typed) for n in names)
        ranked.append((rank, f"{name} ({station})"))
    named = [entry for entry in ranked if entry[0] < _NO_MATCH]
    chosen = sorted(named, key=lambda entry: entry[0]) if named else ranked
    return [label for _, label in chosen[:MAX_SUGGESTIONS]]


async def _topics(partial: str) -> list[str]:
    """OIG's report topics that contain the partial text."""
    result = await fetch_object("taxonomy/topic")
    items = result.get("items", [])
    return _matching([str(i["value"]) for i in items if i.get("value")], partial)


async def complete(
    ref: PromptReference | ResourceTemplateReference,
    argument: CompletionArgument,
    context: CompletionContext | None,
) -> list[str]:
    """Suggest values for the three arguments that have them; nothing otherwise."""
    partial = argument.value.strip()
    if len(partial) > MAX_PARTIAL:
        return []
    if isinstance(ref, PromptReference):
        target = (ref.name, argument.name)
    else:
        target = (ref.uri, argument.name)
    try:
        match target:
            case ("inspection_readiness_checklist", "facility"):
                return await _facilities(partial)
            case ("open_recommendation_aging_brief", "focus"):
                return await _topics(partial)
            case ("vaoig://taxonomy/{facet}", "facet"):
                return _matching(sorted(FACETS), partial)
    except UpstreamServiceError:
        return []
    return []


def register(mcp: FastMCP) -> None:
    """Register the completion handler, which also advertises the capability."""
    mcp.completion(complete)
