"""Score the Orchestrate agent's answers with this repo's gold, the way the harness does.

    uv run --group eval python eval/orchestrate/score_runs.py eval/results/<folder>

The folder holds one `run-<n>` folder per ADK run, each with the ADK's
`messages/<test>.messages.json` transcripts. For every transcript this scores the
agent's first reply to the question, with the tool calls made before it: that is the
answer a single-turn harness run would have produced. Later turns are driven by the
ADK's simulated user and are recorded, not scored. Each run gets a records.json in the
harness format, so `eval/phoenix/rejudge_watsonx.py` can judge it again, and the
folder gets a summary.md across runs. No calls are made to the MCP server or the
data API; the judge is the same Claude judge and prompt as the harness.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import anthropic
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "eval" / "phoenix"))
from run_experiment import metrics_for  # noqa: E402
from scoring import load_gold, load_index, score_code, score_judge  # noqa: E402


def first_reply(messages: list[dict]) -> dict:
    """The agent's first text reply, the tool calls before it, and what followed."""
    calls, pending, answer, turns = [], {}, None, 0
    for message in messages:
        if message["role"] == "user":
            turns += 1
            continue
        if answer is not None:
            continue
        if message["type"] == "tool_call":
            for call in message["tool_calls"] or []:
                pending[call["id"]] = {
                    "tool": call["function"]["name"],
                    "args": json.loads(call["function"]["arguments"] or "{}"),
                    "is_error": False,
                }
                calls.append(pending[call["id"]])
        elif message["type"] == "tool_response":
            content = json.loads(message["content"])
            body = str(content.get("content", ""))
            call = pending.get(content.get("tool_call_id"))
            if call is not None:
                call["is_error"] = '"error"' in body or "Error Details" in body
                call["error"] = body[:300] if call["is_error"] else None
        elif message["type"] == "text":
            answer = message["content"]
    return {
        "answer": answer or "",
        "tool_calls": calls,
        "user_turns": turns,
        "replies": sum(
            m["role"] == "assistant" and m["type"] == "text" for m in messages
        ),
    }


def gold_by_test() -> dict:
    gold = load_gold("all")["questions"]
    return {q["id"]: q for q in gold}


async def score_run(
    run_dir: Path, gold: dict, llm, judge_model: str, rejudge: bool
) -> list[dict]:
    numbers, urls = load_index()
    gate = asyncio.Semaphore(4)
    saved = run_dir / "records.json"
    # Rescoring keeps the judge's earlier verdicts unless asked to judge again.
    verdicts = (
        {r["id"]: r["score"]["judge"] for r in json.loads(saved.read_text())}
        if saved.exists() and not rejudge
        else {}
    )

    async def one(path: Path) -> dict:
        test = path.name.split(".")[0]
        question = gold[test]
        run = first_reply(json.loads(path.read_text()))
        score = score_code(question, run, numbers, urls)
        if test in verdicts:
            score["judge"] = verdicts[test]
        else:
            async with gate:
                score["judge"] = await score_judge(question, run, llm, judge_model)
        return {
            "id": test,
            "category": question["category"],
            "run": run,
            "score": score,
            "metrics": metrics_for(score),
        }

    paths = sorted((run_dir / "messages").glob("*.messages.json"))
    records = await asyncio.gather(*(one(p) for p in paths))
    order = list(gold)
    records.sort(key=lambda r: order.index(r["id"]))
    (run_dir / "records.json").write_text(json.dumps(records, indent=1))
    return records


def problems(record: dict) -> list[str]:
    score = record["score"]
    found = [f"missing fact: {c['label']}" for c in score["checks"] if not c["passed"]]
    if score["report_list"] and not score["report_list"]["passed"]:
        found.append(
            f"list: extra {score['report_list']['extra']}, "
            f"missed {score['report_list']['missed']}"
        )
    if score["tools_pass"] is False:
        found.append(f"tools called: {score['tools_called'] or 'none'}")
    if not score["judge"]["agrees_with_reference"]:
        found.append(f"judge: {score['judge']['reason']}")
    found += [
        f"caveat: {c['reason']}" for c in score["judge"]["criteria"] if not c["passed"]
    ]
    if score["unknown_numbers"] or score["unknown_urls"]:
        found.append(
            f"unknown citations: {score['unknown_numbers'] + score['unknown_urls']}"
        )
    if score["citation_present"] is False:
        found.append("no report number and link together")
    if score["data_date_stated"] is False:
        found.append("data date not stated")
    if score["tool_errors"]:
        errors = [c["error"] for c in record["run"]["tool_calls"] if c["is_error"]]
        found.append(f"tool errors before the reply: {errors}")
    return found


