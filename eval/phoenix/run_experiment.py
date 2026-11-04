"""Run the gold questions through the assistant, score them, and log to Phoenix.

    uv run --group eval python eval/phoenix/run_experiment.py --url http://127.0.0.1:8000

Needs ANTHROPIC_API_KEY and MCP_AUTH_TOKEN, from the environment or `.env`. Refuses
to run if the server's data differs from the pinned snapshot. Writes records.json
and summary.md under eval/results/, then records the run as a Phoenix experiment with
traces. A Phoenix failure does not lose the results. `--rescore <dir>` scores saved
answers again without calling the assistant.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path
from statistics import mean, median

import anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from agent import preflight, run_question  # noqa: E402
from scoring import (  # noqa: E402
    cost,
    load_index,
    question_passed,
    score_code,
    score_judge,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_PATH = REPO_ROOT / "eval" / "gold" / "questions.json"
RESULTS_DIR = REPO_ROOT / "eval" / "results"
PHOENIX_HOST = "127.0.0.1"
PHOENIX_PORT = 6006
PROJECT = "oig-mcp-eval"


def phoenix_running() -> bool:
    with socket.socket() as probe:
        probe.settimeout(1)
        return probe.connect_ex((PHOENIX_HOST, PHOENIX_PORT)) == 0


def start_phoenix() -> subprocess.Popen | None:
    """Start a local Phoenix unless one is already running."""
    if phoenix_running():
        return None
    working_dir = REPO_ROOT / "eval" / ".phoenix"
    working_dir.mkdir(exist_ok=True)
    log = (working_dir / "server.log").open("a")
    process = subprocess.Popen(
        [sys.executable, "-m", "phoenix.server.main", "serve"],
        env={**os.environ, "PHOENIX_WORKING_DIR": str(working_dir)},
        stdout=log,
        stderr=log,
    )
    for _ in range(60):
        if phoenix_running():
            return process
        time.sleep(1)
    process.terminate()
    raise RuntimeError("Phoenix did not start. See eval/.phoenix/server.log.")


def instrument() -> None:
    from openinference.instrumentation.anthropic import AnthropicInstrumentor
    from phoenix.otel import register

    provider = register(
        project_name=PROJECT,
        endpoint=f"http://{PHOENIX_HOST}:{PHOENIX_PORT}/v1/traces",
        verbose=False,
    )
    AnthropicInstrumentor().instrument(tracer_provider=provider)


def log_experiment(gold: dict, records: list[dict], args, name: str) -> None:
    """Record finished results as a Phoenix experiment, without new model calls."""
    from phoenix.client import Client

    client = Client(base_url=f"http://{PHOENIX_HOST}:{PHOENIX_PORT}")
    dataset_name = f"oig-eval-{gold['snapshot']['sha256'][:12]}"
    try:
        dataset = client.datasets.get_dataset(dataset=dataset_name)
    except Exception:
        dataset = client.datasets.create_dataset(
            name=dataset_name,
            inputs=[
                {"id": q["id"], "question": q["question"]} for q in gold["questions"]
            ],
            outputs=[{"reference": q["reference"]} for q in gold["questions"]],
            metadata=[{"category": q["category"]} for q in gold["questions"]],
            dataset_description="OIG gold questions, answers computed by SQL.",
        )
    by_id = {record["id"]: record for record in records}

    def task(input):  # noqa: A002 - Phoenix binds this parameter by name.
        record = by_id.get(input["id"])
        return record or {"skipped": True}

    def metric(key):
        def evaluate(output):
            value = (output.get("metrics") or {}).get(key)
            return {"score": float(value)} if value is not None else {"label": "n/a"}

        return evaluate

    keys = (
        "passed",
        "exact_match",
        "judge_agrees",
        "list_precision",
        "list_recall",
        "tool_selection",
        "caveats",
        "citation_integrity",
    )
    client.experiments.run_experiment(
        dataset=dataset,
        task=task,
        evaluators={key: metric(key) for key in keys},
        experiment_name=name,
        experiment_metadata={
            "agent_model": args.model,
            "judge_model": args.judge_model,
        },
        print_summary=False,
    )


def metrics_for(score: dict) -> dict:
    """The per-question values that roll up into the summary and Phoenix."""
    criteria = score["judge"]["criteria"]
    report_list = score["report_list"]
    return {
        "passed": question_passed(score),
        "exact_match": score["exact_pass"],
        "judge_agrees": score["judge"]["agrees_with_reference"],
        "list_precision": report_list["precision"] if report_list else None,
        "list_recall": report_list["recall"]
        if report_list and report_list["mode"] == "exact"
        else None,
        "tool_selection": score["tools_pass"],
        "caveats": sum(c["passed"] for c in criteria) / len(criteria)
        if criteria
        else None,
        "citation_integrity": not (score["unknown_numbers"] or score["unknown_urls"]),
    }


def share(values: list) -> str:
    present = [value for value in values if value is not None]
    if not present:
        return "n/a"
    return f"{sum(map(bool, present))} of {len(present)}"


def write_summary(path: Path, gold: dict, records: list[dict], args) -> str:
    rows = [record["metrics"] for record in records]
    criteria = [c for r in records for c in r["score"]["judge"]["criteria"]]
    latencies: dict[str, list[int]] = {}
    for record in records:
        for call in record["run"]["tool_calls"]:
            latencies.setdefault(call["tool"], []).append(call["ms"])
    agent_cost = sum(cost(r["run"]["usage"], args.model) for r in records)
    judge_cost = sum(
        cost(r["score"]["judge"]["usage"], args.judge_model) for r in records
    )
    precision = [r["list_precision"] for r in rows if r["list_precision"] is not None]
    recall = [r["list_recall"] for r in rows if r["list_recall"] is not None]
    categories = Counter(r["category"] for r in records)

    lines = [
        f"# Evaluation run: {args.model}",
        "",
        f"Data snapshot `{gold['snapshot']['sha256'][:16]}`, data as of "
        f"{gold['snapshot']['data_as_of']}. Agent `{args.model}` at effort "
        f"`{args.effort}`, judge `{args.judge_model}`. Run {date.today().isoformat()}.",
        "",
        "| Measure | Result | Scored by |",
        "|---|---|---|",
        f"| Questions passing every check | {share([r['passed'] for r in rows])} | Both |",
        f"| Exact facts present | {share([r['exact_match'] for r in rows])} | Code |",
        f"| Agrees with the gold reference | {share([r['judge_agrees'] for r in rows])} | Judge |",
        f"| List precision, mean | {mean(precision):.2f} | Code |"
        if precision
        else "| List precision | n/a | Code |",
        f"| List recall, exact lists | {mean(recall):.2f} | Code |"
        if recall
        else "| List recall | n/a | Code |",
        f"| Tool selection | {share([r['tool_selection'] for r in rows])} | Code |",
        f"| Caveats and behaviors | {share([c['passed'] for c in criteria])} | Judge |",
        f"| Citation integrity: every cited report and link exists | "
        f"{share([r['citation_integrity'] for r in rows])} | Code |",
        f"| Citation present where required | "
        f"{share([r['score']['citation_present'] for r in records])} | Code |",
        f"| Data date stated where required | "
        f"{share([r['score']['data_date_stated'] for r in records])} | Code |",
        "",
        f"Questions by category: {', '.join(f'{k} {v}' for k, v in sorted(categories.items()))}. "
        f"Estimated cost at list prices: agent ${agent_cost:.2f}, judge ${judge_cost:.2f}.",
        "",
        "## By question",
        "",
        "| Question | Pass | Facts | Judge | Tools | Citations valid | Seconds | Tool calls |",
        "|---|---|---|---|---|---|---|---|",
    ]
    mark = {True: "yes", False: "NO", None: "-"}
    for record in records:
        m = record["metrics"]
        lines.append(
            f"| {record['id']} | {mark[m['passed']]} | {mark[m['exact_match']]} "
            f"| {mark[m['judge_agrees']]} | {mark[m['tool_selection']]} "
            f"| {mark[m['citation_integrity']]} | {record['run']['seconds']} "
            f"| {len(record['run']['tool_calls'])} |"
        )
    lines += [
        "",
        "## Tool latency through the server",
        "",
        "| Tool | Calls | Median ms | Slowest ms |",
        "|---|---|---|---|",
    ]
    for tool, values in sorted(latencies.items()):
        lines.append(
            f"| {tool} | {len(values)} | {median(values):.0f} | {max(values)} |"
        )

    failures = [record for record in records if not record["metrics"]["passed"]]
    if failures:
        lines += ["", "## What failed", ""]
    for record in failures:
        score = record["score"]
        problems = [
            f"missing fact: {c['label']}" for c in score["checks"] if not c["passed"]
        ]
        if score["report_list"] and not score["report_list"]["passed"]:
            problems.append(
                f"list: extra {score['report_list']['extra']}, "
                f"missed {score['report_list']['missed']}"
            )
        if score["tools_pass"] is False:
            problems.append(f"tools called: {score['tools_called']}")
        if not score["judge"]["agrees_with_reference"]:
            problems.append(f"judge: {score['judge']['reason']}")
        problems += [
            f"caveat: {c['reason']}"
            for c in score["judge"]["criteria"]
            if not c["passed"]
        ]
        if score["unknown_numbers"] or score["unknown_urls"]:
            problems.append(
                f"unknown citations: {score['unknown_numbers'] + score['unknown_urls']}"
            )
        if score["citation_present"] is False:
            problems.append("no report number and link together")
        if score["data_date_stated"] is False:
            problems.append("data date not stated")
        lines.append(f"- **{record['id']}**: " + "; ".join(problems))

    text = "\n".join(lines) + "\n"
    path.write_text(text)
    return text


async def answer_all(questions, args, llm, token) -> list[dict]:
    gate = asyncio.Semaphore(args.concurrency)

    async def one(gold: dict) -> dict:
        async with gate:
            try:
                run = await run_question(
                    gold["question"],
                    llm=llm,
                    model=args.model,
                    effort=args.effort,
                    url=args.url,
                    token=token,
                )
            except anthropic.APIError as exc:
                raise SystemExit(f"{gold['id']}: {type(exc).__name__}: {exc}") from exc
        print(
            f"  answered {gold['id']}: {len(run['tool_calls'])} tool calls, "
            f"{run['seconds']}s, stop {run['stop_reason']}",
            flush=True,
        )
        return {"id": gold["id"], "category": gold["category"], "run": run}

    return await asyncio.gather(*(one(gold) for gold in questions))


async def score_all(records, questions, args, llm) -> None:
    numbers, urls = load_index()
    by_id = {gold["id"]: gold for gold in questions}
    gate = asyncio.Semaphore(args.concurrency)

    async def one(record: dict) -> None:
        gold = by_id[record["id"]]
        score = score_code(gold, record["run"], numbers, urls)
        async with gate:
            score["judge"] = await score_judge(
                gold, record["run"], llm, args.judge_model
            )
        record["score"] = score
        record["metrics"] = metrics_for(score)

    await asyncio.gather(*(one(record) for record in records))


async def main_async(args) -> int:
    load_dotenv(REPO_ROOT / ".env")
    token = os.environ.get("MCP_AUTH_TOKEN", "")
    gold = json.loads(GOLD_PATH.read_text())
    questions = [
        q for q in gold["questions"] if not args.only or q["id"] in args.only.split(",")
    ]
    llm = anthropic.AsyncAnthropic(max_retries=5)

    phoenix_process = None
    if not args.no_phoenix:
        try:
            phoenix_process = start_phoenix()
            instrument()
        except Exception as exc:
            print(f"Phoenix is unavailable, continuing without it: {exc}")
            args.no_phoenix = True

    try:
        if args.rescore:
            out_dir = Path(args.rescore)
            saved = json.loads((out_dir / "records.json").read_text())
            records = [
                {key: record[key] for key in ("id", "category", "run")}
                for record in saved
            ]
            kept = {q["id"] for q in questions}
            records = [record for record in records if record["id"] in kept]
        else:
            if not token:
                print("MCP_AUTH_TOKEN must be set.")
                return 2
            await preflight(args.url, token, gold["snapshot"])
            name = args.name or f"{date.today().isoformat()}-{args.model}"
            out_dir = RESULTS_DIR / name
            out_dir.mkdir(parents=True, exist_ok=True)
            print(f"Asking {len(questions)} questions of {args.model}", flush=True)
            records = await answer_all(questions, args, llm, token)
            (out_dir / "records.json").write_text(json.dumps(records, indent=1))

        print(f"Scoring with {args.judge_model}", flush=True)
        await score_all(records, questions, args, llm)
        (out_dir / "records.json").write_text(json.dumps(records, indent=1))
        print(write_summary(out_dir / "summary.md", gold, records, args))
        print(f"Results are in {out_dir}")

        if not args.no_phoenix:
            try:
                log_experiment(gold, records, args, out_dir.name)
                print(f"Phoenix: http://{PHOENIX_HOST}:{PHOENIX_PORT}")
            except Exception as exc:
                print(f"Could not log to Phoenix: {type(exc).__name__}: {exc}")
    finally:
        if phoenix_process and not args.keep_phoenix:
            time.sleep(5)  # Let trace exports finish.
            phoenix_process.terminate()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--model", default=os.getenv("AGENT_MODEL", "claude-opus-5-5"))
    parser.add_argument(
        "--judge-model", default=os.getenv("JUDGE_MODEL", "claude-opus-5-5")
    )
    parser.add_argument("--effort", default=os.getenv("AGENT_EFFORT", "medium"))
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--only", help="Comma-separated question IDs")
    parser.add_argument("--name", help="Results folder name")
    parser.add_argument("--rescore", help="A results folder to score again")
    parser.add_argument("--no-phoenix", action="store_true")
    parser.add_argument("--keep-phoenix", action="store_true")
    return asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
