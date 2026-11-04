"""Score answers from an agent outside this harness, using the same gold and judge.

    uv run --group eval python eval/phoenix/score_external.py docs/qna.md \
        --label "DeepSeek V4 Pro 0813 through Hermes Agent" --name <results folder>

The file holds `## Q<n>: question` sections, in the order of QNA_ORDER, each with a
`**Tools used:**` line and an answer ending at `### OBSERVATIONS`. Only the answer is
scored. Tool calls were not observed by this harness, so tool choice rests on the
agent's own log and latency is not measured.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from run_experiment import GOLD_PATH, REPO_ROOT, RESULTS_DIR, metrics_for  # noqa: E402
from scoring import load_index, score_code, score_judge  # noqa: E402

QNA_ORDER = [
    "count-open-total",
    "count-hfi-2026",
    "count-two-states",
    "closure-vba-median",
    "closure-vha-rate",
    "facility-el-paso-oldest",
    "report-el-paso-2026",
    "cluster-top-hfi",
    "search-plain-language",
    "search-peer-actions",
    "brief-el-paso",
    "trend-suicide",
    "behave-ambiguous-facility",
    "behave-unanswerable",
    "behave-on-time-rate",
    "behave-no-rating",
    "behave-no-prediction",
    "facility-clean-inspection",
]


def parse(path: Path) -> list[dict]:
    """Split the file into scored answers, with the tools each one reports."""
    text = path.read_text()
    sections = re.split(r"^## Q\d+:.*$", text, flags=re.M)[1:]
    if len(sections) != len(QNA_ORDER):
        raise SystemExit(f"Expected {len(QNA_ORDER)} questions, found {len(sections)}.")
    runs = []
    for gold_id, section in zip(QNA_ORDER, sections):
        body = re.split(r"^---\s*$", section, flags=re.M)[0]
        answer = body.split("### OBSERVATIONS")[0]
        tools_line = re.search(r"\*\*Tools used:\*\*(.*)", answer)
        reported = tools_line.group(1) if tools_line else ""
        # "none that answer it" means no tool was used to answer, whatever it names.
        tools = (
            []
            if reported.strip().startswith("none")
            else re.findall(r"vaoig_\w+", reported)
        )
        answer = re.sub(r"\*\*Tools used:\*\*.*\n", "", answer).strip()
        runs.append(
            {
                "id": gold_id,
                "answer": answer,
                "tool_calls": [
                    {"tool": tool, "is_error": False} for tool in dict.fromkeys(tools)
                ],
            }
        )
    return runs


async def main_async(args) -> None:
    load_dotenv(REPO_ROOT / ".env")
    gold = {q["id"]: q for q in json.loads(GOLD_PATH.read_text())["questions"]}
    numbers, urls = load_index()
    llm = anthropic.AsyncAnthropic(max_retries=5)
    records = []
    for run in parse(Path(args.path)):
        question = gold[run["id"]]
        score = score_code(question, run, numbers, urls)
        score["judge"] = await score_judge(question, run, llm, args.judge_model)
        records.append(
            {
                "id": run["id"],
                "category": question["category"],
                "run": run,
                "score": score,
                "metrics": metrics_for(score),
            }
        )
    out_dir = RESULTS_DIR / args.name
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "records.json").write_text(json.dumps(records, indent=1))

    def share(key: str) -> str:
        values = [r["metrics"][key] for r in records if r["metrics"][key] is not None]
        return f"{sum(map(bool, values))} of {len(values)}"

    criteria = [c for r in records for c in r["score"]["judge"]["criteria"]]
    lines = [
        f"# External run: {args.label}",
        "",
        f"{len(records)} of the gold questions, judged by `{args.judge_model}`. Tool "
        "use is as the agent reported it. The answers were written into an artifact in "
        "a format the operator set, unlike the isolated harness runs.",
        "",
        "| Measure | Result |",
        "|---|---|",
        f"| Questions passing every check | {share('passed')} |",
        f"| Exact facts present | {share('exact_match')} |",
        f"| Agrees with the gold reference | {share('judge_agrees')} |",
        f"| Tool selection, as reported | {share('tool_selection')} |",
        f"| Caveats and behaviors | {sum(c['passed'] for c in criteria)} of {len(criteria)} |",
        f"| Every cited report number and link exists | {share('citation_integrity')} |",
        "| Report number and link given where required | "
        + f"{sum(r['score']['citation_present'] is True for r in records)} of "
        + f"{sum(r['score']['citation_present'] is not None for r in records)} |",
        "| Data date stated where required | "
        + f"{sum(r['score']['data_date_stated'] is True for r in records)} of "
        + f"{sum(r['score']['data_date_stated'] is not None for r in records)} |",
        "",
        "## What failed",
        "",
    ]
    for record in records:
        score = record["score"]
        problems = [
            f"missing fact: {c['label']}" for c in score["checks"] if not c["passed"]
        ]
        if score["report_list"] and not score["report_list"]["passed"]:
            problems.append(f"list: {score['report_list']}")
        if score["tools_pass"] is False:
            problems.append(f"tools: {score['tools_called']}")
        if not score["judge"]["agrees_with_reference"]:
            problems.append(f"judge: {score['judge']['reason']}")
        problems += [
            f"caveat: {c['reason']}"
            for c in score["judge"]["criteria"]
            if not c["passed"]
        ]
        if score["unknown_numbers"] or score["unknown_urls"]:
            problems.append(
                f"unknown: {score['unknown_numbers'] + score['unknown_urls']}"
            )
        if score["citation_present"] is False:
            problems.append("no report number and link together")
        if score["data_date_stated"] is False:
            problems.append("data date not stated")
        if problems:
            lines.append(f"- **{record['id']}**: " + "; ".join(problems))
    summary = "\n".join(lines) + "\n"
    (out_dir / "summary.md").write_text(summary)
    print(summary)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path")
    parser.add_argument("--label", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--judge-model", default="claude-opus-5-5")
    asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    main()
