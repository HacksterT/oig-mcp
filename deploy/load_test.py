#!/usr/bin/env python3
"""Load test: how the server holds up as concurrent clients ramp up.

    uv run python deploy/load_test.py setup 40      # add load-01..load-40 tokens
    uv run python deploy/load_test.py run --url https://mcp.troymd.com --out out.json
    uv run python deploy/load_test.py cleanup       # remove the load-* tokens

Each simulated client has its own token, so the per-client rate limit is not what
is measured, and its own MCP connection. It repeats tool calls taken from the
saved Claude evaluation runs, so the mix of tools and arguments is what agents
really sent, with a short pause between calls. Stages run for a fixed time each
(1, 5, 10, 20, then 40 clients by default) and report, per stage: calls,
answers, clean refusals (rate limited, data API busy, search too slow), other
errors, throughput, and latency percentiles per tool. Every reply is checked
for a credential, the upstream address, or internal detail, as the robustness
check does. A stage whose other errors pass --max-error-rate stops the test.

`setup` and `cleanup` change MCP_CLIENT_TOKENS in `.env` and recreate the
container, as deploy/mcp_clients.py does; tokens are never printed. Load clients
are named load-NN, so their usage-log lines and traces can be told apart.
Run it only when no one else is using the server: it shares the data API.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import secrets
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastmcp import Client

sys.path.insert(0, str(Path(__file__).parent))
from mcp_clients import read_clients, restart_server, write_clients  # noqa: E402
from robustness_check import Checker, reply_text  # noqa: E402
from verify_deployment import (  # noqa: E402
    Report,
    bearer_transport,
    load_dotenv,
    watched_secrets,
)

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
PREFIX = "load-"
# The saved runs whose tool calls make up the mix: what agents actually sent.
SOURCE_RUNS = ("2026-11-17-sonnet-5-5", "2026-11-17-opus-5-5-s22-branch")
REFUSALS = {
    "rate_limited": "rate limit exceeded",
    "busy": "data api is busy",
    "too_slow": "took too long",
}


def call_pool() -> list[tuple[str, dict[str, Any]]]:
    """Every successful tool call in the source runs, repeats included, so tools
    appear as often as agents used them."""
    pool = []
    for run in SOURCE_RUNS:
        records = json.loads((ROOT / "eval/results" / run / "records.json").read_text())
        for record in records:
            for call in record["run"]["tool_calls"]:
                if not call["is_error"]:
                    pool.append((call["tool"], call.get("arguments") or {}))
    return pool


def outcome_of(result: Any, text: str) -> str:
    if not result.is_error:
        return "answered"
    folded = text.casefold()
    return next((k for k, words in REFUSALS.items() if words in folded), "error")


async def client_loop(
    url: str,
    token: str,
    pool: list[tuple[str, dict[str, Any]]],
    deadline: float,
    think: float,
    checker: Checker,
    rows: list[dict[str, Any]],
) -> None:
    rng = random.Random()
    await asyncio.sleep(rng.uniform(0, think))  # don't start every client at once
    try:
        async with Client(bearer_transport(url, token), timeout=120) as client:
            while time.monotonic() < deadline:
                tool, arguments = rng.choice(pool)
                started = time.monotonic()
                try:
                    result = await client.call_tool(
                        tool, arguments, raise_on_error=False
                    )
                    text = reply_text(result)
                    outcome = outcome_of(result, text)
                except Exception as exc:  # A transport failure is an error here.
                    text, outcome = f"{type(exc).__name__}", "error"
                clean, _ = checker.clean(text)
                rows.append(
                    {
                        "tool": tool,
                        "ms": round((time.monotonic() - started) * 1000),
                        "outcome": outcome,
                        "clean": clean,
                    }
                )
                await asyncio.sleep(rng.uniform(think / 2, think * 1.5))
    except Exception as exc:
        rows.append(
            {
                "tool": "connect",
                "ms": 0,
                "outcome": "error",
                "clean": True,
                "detail": type(exc).__name__,
            }
        )


def percentile(values: list[int], share: float) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))]


def summarize(clients: int, seconds: float, rows: list[dict[str, Any]]) -> dict:
    outcomes = Counter(row["outcome"] for row in rows)
    by_tool: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        if row["outcome"] == "answered":
            by_tool[row["tool"]].append(row["ms"])
    answered = [row["ms"] for row in rows if row["outcome"] == "answered"]
    return {
        "clients": clients,
        "seconds": seconds,
        "calls": len(rows),
        "outcomes": dict(outcomes),
        "unclean": sum(not row["clean"] for row in rows),
        "calls_per_second": round(len(rows) / seconds, 2),
        "answered_ms": {
            "p50": percentile(answered, 0.50),
            "p95": percentile(answered, 0.95),
            "p99": percentile(answered, 0.99),
        }
        if answered
        else None,
        "by_tool": {
            tool: {
                "answered": len(ms),
                "p50": percentile(ms, 0.50),
                "p95": percentile(ms, 0.95),
                "max": max(ms),
            }
            for tool, ms in sorted(by_tool.items())
        },
    }


def show(stage: dict) -> None:
    o = stage["outcomes"]
    refused = sum(o.get(k, 0) for k in REFUSALS)
    lat = stage["answered_ms"] or {"p50": 0, "p95": 0, "p99": 0}
    print(
        f"{stage['clients']:>3} clients: {stage['calls']:>5} calls"
        f" ({stage['calls_per_second']}/s), {o.get('answered', 0)} answered,"
        f" {refused} refused cleanly {dict((k, o[k]) for k in REFUSALS if k in o)},"
        f" {o.get('error', 0)} errors, {stage['unclean']} unclean;"
        f" answered p50 {lat['p50']} ms, p95 {lat['p95']} ms, p99 {lat['p99']} ms",
        flush=True,
    )


async def run(args: argparse.Namespace) -> int:
    load_dotenv(ENV_FILE)
    tokens = [
        t for n, t in sorted(read_clients(ENV_FILE).items()) if n.startswith(PREFIX)
    ]
    stages = [int(s) for s in args.stages.split(",")]
    if len(tokens) < max(stages):
        print(f"Need {max(stages)} load clients; run `setup {max(stages)}` first.")
        return 2
    upstream = urlparse(os.environ.get("OIG_DATA_API_BASE_URL", "")).hostname or ""
    checker = Checker(Report(watched_secrets() + tokens), upstream)
    pool = call_pool()
    print(f"{len(pool)} calls in the mix: {dict(Counter(t for t, _ in pool))}")
    results = []
    for clients in stages:
        rows: list[dict[str, Any]] = []
        started = time.monotonic()
        deadline = started + args.seconds
        await asyncio.gather(
            *(
                client_loop(args.url, token, pool, deadline, args.think, checker, rows)
                for token in tokens[:clients]
            )
        )
        stage = summarize(clients, round(time.monotonic() - started, 1), rows)
        results.append(stage)
        show(stage)
        if args.out:
            Path(args.out).write_text(json.dumps({"stages": results}, indent=1))
        errors = stage["outcomes"].get("error", 0)
        if stage["unclean"] or errors > args.max_error_rate * max(stage["calls"], 1):
            print("Stopping: errors or unclean replies passed the threshold.")
            return 1
        await asyncio.sleep(args.rest)  # let buckets and queues drain between stages
    return 0


def setup(count: int) -> int:
    clients = {
        n: t for n, t in read_clients(ENV_FILE).items() if not n.startswith(PREFIX)
    }
    for index in range(1, count + 1):
        clients[f"{PREFIX}{index:02d}"] = secrets.token_urlsafe(32)
    write_clients(ENV_FILE, clients)
    print(f"Added {count} load clients (tokens not shown). Restarting the server.")
    return 0 if restart_server() else 1


def cleanup() -> int:
    clients = read_clients(ENV_FILE)
    kept = {n: t for n, t in clients.items() if not n.startswith(PREFIX)}
    write_clients(ENV_FILE, kept)
    print(f"Removed {len(clients) - len(kept)} load clients. Restarting the server.")
    return 0 if restart_server() else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("setup")
    add.add_argument("count", type=int)
    sub.add_parser("cleanup")
    go = sub.add_parser("run")
    go.add_argument("--url", required=True, help="Server base URL, without /mcp")
    go.add_argument("--stages", default="1,5,10,20,40")
    go.add_argument("--seconds", type=float, default=60)
    go.add_argument("--think", type=float, default=1.0, help="Mean pause between calls")
    go.add_argument("--rest", type=float, default=20, help="Pause between stages")
    go.add_argument("--max-error-rate", type=float, default=0.10)
    go.add_argument("--out", help="Write the stage results here as JSON")
    args = parser.parse_args()
    if args.command == "setup":
        return setup(args.count)
    if args.command == "cleanup":
        return cleanup()
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
