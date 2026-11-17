"""What the facility form saves: the same question, asked with and without it.

Runs "What has OIG found at the Columbia VA?" several times in each arm, over
stdio, with Claude through Anthropic's API and the server's own instructions as
the system prompt, as in the Phoenix harness (eval/phoenix/agent.py):

- before: the server before #114 (`--before`, checked out in a worktree), with a
  client that shows the form; the scripted user picks Missouri (589A4).
- after: the current server, the same form and pick. The result now says the
  user chose.
- no_form: the current server with a client that cannot show forms, the path most
  hosts take: the server returns the matches and a next step, the model asks in
  chat, and the scripted user answers "The one in Missouri."

Measures, per run: calls to the server, model requests, user turns, tokens, tool
output read, whether the form was shown, and which facilities were opened.

    uv run --group eval python eval/elicitation/ab_run.py --runs 5
    uv run --group eval python eval/elicitation/ab_run.py --runs 5 --arms no_form
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

import anthropic
from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

ROOT = Path(__file__).resolve().parents[2]
QUESTION = "What has OIG found at the Columbia VA?"
CHOICE = "589A4"  # Missouri, as in the Claude Code takes
USER_REPLY = "The one in Missouri."  # the user's answer when asked in chat
FACILITY_TOOLS = {"vaoig_get_facility_profile", "vaoig_get_inspection_brief"}
MAX_TURNS = 15
SUMMARY_KEYS = [
    "server_calls",
    "facility_calls",
    "model_requests",
    "user_turns",
    "tokens",
    "tool_output_chars",
    "seconds",
]


def server(directory: Path) -> StdioTransport:
    return StdioTransport(
        command="uv", args=["--directory", str(directory), "run", "oig-mcp"]
    )


def _station(data: dict) -> str | None:
    facility = data.get("facility") or {}
    return data.get("station_number") or facility.get("station_number")


async def one_run(
    directory: Path, llm: Any, model: str, effort: str, *, form: bool
) -> dict:
    asked: list[str] = []

    async def choose(message, response_type, params, context):
        asked.append(message)
        return CHOICE

    usage = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
    calls: list[dict] = []
    requests, user_turns = 0, 1
    started = time.perf_counter()
    handler = {"elicitation_handler": choose} if form else {}
    async with Client(server(directory), timeout=180, **handler) as client:
        tools = [
            {
                "name": t.name,
                "description": t.description or "",
                "input_schema": t.inputSchema,
            }
            for t in await client.list_tools()
        ]
        messages: list[dict] = [{"role": "user", "content": QUESTION}]
        answer = ""
        for _ in range(MAX_TURNS):
            response = await llm.messages.create(
                model=model,
                max_tokens=16000,
                system=client.instructions or "",
                tools=tools,
                messages=messages,
                output_config={"effort": effort},
                cache_control={"type": "ephemeral"},
            )
            requests += 1
            usage["input"] += response.usage.input_tokens
            usage["output"] += response.usage.output_tokens
            usage["cache_write"] += response.usage.cache_creation_input_tokens or 0
            usage["cache_read"] += response.usage.cache_read_input_tokens or 0
            answer = "\n".join(b.text for b in response.content if b.type == "text")
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason == "pause_turn":
                continue
            if response.stop_reason != "tool_use":
                opened = any(c["station"] for c in calls)
                if not form and not opened and user_turns == 1:
                    # The model asked which facility; the user answers in chat.
                    messages.append({"role": "user", "content": USER_REPLY})
                    user_turns += 1
                    continue
                break
            results = []
            for block in [b for b in response.content if b.type == "tool_use"]:
                result = await client.call_tool(
                    block.name, block.input, raise_on_error=False
                )
                text = "\n".join(
                    i.text for i in result.content if getattr(i, "text", None)
                )
                data = result.structured_content or {}
                calls.append(
                    {
                        "tool": block.name,
                        "arguments": block.input,
                        "station": _station(data),
                        "matches": len(data.get("matches") or []) or None,
                        "result_chars": len(text),
                    }
                )
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": text or "(empty)",
                    }
                )
            messages.append({"role": "user", "content": results})
    facility_calls = [c for c in calls if c["tool"] in FACILITY_TOOLS]
    stations = {c["station"] for c in facility_calls if c["station"]}
    return {
        "server_calls": len(calls),
        "facility_calls": len(facility_calls),
        "model_requests": requests,
        "user_turns": user_turns,
        "tokens": sum(usage.values()),
        "usage": usage,
        "tool_output_chars": sum(c["result_chars"] for c in calls),
        "form_shown": len(asked),
        "stations_opened": sorted(stations),
        "looked_up_another": bool(stations - {CHOICE}),
        "seconds": round(time.perf_counter() - started, 1),
        "calls": calls,
        "answer": answer,
    }


def summary(runs: list[dict]) -> dict:
    out: dict[str, Any] = {
        k: {
            "median": statistics.median(r[k] for r in runs),
            "each": [r[k] for r in runs],
        }
        for k in SUMMARY_KEYS
    }
    out["looked_up_another"] = sum(r["looked_up_another"] for r in runs)
    out["form_shown"] = sum(1 for r in runs if r["form_shown"])
    return out


def before_worktree(commit: str) -> Path:
    """The server as it was at `commit`, sharing this checkout's .env by link."""
    worktree = Path("/tmp/oig-mcp-before-114")
    if not worktree.exists():
        git = ["git", "-C", str(ROOT), "worktree", "add", "--detach"]
        subprocess.run([*git, str(worktree), commit], check=True)
        (worktree / ".env").symlink_to(ROOT / ".env")
    return worktree


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--arms", default="before,after", help="before, after, no_form")
    parser.add_argument("--before", default="f133d93", help="last commit before #114")
    parser.add_argument("--model", default="claude-opus-5-5")
    parser.add_argument("--effort", default="medium")
    parser.add_argument(
        "--out", default=str(ROOT / "eval/results/2026-11-17-elicitation-ab")
    )
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    head = ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"]
    current = subprocess.run(head, capture_output=True, text=True, check=True)

    arms = args.arms.split(",")
    directories = {"after": ROOT, "no_form": ROOT}
    if "before" in arms:
        directories["before"] = before_worktree(args.before)
    llm = anthropic.AsyncAnthropic()
    results: dict[str, Any] = {
        "question": QUESTION,
        "choice": CHOICE,
        "user_reply": USER_REPLY,
        "model": args.model,
        "effort": args.effort,
        "before_commit": args.before,
        "current_commit": current.stdout.strip(),
        "runs": {},
    }
    for arm in arms:
        runs = []
        for i in range(args.runs):
            run = await one_run(
                directories[arm], llm, args.model, args.effort, form=arm != "no_form"
            )
            print(
                f"{arm} {i + 1}: calls={run['server_calls']} "
                f"requests={run['model_requests']} turns={run['user_turns']} "
                f"tokens={run['tokens']} form={run['form_shown']} "
                f"stations={run['stations_opened']}",
                flush=True,
            )
            runs.append(run)
        results["runs"][arm] = runs
        results[f"summary_{arm}"] = summary(runs)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    name = f"runs-{'-'.join(arms)}.json"
    (out / name).write_text(json.dumps(results, indent=2, default=str))
    print(json.dumps({k: v for k, v in results.items() if k.startswith("summary")}))


if __name__ == "__main__":
    asyncio.run(main())
