#!/usr/bin/env python3
"""Read the test traces: each tool call, and what the data API did for it.

    python3 deploy/traces.py list              # recent tool calls
    python3 deploy/traces.py list --client mkuprian -n 50
    python3 deploy/traces.py show latest       # one call, with the API's side
    python3 deploy/traces.py show 3f9c2a1b7d6e4f00 --full
    python3 deploy/traces.py api               # recent API requests, from any caller

Tool calls come from oig-mcp's logs/traces, and API requests from oig-data-source's
data/logs/traces. Both are on only while MCP_TRACE_DIR and OIG_TRACE_DIR are set.
Traces hold questions and answers, so read them here rather than sharing the files.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MCP_DIR = ROOT / "logs" / "traces"
API_DIR = ROOT.parent / "oig-data-source" / "data" / "logs" / "traces"


def load(directory: Path, pattern: str = "*/*.json") -> list[dict]:
    records = []
    for path in sorted(directory.glob(pattern)):
        try:
            records.append(json.loads(path.read_text()))
        except (OSError, ValueError):
            continue
    return records


def short(value: object, limit: int = 160) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def list_calls(args: argparse.Namespace) -> None:
    records = [
        r
        for r in load(args.mcp_dir)
        if not args.client or r.get("client") == args.client
    ]
    if not records:
        print("No tool-call traces.")
        return
    for r in records[-args.n :]:
        print(
            f"{r['time'][:19]}  {r['trace_id']}  {r.get('client', ''):<12} "
            f"{r.get('tool', ''):<32} {r.get('outcome', ''):<12} "
            f"{r.get('ms', 0):>6} ms  {len(r.get('api_calls', []))} API"
        )


def list_api(args: argparse.Namespace) -> None:
    records = load(args.api_dir)
    if not records:
        print("No API traces.")
        return
    for r in records[-args.n :]:
        print(
            f"{r['time'][:19]}  {r['trace_id']}  {r.get('client') or '-':<12} "
            f"{r.get('status')}  {r.get('ms', 0):>5} ms  {r['path']}  "
            f"{short(r.get('query'), 80)}"
        )


def show_api(record: dict, full: bool) -> None:
    print(
        f"    API {record['path']} -> {record.get('handler')}  "
        f"{record.get('status')}  {record.get('ms')} ms  "
        f"{record.get('response_bytes')} B"
    )
    if record.get("query"):
        print(f"      query: {short(record['query'])}")
    steps = record.get("steps", {})
    if "query" in steps:
        q = steps["query"]
        print(
            f"      embedding: {'ok' if q.get('embedded') else 'unavailable'} "
            f"({q.get('embed_ms')} ms)  "
            f"keyword match: {short(q.get('keyword_match'), 100)}"
        )
    if "fusion" in steps:
        fusion = steps["fusion"]
        for name, ranked in fusion["lists"].items():
            print(
                f"      {name}: {ranked['count']} hits, "
                f"top {short(ranked['top'][:5], 100)}"
            )
        print(f"      merged: {fusion['merged_count']}")
        for item in fusion["merged_top"][: 20 if full else 5]:
            print(
                f"        {item['rec_id']}  score {item['score']}  "
                f"ranks {item['ranks']}"
            )
    print(
        f"      SQL: {len(record.get('sql', []))} statements, plus "
        f"{record.get('sql_internal', 0)} internal index lookups"
    )
    if full:
        for statement in record.get("sql", []):
            print(f"        {statement}")
        print("      response:")
        print(json.dumps(record.get("response"), indent=2, ensure_ascii=False))


def show(args: argparse.Namespace) -> None:
    calls = load(args.mcp_dir)
    if args.trace == "latest":
        if not calls:
            sys.exit("No tool-call traces.")
        call = calls[-1]
    else:
        matches = [c for c in calls if c["trace_id"].startswith(args.trace)]
        call = matches[-1] if matches else None
    trace_id = call["trace_id"] if call else args.trace
    api = load(args.api_dir, f"*/*-{trace_id}*-*.json")
    if call is None and not api:
        sys.exit(f"No trace {args.trace}.")
    if call:
        print(
            f"{call['time'][:19]}  {call.get('client')}  {call.get('tool')}  "
            f"{call.get('ms')} ms  {call.get('outcome')}  trace {trace_id}"
        )
        print(f"  arguments: {short(call.get('arguments'), 300)}")
        for c in call.get("api_calls", []):
            error = f"  {c['error']}" if c.get("error") else ""
            print(
                f"  GET {c['path']}  {c.get('status')}  {c.get('ms')} ms  "
                f"{c.get('bytes')} B{error}  {short(c.get('params'), 100)}"
            )
    for record in api:
        show_api(record, args.full)
    if call:
        if call.get("error"):
            print(f"  error: {call['error']}")
        result = call.get("result")
        if args.full:
            print("  result:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            size = len(json.dumps(result, default=str))
            print(f"  result: {size} characters  {short(result, 200)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mcp-dir", type=Path, default=MCP_DIR)
    parser.add_argument("--api-dir", type=Path, default=API_DIR)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("list")
    p.add_argument("-n", type=int, default=20)
    p.add_argument("--client")
    p.set_defaults(run=list_calls)
    p = sub.add_parser("api")
    p.add_argument("-n", type=int, default=20)
    p.set_defaults(run=list_api)
    p = sub.add_parser("show")
    p.add_argument("trace", nargs="?", default="latest")
    p.add_argument("--full", action="store_true")
    p.set_defaults(run=show)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
