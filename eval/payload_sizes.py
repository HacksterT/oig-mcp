"""Measure what each tool result costs a model, with no model involved.

Replays the tool calls saved in evaluation runs (records.json) against the
server in this checkout, in process, using the live data API from `.env`, and
reports each result's size in characters and approximate tokens (characters
divided by four), by tool and by top-level field. Run it before and after a
change to a tool's results to see what the change saves.

    uv run python eval/payload_sizes.py eval/results/2026-11-17-opus-5-5-after-fixes
    uv run python eval/payload_sizes.py RUN_DIR [RUN_DIR ...] --json sizes.json

A call that the saved run made several times with the same arguments is
replayed once and counted once per call, as the model received it each time.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from fastmcp import Client

from oig_mcp.app import mcp

CHARS_PER_TOKEN = 4


def compact_size(value: Any) -> int:
    return len(json.dumps(value, separators=(",", ":"), ensure_ascii=False))


def saved_calls(run_dirs: list[Path]) -> list[tuple[str, str, dict[str, Any]]]:
    """(question id, tool, arguments) for every tool call in the saved runs."""
    calls = []
    for run_dir in run_dirs:
        for record in json.loads((run_dir / "records.json").read_text()):
            for call in record["run"].get("tool_calls", []):
                calls.append((record["id"], call["tool"], call.get("arguments") or {}))
    return calls


async def replay(calls: list[tuple[str, str, dict[str, Any]]]) -> list[dict[str, Any]]:
    measured: dict[str, dict[str, Any]] = {}
    rows = []
    async with Client(mcp) as client:
        for question, tool, arguments in calls:
            key = json.dumps([tool, arguments], sort_keys=True)
            if key not in measured:
                result = await client.call_tool(tool, arguments, raise_on_error=False)
                text = "".join(getattr(c, "text", "") or "" for c in result.content)
                body = result.structured_content or {}
                measured[key] = {
                    "chars": len(text),
                    "error": result.is_error,
                    "fields": {k: compact_size(v) for k, v in body.items()},
                }
            rows.append({"question": question, "tool": tool, **measured[key]})
    return rows


def report(rows: list[dict[str, Any]]) -> None:
    by_tool: dict[str, list[int]] = defaultdict(list)
    fields: dict[str, Counter] = defaultdict(Counter)
    by_question: Counter = Counter()
    for row in rows:
        by_tool[row["tool"]].append(row["chars"])
        fields[row["tool"]].update(row["fields"])
        by_question[row["question"]] += row["chars"]
    total = sum(row["chars"] for row in rows)
    print(
        f"{len(rows)} calls, {total:,} characters, ~{total // CHARS_PER_TOKEN:,} tokens"
    )
    print("\nBy tool (characters per call)")
    print(f"  {'tool':34} {'calls':>5} {'median':>8} {'max':>8} {'total':>9}")
    for tool, sizes in sorted(by_tool.items(), key=lambda kv: -sum(kv[1])):
        print(
            f"  {tool:34} {len(sizes):5} {int(statistics.median(sizes)):8,}"
            f" {max(sizes):8,} {sum(sizes):9,}"
        )
    print("\nLargest fields, summed over calls")
    for tool, counter in sorted(fields.items(), key=lambda kv: -sum(by_tool[kv[0]])):
        top = ", ".join(f"{k} {v:,}" for k, v in counter.most_common(4))
        print(f"  {tool}: {top}")
    print("\nLargest questions (characters across their calls)")
    for question, size in by_question.most_common(6):
        print(f"  {question:34} {size:9,}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("runs", nargs="+", type=Path, help="evaluation result folders")
    parser.add_argument("--json", type=Path, help="also write every row here")
    args = parser.parse_args()
    rows = asyncio.run(replay(saved_calls(args.runs)))
    report(rows)
    if args.json:
        args.json.write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
