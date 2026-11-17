"""Failures a tool can report, and what the assistant should do about each.

Holds the sanitized upstream error, the ToolFailure a tool raises, and the hint
texts chosen by the data API's status. Messages here reach clients, so they name
no hosts, settings, or credentials. The HTTP client lives in upstream.py and
imports from here, never the other way.
"""

from __future__ import annotations

from fastmcp.exceptions import ToolError

UNREACHABLE_HINT = (
    "The OIG data API did not answer. Try the same call once more; if it fails "
    "again, tell the user the data could not be reached."
)
SERVER_ERROR_HINT = (
    "The data API failed on this request. Try it once more, then with fewer or "
    "different filters; if it still fails, tell the user this part could not be "
    "retrieved rather than giving a number."
)
# The API runs at most four searches at once and queues the rest for 10 seconds,
# then answers 429. The assistant retries, not this server: a retry here would
# stack another queue wait onto a call that is already slow, during an overload.
BUSY_HINT = (
    "The data API is busy with other searches. Wait about five seconds and try again."
)
# A full-text query that runs past two seconds is stopped with 503.
TIMED_OUT_HINT = (
    "The search took too long or the data API is briefly unavailable. Try fewer or "
    "more specific words, or add filters, then try again."
)


class UpstreamServiceError(RuntimeError):
    """Sanitized external-service failure safe to return to an MCP client."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


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


def hint_for(exc: UpstreamServiceError) -> str:
    """What the assistant should do about an upstream failure, by its status."""
    if exc.status_code in {400, 422}:
        return "A filter value was rejected. Check its format and try again."
    if exc.status_code == 429:
        return BUSY_HINT
    if exc.status_code == 503:
        return TIMED_OUT_HINT
    if exc.status_code == 500:
        # The API answered and failed; a gateway status (502, 504) means it did not.
        return SERVER_ERROR_HINT
    return UNREACHABLE_HINT


def tool_error(exc: UpstreamServiceError) -> ToolFailure:
    """Turn an upstream failure into a ToolFailure for the tool to raise."""
    return ToolFailure(str(exc), hint_for(exc))
