"""Shaping tool results: provenance, paging, and size.

Pure functions over data already fetched: the provenance block every result
carries, the standard pagination envelope, clipping long narratives, and
collecting report links. No I/O here; fetching is upstream.py, and fixed texts
are guidance.py.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from oig_mcp.config import settings
from oig_mcp.guidance import CITE_FINDINGS, QUOTED_FIELDS, QUOTED_TEXT
from oig_mcp.models import Provenance


def shorten_responses(
    records: list[dict[str, Any]], max_chars: int
) -> list[dict[str, Any]]:
    """Clip long corrective actions, marking any record that was clipped.

    These narratives are the largest part of a result, and a long list of them can
    crowd out a model's context. vaoig_get_report returns the full text.
    """
    shortened = []
    for record in records:
        # Search nests the facility response. Facility profiles keep it flat.
        nested = isinstance(record.get("response"), dict)
        holder = record["response"] if nested else record
        action = holder.get("corrective_action") or ""
        if len(action) > max_chars:
            holder = {
                **holder,
                "corrective_action": action[:max_chars],
                "corrective_action_truncated": True,
            }
            record = {**record, "response": holder} if nested else holder
        shortened.append(record)
    return shortened


def report_urls(*record_lists: list[dict[str, Any]]) -> list[str]:
    """Collect the distinct report links from records, in first-seen order."""
    urls = (record.get("url") for records in record_lists for record in records)
    return list(dict.fromkeys(url for url in urls if url))


def paginate(items: list[Any], limit: int, offset: int) -> dict[str, Any]:
    """Slice a list and return a standard pagination envelope.

    Returns a dict with `total`, `count`, `offset`, `items`, `has_more`, and
    `next_offset` — the shape recommended in the MCP best-practices guide.
    """
    total = len(items)
    window = items[offset : offset + limit]
    next_offset = offset + len(window)
    return {
        "total": total,
        "count": len(window),
        "offset": offset,
        "items": window,
        "has_more": next_offset < total,
        "next_offset": next_offset if next_offset < total else None,
    }


def build_provenance(
    data_as_of: str | None,
    source_urls: list[str] | None = None,
    *,
    citation: str = CITE_FINDINGS,
    quoted: bool = True,
) -> dict[str, Any]:
    """Return a provenance block for a response, flagging stale data.

    `data_as_of` is the ISO date (YYYY-MM-DD) the data was collected. An
    unparseable or missing date yields `stale = None` rather than a guess. `citation`
    says how to cite the response. Pass CITE_TOTALS for counts across reports.
    Pass quoted=False only when the response carries no report text.
    """
    days_old: int | None = None
    stale: bool | None = None
    if data_as_of:
        try:
            days_old = (date.today() - date.fromisoformat(data_as_of[:10])).days
            stale = days_old > settings.stale_after_days
        except ValueError:
            pass
    return Provenance(
        data_as_of=data_as_of,
        days_old=days_old,
        stale=stale,
        source_urls=source_urls or [],
        citation=citation,
        quoted_fields=list(QUOTED_FIELDS) if quoted else [],
        quoted_text=QUOTED_TEXT if quoted else "",
    ).model_dump()
