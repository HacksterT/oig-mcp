"""Send hostile, malformed, and heavy input to a running oig-mcp server.

    uv run python deploy/robustness_check.py --url http://127.0.0.1:8000

Every tool gets inputs it should refuse or survive: path traversal and encoded
paths, header and query injection, SQL and full-text-search syntax, values past
every bound, wrong types, unknown fields, and names that match nothing. Each reply
must be a clean answer or a clean error: no crash, no stack trace, no upstream
address, no credential. Then three load checks: a burst past the per-client rate
limit (refused cleanly, then recovered), parallel searches past the data API's four
search slots (answered or told to retry), and parallel light calls for latency.

No model is involved. It needs MCP_AUTH_TOKEN, from the environment or `.env`;
secrets are read in-process and never printed. Exit code 0 means every check passed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastmcp import Client
from mcp_types import PromptReference

sys.path.insert(0, str(Path(__file__).parent))
from verify_deployment import (  # noqa: E402
    Report,
    bearer_transport,
    load_dotenv,
    watched_secrets,
)

ROOT = Path(__file__).resolve().parents[1]
PACE = 0.6  # seconds between hostile calls, under the 2 per second limit
LEAK_MARKERS = ("Traceback", 'File "', "sqlite3.", "httpx.", "Exception")

# (tool, arguments, what the case tests). Each must end in a clean answer or error.
REPORT = "vaoig_get_report"
SEARCH = "vaoig_search_findings"
ANALYZE = "vaoig_analyze_recommendations"
PROFILE = "vaoig_get_facility_profile"
BRIEF = "vaoig_get_inspection_brief"
CLUSTERS = "vaoig_find_systemic_clusters"
STATUS = "vaoig_get_dataset_status"

HOSTILE: list[tuple[str, dict[str, Any], str]] = [
    (REPORT, {"report_number": "../../etc/passwd"}, "path traversal"),
    (REPORT, {"report_number": "%2e%2e%2fv1%2fmeta"}, "encoded traversal"),
    (REPORT, {"report_number": "26-00055-01?admin=1"}, "query injection"),
    (REPORT, {"report_number": "26-00055-01\r\nX-Evil: 1"}, "header injection"),
    (REPORT, {"report_number": "' OR '1'='1"}, "SQL syntax"),
    (REPORT, {"report_number": "x" * 31}, "over the length bound"),
    (REPORT, {"report_number": ""}, "empty value"),
    (REPORT, {"node_id": -1}, "negative id"),
    (REPORT, {"node_id": 10**12}, "id that does not exist"),
    (REPORT, {}, "neither argument"),
    (REPORT, {"report_number": "26-99999-999"}, "report that does not exist"),
    (SEARCH, {"question": "a" * 501}, "over the length bound"),
    (SEARCH, {"question": "a"}, "under the length bound"),
    (SEARCH, {"question": 'NEAR(cart lock) "unclosed'}, "search syntax"),
    (SEARCH, {"question": "* OR 1=1 --"}, "search and SQL syntax"),
    (SEARCH, {"question": "\u0000‮💊🔒"}, "control and emoji"),
    (SEARCH, {"question": "carts", "limit": 0}, "limit below bound"),
    (SEARCH, {"question": "carts", "limit": 101}, "limit above bound"),
    (SEARCH, {"question": "carts", "offset": -1}, "negative offset"),
    (SEARCH, {"question": "carts", "offset": 10**9}, "offset past end"),
    (SEARCH, {"question": "carts", "limit": "ten"}, "wrong type"),
    (
        SEARCH,
        {"question": "carts", "filters": {"admin": True}},
        "unknown filter",
    ),
    (
        SEARCH,
        {"question": "carts", "filters": {"station_number": "../meta"}},
        "traversal in a filter",
    ),
    (ANALYZE, {"group_by": "facility"}, "invalid grouping"),
    (
        ANALYZE,
        {"group_by": "year", "filters": {"published_from": "2026-13-45"}},
        "impossible date",
    ),
    (
        ANALYZE,
        {"group_by": "year", "filters": {"status": ["deleted"]}},
        "invalid status",
    ),
    (
        ANALYZE,
        {"group_by": "office", "filters": {"domain": "OIT"}},
        "office in the domain filter",
    ),
    (
        ANALYZE,
        {"group_by": "year", "keywords": "a" * 201},
        "over the length bound",
    ),
    (PROFILE, {"facility": "%"}, "SQL wildcard"),
    (PROFILE, {"facility": "../../v1/meta"}, "path traversal"),
    (PROFILE, {"facility": "Nowhere Land"}, "no match"),
    (PROFILE, {"facility": "a" * 201}, "over the length bound"),
    (BRIEF, {"facility": "Nowhere Land"}, "no match"),
    (CLUSTERS, {"cluster_id": 10**9}, "cluster that does not exist"),
    (CLUSTERS, {"wording": "'; DROP TABLE x;--"}, "SQL syntax"),
    (CLUSTERS, {"min_reports": 0}, "below bound"),
    ("vaoig_no_such_tool", {}, "unknown tool"),
]
RESOURCES = [
    "vaoig://taxonomy/..%2F..%2Fmeta",
    "vaoig://taxonomy/does-not-exist",
]
# Argument completion takes text as a person types it. These must yield a clean,
# bounded answer: a few suggestions or none, never an error or internal detail.
CHECKLIST = PromptReference(type="ref/prompt", name="inspection_readiness_checklist")
COMPLETIONS = [
    (CHECKLIST, "../../meta?q=1#x", "traversal and query syntax"),
    (CHECKLIST, "x" * 5000, "oversized partial value"),
    (CHECKLIST, "' OR 1=1 --", "SQL syntax"),
]


def reply_text(result: Any) -> str:
    return "\n".join(getattr(item, "text", "") or "" for item in result.content)


def describe(result: Any) -> str:
    """A short, safe description of a reply: answer, error, or validation refusal."""
    text = reply_text(result)
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        body = None
    if not result.is_error:
        if body is None:
            return "answer (not JSON)"
        return f"answer: {body['error'][:60]}" if "error" in body else "answer"
    if "validation error" in text.lower() or "input should" in text.lower():
        return "refused: invalid input"
    if isinstance(body, dict):
        return f"error: {body.get('error', '')[:60]}"
    return f"error: {text[:60]}"


class Checker:
    def __init__(self, report: Report, upstream_host: str) -> None:
        self.report = report
        self.upstream_host = upstream_host

    def clean(self, text: str) -> tuple[bool, str]:
        if not self.report.has_no_secret(text):
            return False, "a credential appeared"
        if self.upstream_host and self.upstream_host in text:
            return False, "the upstream address appeared"
        marker = next((m for m in LEAK_MARKERS if m in text), None)
        if marker:
            return False, f"internal detail appeared: {marker}"
        return True, ""


async def hostile_inputs(client: Client, checker: Checker) -> None:
    print("\nHostile and malformed input")
    for tool, arguments, case in HOSTILE:
        try:
            result = await client.call_tool(tool, arguments, raise_on_error=False)
            text = reply_text(result)
            ok, why = checker.clean(text)
            outcome = describe(result)
        except Exception as exc:  # A protocol-level failure is a failed check.
            ok, why, outcome = False, f"client raised {type(exc).__name__}", ""
        checker.report.check(f"{tool}: {case}", ok, why or outcome)
        await asyncio.sleep(PACE)
    for uri in RESOURCES:
        try:
            contents = await client.read_resource(uri)
            text = " ".join(getattr(c, "text", "") or "" for c in contents)
            outcome = "answer"
        except Exception as exc:
            text = str(exc)
            outcome = f"refused: {type(exc).__name__}"
        ok, why = checker.clean(text)
        checker.report.check(f"resource {uri}", ok, why or outcome)
        await asyncio.sleep(PACE)
    for ref, value, case in COMPLETIONS:
        try:
            argument = {"name": "facility", "value": value}
            completion = await client.complete(ref, argument)
            text = " ".join(completion.values)
            ok, why = checker.clean(text)
            ok = ok and len(completion.values) <= 10
            outcome = f"{len(completion.values)} suggestions"
        except Exception as exc:
            ok, why, outcome = False, f"client raised {type(exc).__name__}", ""
        checker.report.check(f"completion: {case}", ok, why or outcome)
        await asyncio.sleep(PACE)


async def rate_limit(client: Client, checker: Checker) -> None:
    print("\nBurst past the per-client rate limit, then recovery")
    calls = [
        client.call_tool(REPORT, {"report_number": "26-00055-01"}, raise_on_error=False)
        for _ in range(45)
    ]
    results = await asyncio.gather(*calls, return_exceptions=True)
    refused = answered = broken = 0
    for result in results:
        failed = isinstance(result, Exception) or result.is_error
        text = str(result) if isinstance(result, Exception) else reply_text(result)
        answered += not failed
        refused += failed and "rate limit" in text.lower()
        broken += not checker.clean(text)[0]
    checker.report.check(
        "45 calls at once: the limit refuses some, answers the rest",
        refused > 0 and answered > 0 and broken == 0,
        f"{answered} answered, {refused} refused by the limit, {broken} unclean",
    )
    await asyncio.sleep(16)  # the bucket refills at two calls a second
    result = await client.call_tool(STATUS, {}, raise_on_error=False)
    checker.report.check(
        "after a pause, calls succeed again", not result.is_error, describe(result)
    )


async def parallel_searches(client: Client, checker: Checker) -> None:
    print("\nEight searches at once, past the data API's four search slots")
    questions = [
        "unlocked medication carts",
        "suicide risk screening",
        "test result communication",
        "environment of care cleanliness",
        "community care consult delays",
        "controlled substance inspections",
        "staffing shortages in nursing",
        "infection control in dialysis",
    ]
    started = time.perf_counter()
    results = await asyncio.gather(
        *(
            client.call_tool(SEARCH, {"question": q}, raise_on_error=False)
            for q in questions
        ),
        return_exceptions=True,
    )
    seconds = time.perf_counter() - started
    answered = busy = other = 0
    for result in results:
        if isinstance(result, Exception):
            other += 1
            continue
        text = reply_text(result)
        if not checker.clean(text)[0]:
            other += 1
        elif not result.is_error:
            answered += 1
        elif "busy" in text.lower() or "took too long" in text.lower():
            busy += 1
        else:
            other += 1
    checker.report.check(
        "every search is answered or told to retry",
        other == 0 and answered > 0,
        f"{answered} answered, {busy} told to retry, {other} other, {seconds:.1f} s",
    )
    await asyncio.sleep(10)


async def latency(client: Client, checker: Checker) -> None:
    print("\nTen light calls at once")
    calls = [
        (REPORT, {"report_number": "25-00193-155"}),
        (ANALYZE, {"group_by": "office"}),
        (PROFILE, {"facility": "El Paso"}),
        (CLUSTERS, {"limit": 5}),
        (STATUS, {}),
    ] * 2

    async def timed(tool: str, arguments: dict) -> tuple[float, bool]:
        started = time.perf_counter()
        result = await client.call_tool(tool, arguments, raise_on_error=False)
        return time.perf_counter() - started, not result.is_error

    results = await asyncio.gather(*(timed(t, a) for t, a in calls))
    seconds = sorted(s for s, _ in results)
    ok = all(success for _, success in results)
    checker.report.check(
        "all ten succeed",
        ok,
        f"median {statistics.median(seconds):.2f} s, slowest {seconds[-1]:.2f} s",
    )


async def run(url: str, token: str, checker: Checker) -> None:
    async with Client(bearer_transport(url, token), timeout=120) as client:
        await hostile_inputs(client, checker)
        await rate_limit(client, checker)
        await parallel_searches(client, checker)
        await latency(client, checker)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    token = os.environ.get("MCP_AUTH_TOKEN", "")
    if not token:
        print("MCP_AUTH_TOKEN must be set.")
        return 2
    upstream = urlparse(os.environ.get("OIG_DATA_API_BASE_URL", "")).hostname or ""
    if upstream in {"localhost", "127.0.0.1"}:
        upstream = ""
    report = Report(watched_secrets())
    asyncio.run(run(args.url, token, Checker(report, upstream)))
    print(f"\n{report.passed} passed, {report.failed} failed")
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
