"""The hardened HTTP client for the OIG data API.

Every request to the data API goes through fetch_json: a fixed, operator-set
origin, relative paths only, no redirects or proxies, a size cap, an overall
deadline, a process-wide concurrency limit, and Access headers the caller cannot
replace. Failures leave here as a sanitized UpstreamServiceError (failures.py).
Formatting results and wording hints do not belong here.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, nullcontext
from typing import Any
from urllib.parse import unquote, urlsplit

import anyio
import httpx

from oig_mcp import tracing
from oig_mcp.config import settings
from oig_mcp.failures import UpstreamServiceError

_log = logging.getLogger("oig_mcp.usage")

# Federal APIs can be slow or intermittently unresponsive — always use an
# explicit timeout. Bump this for large exports.
DEFAULT_TIMEOUT = 30.0
MAX_RESPONSE_BYTES = 5_000_000

# Keep outbound origins operator-controlled. Do not replace this with a tool
# argument. The origin comes from OIG_DATA_API_BASE_URL (see config.py).
API_BASE_URL = settings.oig_data_api_base_url

# For the operator's log, not the client: it names settings and how the API runs.
UNREACHABLE_LOG = (
    "data API unreachable (%s): start the oig-data-source API (docker compose up -d) "
    "or check OIG_DATA_API_BASE_URL and the Cloudflare Access service token"
)
# Upstream requests in flight at once, across all tool calls in this process. The
# inspection brief alone runs ten searches, and the data API runs four at a time,
# so one burst of briefs would otherwise queue hundreds of requests upstream.
MAX_CONCURRENT_UPSTREAM = 8
_upstream_limiter = anyio.CapacityLimiter(MAX_CONCURRENT_UPSTREAM)


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


# One pooled client for the server's life, opened by http_client_lifespan, so calls
# reuse connections instead of a new TLS handshake through Cloudflare each time.
# Measured against the hosted API, it cut median search time by about 30 percent.
_shared_client: httpx.AsyncClient | None = None


def _new_client() -> httpx.AsyncClient:
    """A client fixed to the configured origin, with no redirects or proxies."""
    return httpx.AsyncClient(
        base_url=API_BASE_URL,
        follow_redirects=False,
        timeout=DEFAULT_TIMEOUT,
        trust_env=False,
    )


@asynccontextmanager
async def http_client_lifespan(_server: Any) -> AsyncIterator[dict[str, Any]]:
    """Open the shared client when the server starts and close it at shutdown."""
    global _shared_client
    _shared_client = _new_client()
    try:
        yield {}
    finally:
        client, _shared_client = _shared_client, None
        await client.aclose()


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
    # Identity encoding: httpx expands each compressed chunk whole before the size
    # check below sees it, so one small chunk could grow to many megabytes first.
    request_headers = {
        "Accept": "application/json",
        **(headers or {}),
        "Accept-Encoding": "identity",
    }
    request_headers.update(tracing.headers())
    request_headers.update(_access_headers())
    started = time.monotonic()
    status: int | None = None
    content = bytearray()
    error: str | None = None
    # Outside a running server (a script or a direct call), open a client for this
    # one request. Headers go on the request, never on the shared client.
    opened = nullcontext(_shared_client) if _shared_client else _new_client()
    try:
        # httpx's timeout is per phase, so a slow trickle could hold a call open;
        # fail_after bounds the whole request, including the wait for a slot.
        with anyio.fail_after(timeout * 2):
            async with (
                _upstream_limiter,
                opened as client,
                client.stream(
                    "GET",
                    safe_path,
                    params=params,
                    headers=request_headers,
                    timeout=timeout,
                ) as response,
            ):
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
    except httpx.InvalidURL:
        # Arguments that make the request itself invalid, such as an over-long query.
        error = "invalid request"
        raise UpstreamServiceError(
            "The request was too large or malformed.", status_code=400
        ) from None
    except (httpx.RequestError, TimeoutError) as exc:
        error = type(exc).__name__
        _log.warning(UNREACHABLE_LOG, error)
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