def adk_comparison(folder: Path, runs: dict[str, list[dict]]) -> list[str]:
    """Where the ADK's journey success and this scoring disagree, per run."""
    counts = {"both pass": 0, "both fail": 0, "ADK only": 0, "gold only": 0}
    differ = []
    for name, records in sorted(runs.items()):
        path = folder / name / "summary_metrics.csv"
        if not path.exists():
            return []
        with path.open() as handle:
            adk = {
                r["dataset_name"]: r["is_success"] == "True"
                for r in csv.DictReader(handle)
            }
        for record in records:
            ours, theirs = record["metrics"]["passed"], adk.get(record["id"])
            if theirs is None:
                continue
            key = (
                ("both pass" if ours else "both fail")
                if ours == theirs
                else ("ADK only" if theirs else "gold only")
            )
            counts[key] += 1
            if ours != theirs:
                differ.append(
                    f"{record['id']} ({name}): passes {key.replace(' only', '')} only"
                )
    total = sum(counts.values())
    return [
        "",
        "## Against the ADK's journey success",
        "",
        f"Same verdict on {counts['both pass'] + counts['both fail']} of {total}: "
        f"{counts['both pass']} pass both, {counts['both fail']} fail both. "
        f"{counts['ADK only']} pass only the ADK; {counts['gold only']} pass only the "
        "gold scoring. The ADK reads the whole conversation and has no citation or "
        "data date check; this scoring reads the first reply and requires both.",
        "",
        *(f"- {line}" for line in differ),
    ]


def summarize(folder: Path, runs: dict[str, list[dict]], judge_model: str) -> str:
    names = sorted(runs)
    by_test: dict[str, dict[str, dict]] = defaultdict(dict)
    for name in names:
        for record in runs[name]:
            by_test[record["id"]][name] = record

    def share(name: str, key: str) -> str:
        values = [
            r["metrics"][key] for r in runs[name] if r["metrics"][key] is not None
        ]
        return f"{sum(map(bool, values))} of {len(values)}"

    def code_share(name: str, key: str) -> str:
        values = [r["score"][key] for r in runs[name] if r["score"][key] is not None]
        return f"{sum(map(bool, values))} of {len(values)}"

    def criteria_share(name: str) -> str:
        items = [
            c["passed"] for r in runs[name] for c in r["score"]["judge"]["criteria"]
        ]
        return f"{sum(items)} of {len(items)}"

    header = "| Measure | " + " | ".join(names) + " |"
    rule = "|---|" + "---|" * len(names)
    rows = [
        ("Questions passing every check", lambda n: share(n, "passed")),
        ("Exact facts present", lambda n: share(n, "exact_match")),
        ("Agrees with the gold reference", lambda n: share(n, "judge_agrees")),
        ("Tool selection", lambda n: share(n, "tool_selection")),
        ("Caveats and behaviors", criteria_share),
        (
            "Every cited report and link exists",
            lambda n: share(n, "citation_integrity"),
        ),
        (
            "Citation present where required",
            lambda n: code_share(n, "citation_present"),
        ),
        (
            "Data date stated where required",
            lambda n: code_share(n, "data_date_stated"),
        ),
    ]
    lines = [
        f"# Orchestrate agent, scored with the gold: {folder.name}",
        "",
        "The watsonx Orchestrate agent's first reply to each question, from the ADK "
        f"transcripts, scored with the harness's code checks and the `{judge_model}` "
        "judge. Later turns, driven by the ADK's simulated user, are not scored.",
        "",
        header,
        rule,
        *(
            f"| {label} | " + " | ".join(fn(n) for n in names) + " |"
            for label, fn in rows
        ),
        "",
        "## By question",
        "",
        "| Question | " + " | ".join(names) + " | Passed |",
        "|---|" + "---|" * (len(names) + 1),
    ]
    mark = {True: "yes", False: "NO"}
    for test, per_run in by_test.items():
        passed = [per_run[n]["metrics"]["passed"] for n in names if n in per_run]
        lines.append(
            f"| {test} | "
            + " | ".join(
                mark[per_run[n]["metrics"]["passed"]] if n in per_run else "-"
                for n in names
            )
            + f" | {sum(passed)} of {len(passed)} |"
        )
    lines += adk_comparison(folder, runs)
    lines += ["", "## What failed", ""]
    for test, per_run in by_test.items():
        for name in names:
            record = per_run.get(name)
            if record and not record["metrics"]["passed"]:
                calls = (
                    ", ".join(
                        f"{c['tool']}({json.dumps(c['args'])[:120]})"
                        for c in record["run"]["tool_calls"]
                    )
                    or "no tool call"
                )
                lines.append(f"- **{test}, {name}**: " + "; ".join(problems(record)))
                lines.append(f"  - Calls before the reply: {calls}")
    return "\n".join(lines) + "\n"


async def main_async(folder: Path, judge_model: str, rejudge: bool) -> int:
    load_dotenv(REPO_ROOT / ".env")
    gold = gold_by_test()
    llm = anthropic.AsyncAnthropic(max_retries=5)
    runs = {}
    for run_dir in sorted(
        p for p in folder.iterdir() if p.is_dir() and p.name.startswith("run-")
    ):
        runs[run_dir.name] = await score_run(run_dir, gold, llm, judge_model, rejudge)
        print(f"{run_dir.name}: scored {len(runs[run_dir.name])}")
    summary = summarize(folder, runs, judge_model)
    (folder / "summary.md").write_text(summary)
    print(summary.split("## By question")[0])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path)
    parser.add_argument("--judge-model", default="claude-opus-5-5")
    parser.add_argument(
        "--rejudge", action="store_true", help="Judge again instead of reusing verdicts"
    )
    args = parser.parse_args()
    return asyncio.run(main_async(args.folder, args.judge_model, args.rejudge))


if __name__ == "__main__":
    sys.exit(main())
