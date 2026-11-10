"""Shared helpers: HTTP client, response formatting, and pagination.

Import these from your tool modules instead of re-implementing them. Keeping
I/O and formatting here keeps each tool file focused on its own logic.
"""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import unquote, urlsplit

import httpx
from fastmcp.exceptions import ToolError

from oig_mcp import tracing
from oig_mcp.config import settings

# Federal APIs can be slow or intermittently unresponsive — always use an
# explicit timeout. Bump this for large exports.
DEFAULT_TIMEOUT = 30.0
MAX_RESPONSE_BYTES = 5_000_000

# Keep outbound origins operator-controlled. Do not replace this with a tool
# argument. The origin comes from OIG_DATA_API_BASE_URL (see config.py).
API_BASE_URL = settings.oig_data_api_base_url

UNREACHABLE_HINT = (
    "The OIG data API is not reachable. Start the oig-data-source API locally "
    "(docker compose up -d) or check OIG_DATA_API_BASE_URL and the Cloudflare Access "
    "service token in the server's environment."
)

# These travel in each result, because not every MCP host passes the server's
# instructions to its model. Totals have no single report to cite.
CITE_FINDINGS = (
    "Give the report number and link for each finding you mention, and state "
    "data_as_of."
)
CITE_TOTALS = (
    "State data_as_of. These are totals across reports, so no single report is the "
    "source."
)

READ_ONLY_TOOL = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}


def _access_headers() -> dict[str, str]:
    """Cloudflare Access service-token headers and the data API key, when set.

    Applied last in fetch_json, so a caller can't replace them."""
    headers = {}
    if settings.cf_access_client_id and settings.cf_access_client_secret:
        headers["CF-Access-Client-Id"] = settings.cf_access_client_id
        headers["CF-Access-Client-Secret"] = settings.cf_access_client_secret
    if settings.oig_data_api_key:
        headers["Authorization"] = f"Bearer {settings.oig_data_api_key}"
    return headers


class UpstreamServiceError(RuntimeError):
    """Sanitized external-service failure safe to return to an MCP client."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _validate_relative_path(path: str) -> str:
    """Reject paths that could select or escape the configured API origin."""
    parsed = urlsplit(path)
    decoded_path = parsed.path
    for _ in range(3):
        decoded = unquote(decoded_path)
        if decoded == decoded_path:
            break
        decoded_path = decoded
    segments = decoded_path.replace("\\", "/").split("/")
    if (
        not path
        or parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or decoded_path.startswith(("/", "\\"))
        or any(segment in {".", ".."} for segment in segments)
    ):
        raise ValueError("path must be a relative API path without a query or fragment")
    return path


async def fetch_json(
    path: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    """GET a path from the fixed API origin and return parsed JSON.

    Raises:
        ValueError: if path could select or escape the configured API origin.
        UpstreamServiceError: with a sanitized message for external failures.
    """
    safe_path = _validate_relative_path(path)
    request_headers = {"Accept": "application/json", **(headers or {})}
    request_headers.update(tracing.headers())
    request_headers.update(_access_headers())
    started = time.monotonic()
    status: int | None = None
    content = bytearray()
    error: str | None = None
    try:
        async with httpx.AsyncClient(
            base_url=API_BASE_URL,
            follow_redirects=False,
            timeout=timeout,
            trust_env=False,
        ) as client:
            async with client.stream(
                "GET", safe_path, params=params, headers=request_headers
            ) as response:
                status = response.status_code
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > MAX_RESPONSE_BYTES:
                        raise UpstreamServiceError(
                            "Upstream response exceeded the size limit."
                        )
                return json.loads(content)
    except UpstreamServiceError as exc:
        error = str(exc)
        raise
    except httpx.HTTPStatusError as exc:
        error = f"status {exc.response.status_code}"
        raise UpstreamServiceError(
            f"Upstream service returned status {exc.response.status_code}.",
            status_code=exc.response.status_code,
        ) from None
    except (httpx.DecodingError, json.JSONDecodeError, UnicodeDecodeError):
        error = "invalid JSON"
        raise UpstreamServiceError("Upstream service returned invalid JSON.") from None
    except httpx.RequestError as exc:
        error = type(exc).__name__
        raise UpstreamServiceError("Upstream service request failed.") from None
    finally:
        tracing.api_call(
            safe_path,
            params,
            status,
            round((time.monotonic() - started) * 1000),
            len(content),
            error,
        )


async def fetch_object(
    path: str, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """GET a JSON object, dropping unset parameters so they are not sent as empty."""
    cleaned = {k: v for k, v in (params or {}).items() if v is not None}
    result = await fetch_json(path, params=cleaned)
    if not isinstance(result, dict):
        raise UpstreamServiceError("Upstream service returned an unexpected shape.")
    return result


class ToolFailure(ToolError):
    """A tool call that failed, with an error and a hint the assistant can act on.

    Raise it from a tool. middleware.ToolFailureMiddleware returns it as a result
    marked isError that keeps {"error", "hint"} as structured content, so clients,
    the usage log, and traces all see a failure. Answers such as "not found" or
    "several facilities match" are not failures: return those normally.
    """

    def __init__(self, error: str, hint: str) -> None:
        super().__init__(f"{error} {hint}")
        self.body = {"error": error, "hint": hint}


def tool_error(exc: UpstreamServiceError) -> ToolFailure:
    """Turn an upstream failure into a ToolFailure for the tool to raise."""
    if exc.status_code in {400, 422}:
        hint = "A filter value was rejected. Check its format and try again."
    else:
        hint = UNREACHABLE_HINT
    return ToolFailure(str(exc), hint)


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
) -> dict[str, Any]:
    """Return a provenance block for a response, flagging stale data.

    `data_as_of` is the ISO date (YYYY-MM-DD) the data was collected. An
    unparseable or missing date yields `stale = None` rather than a guess. `citation`
    says how to cite the response. Pass CITE_TOTALS for counts across reports.
    """
    from datetime import date

    from oig_mcp.models import Provenance

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
    ).model_dump()
