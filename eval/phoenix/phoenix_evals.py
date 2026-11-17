"""Judge saved runs with Phoenix evaluators on a watsonx.ai model, as IBM's skill intends.

    uv run --group eval python eval/phoenix/phoenix_evals.py eval/results/<folder> [...]

For every answer in a results folder (harness runs, or Orchestrate runs with their
ADK transcripts), five arize-phoenix-evals judges run on JUDGE_MODEL_WATSONX
(default meta-llama/llama-3-3-70b-instruct):

- match_expected_response and check_answer_scope, the skill's two judges;
- Phoenix's tool_selection and tool_invocation, on the answer's tool calls;
- Phoenix's tool_response_handling, once per answer, on every tool call it made, their
  full responses, and the final answer.

Tool responses come in full from the ADK transcripts for Orchestrate, and from this
server's traces (logs/traces) for harness runs, matched by tool and arguments. Tool
results are deterministic for the pinned snapshot, so a trace from the same run's
time window is the response the agent saw. Where no trace matches, the saved
1,500-character preview is used and counted. An answer's tool responses are capped at
120,000 characters in all for the judge, shared among its calls.

Writes phoenix_evals.json and phoenix_evals.md into each folder (into each run-N
folder for Orchestrate), and logs each as a Phoenix experiment on the gold dataset,
so the evaluations appear in the Phoenix UI next to the earlier experiments. No call
reaches the MCP server or the data API.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from judges import (  # noqa: E402
    check_answer_scope,
    judge_model,
    match_expected_response,
    tool_invocation,
    tool_response_handling,
    tool_selection,
)
from scoring import load_gold  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
TRACES = REPO_ROOT / "logs" / "traces"
RESULT_CAP = 120_000  # characters of tool responses per answer, for the judge
CONCURRENCY = 6
RUN_WINDOW = timedelta(minutes=75)


# --- Tools offered to the agent -------------------------------------------------


def available_tools() -> str:
    """The server's tools as an agent sees them: name, description, input schema."""
    from fastmcp import Client

    from oig_mcp.app import mcp

    async def listing():
        async with Client(mcp) as client:
            return await client.list_tools()

    lines = []
    for tool in asyncio.run(listing()):
        schema = getattr(tool, "input_schema", None) or tool.inputSchema
        params = {
            name: spec.get("description", "")
            for name, spec in (schema.get("properties") or {}).items()
        }
        lines.append(
            f"- {tool.name}: {' '.join(tool.description.split())}\n"
            f"  parameters: {json.dumps(params)}"
        )
    return "\n".join(lines)


# --- Answers and their tool calls -------------------------------------------------


def _key(tool: str, arguments: dict) -> str:
    return tool + json.dumps(arguments or {}, sort_keys=True)


def trace_index() -> dict[str, list[tuple[datetime, str]]]:
    index: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    for path in TRACES.glob("*/*.json"):
        try:
            trace = json.loads(path.read_text())
            when = datetime.fromisoformat(trace["time"])
        except (ValueError, KeyError, OSError):
            continue
        result = trace.get("result")
        text = result if isinstance(result, str) else json.dumps(result)
        index[_key(trace.get("tool", ""), trace.get("arguments"))].append((when, text))
    return index


def harness_answers(folder: Path, traces: dict) -> tuple[list[dict], int]:
    """Answers from a harness records.json, with full tool responses from traces."""
    records = json.loads((folder / "records.json").read_text())
    end = datetime.fromtimestamp(
        (folder / "records.json").stat().st_mtime, tz=timezone.utc
    )
    previews = 0
    answers = []
    for record in records:
        calls = []
        for call in record["run"]["tool_calls"]:
            candidates = [
                text
                for when, text in traces.get(
                    _key(call["tool"], call.get("arguments")), []
                )
                if end - RUN_WINDOW <= when <= end + timedelta(minutes=2)
            ]
            if candidates:
                result = candidates[0]
            else:
                previews += 1
                result = (call.get("result_preview") or "") + (
                    "\n[Only the first 1,500 characters of this response were saved.]"
                )
            calls.append(
                {
                    "tool": call["tool"],
                    "arguments": call.get("arguments") or {},
                    "result": result,
                }
            )
        answers.append(
            {
                "id": record["id"],
                "answer": record["run"].get("answer") or "",
                "calls": calls,
            }
        )
    return answers, previews


def _content(message: dict):
    content = message.get("content")
    if isinstance(content, str):
        try:
            return json.loads(content)
        except ValueError:
            return content
    return content


def orchestrate_answers(run_dir: Path) -> tuple[list[dict], int]:
    """Answers from ADK transcripts: the calls before the agent's first reply, each
    paired in order with its response, and that first reply."""
    answers = []
    for path in sorted((run_dir / "messages").glob("*.messages.json")):
        messages = json.loads(path.read_text())
        calls, pending, answer = [], [], ""
        for message in messages[1:]:
            kind, content = message.get("type"), _content(message)
            if kind == "tool_call" and isinstance(content, dict):
                call = {
                    "tool": content.get("name"),
                    "arguments": content.get("args") or {},
                    "result": "",
                }
                calls.append(call)
                pending.append(call)
            elif kind == "tool_response" and pending:
                body = content.get("content") if isinstance(content, dict) else content
                pending.pop(0)["result"] = (
                    body if isinstance(body, str) else json.dumps(body)
                )
            elif kind == "text" and message.get("role") == "assistant":
                answer = content if isinstance(content, str) else json.dumps(content)
                break
        answers.append(
            {
                "id": path.name.removesuffix(".messages.json"),
                "answer": answer,
                "calls": calls,
            }
        )
    return answers, 0


# --- Judging ---------------------------------------------------------------------


def _score(s) -> dict:
    return {
        "label": s.label,
        "score": s.score,
        "explanation": (s.explanation or "").strip(),
    }


async def judge(
    answer: dict,
    question: dict,
    tools: str,
    gate: asyncio.Semaphore,
    handling_only: bool = False,
) -> dict:
    async def run(coro):
        async with gate:
            for attempt in range(4):
                try:
                    return _score(await coro())
                except Exception as exc:  # A judge failure is recorded, not fatal.
                    if attempt == 3:
                        return {
                            "label": "error",
                            "score": None,
                            "explanation": type(exc).__name__,
                        }
                    await asyncio.sleep(2**attempt * 3)

    q, out, calls = question["question"], answer["answer"], answer["calls"]
    selected = ", ".join(c["tool"] for c in calls) or "No tool was called."
    invoked = (
        "\n".join(f"{c['tool']}({json.dumps(c['arguments'])})" for c in calls)
        or "No tool was called."
    )
    tasks = {
        "match_expected_response": run(
            lambda: match_expected_response(q, out, question["reference"])
        ),
        "check_answer_scope": run(lambda: check_answer_scope(q, out)),
        "tool_selection": run(lambda: tool_selection(q, tools, selected)),
        "tool_invocation": run(lambda: tool_invocation(q, tools, invoked)),
    }
    if handling_only:
        for pending in tasks.values():
            pending.close()
        tasks = {}
    handling = []
    if calls:
        # One judgment per answer, with every call and its response: an answer
        # combines its calls (Texas from one, North Carolina from another), so a
        # judge shown one call at a time reads the rest as invented.
        budget = max(RESULT_CAP // len(calls), 4_000)
        invoked_all = "\n".join(
            f"{i}. {c['tool']}({json.dumps(c['arguments'])})"
            for i, c in enumerate(calls, 1)
        )
        results_all = "\n\n".join(
            f"[Response to call {i}, {c['tool']}]\n"
            + (c["result"][:budget] or "(empty response)")
            for i, c in enumerate(calls, 1)
        )
        handling = [
            run(lambda: tool_response_handling(q, invoked_all, results_all, out))
        ]
    names = list(tasks)
    done = await asyncio.gather(*tasks.values(), *handling)
    result = dict(zip(names, done[: len(names)]))
    result["tool_response_handling"] = done[len(names) :]
    return {"id": answer["id"], **result}


def rate(rows: list[dict], key: str) -> str:
    values = [r[key]["score"] for r in rows if r[key]["score"] is not None]
    return f"{sum(values):.0f} of {len(values)}" if values else "n/a"


def summarize(name: str, rows: list[dict], previews: int) -> str:
    all_ok = [
        all(h["score"] == 1 for h in r["tool_response_handling"])
        for r in rows
        if r["tool_response_handling"]
    ]
    errors = sum(
        1
        for r in rows
        for k, v in r.items()
        if k != "id"
        for x in (v if isinstance(v, list) else [v])
        if x["label"] == "error"
    )
    lines = [
        f"# Phoenix evaluations: {name}",
        "",
        f"Judged with arize-phoenix-evals on watsonx.ai `{judge_model()}`, as IBM's mcp-eval-wxai skill specifies. "
        "Correctness and scope are the skill's two judges; tool selection, tool invocation, and tool response "
        "handling are Phoenix's built-in tool evaluators.",
        "",
        "| Evaluator | Result |",
        "|---|---|",
        f"| match_expected_response (correct against the gold reference) | {rate(rows, 'match_expected_response')} |",
        f"| check_answer_scope (in scope, or rightly declined) | {rate(rows, 'check_answer_scope')} |",
        f"| tool_selection (right tools for the question) | {rate(rows, 'tool_selection')} |",
        f"| tool_invocation (right arguments) | {rate(rows, 'tool_invocation')} |",
        f"| tool_response_handling (uses its tool responses correctly, invents nothing) | {sum(all_ok)} of {len(all_ok)} answers with tool calls |",
        "",
        f"Tool responses taken from saved previews only: {previews}. Judge errors: {errors}.",
        "",
        "## Not passed",
        "",
    ]
    for r in rows:
        for key in (
            "match_expected_response",
            "check_answer_scope",
            "tool_selection",
            "tool_invocation",
        ):
            if r[key]["score"] == 0:
                lines.append(f"- **{r['id']}**, {key}: {r[key]['explanation'][:300]}")
        for h in r["tool_response_handling"]:
            if h["score"] == 0:
                lines.append(
                    f"- **{r['id']}**, tool_response_handling: {h['explanation'][:300]}"
                )
    return "\n".join(lines) + "\n"


# --- Phoenix experiments -----------------------------------------------------------


def log_to_phoenix(name: str, rows: list[dict], gold: dict) -> None:
    """Record the evaluations as a Phoenix experiment on the gold dataset."""
    from phoenix.client import Client
    from run_experiment import PHOENIX_HOST, PHOENIX_PORT, start_phoenix

    start_phoenix()
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
    by_id = {r["id"]: r for r in rows}

    def task(input):  # noqa: A002 - Phoenix binds this parameter by name.
        return by_id.get(input["id"]) or {"skipped": True}

    def evaluator(key):
        def evaluate(output):
            if not output or output.get("skipped"):
                return {"label": "n/a"}
            if key == "tool_response_handling":
                handled = [h for h in output[key] if h["score"] is not None]
                if not handled:
                    return {"label": "no tool calls"}
                share = sum(h["score"] for h in handled) / len(handled)
                return {
                    "score": share,
                    "label": f"{sum(h['score'] for h in handled):.0f} of {len(handled)} calls",
                }
            value = output[key]
            return {
                "score": value["score"],
                "label": value["label"],
                "explanation": value["explanation"],
            }

        evaluate.__name__ = key
        return evaluate

    keys = (
        "match_expected_response",
        "check_answer_scope",
        "tool_selection",
        "tool_invocation",
        "tool_response_handling",
    )
    client.experiments.run_experiment(
        dataset=dataset,
        task=task,
        evaluators={key: evaluator(key) for key in keys},
        experiment_name=f"phoenix-evals {name}",
        experiment_metadata={"judge_model": f"watsonx/{judge_model()}", "source": name},
        print_summary=False,
    )


# --- Main ----------------------------------------------------------------------------


async def judge_all(answers, questions, tools, handling_only=False):
    gate = asyncio.Semaphore(CONCURRENCY)
    return await asyncio.gather(
        *(
            judge(a, questions[a["id"]], tools, gate, handling_only)
            for a in answers
            if a["id"] in questions
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folders", nargs="+", type=Path)
    parser.add_argument(
        "--no-phoenix", action="store_true", help="Skip logging experiments"
    )
    parser.add_argument(
        "--handling-only",
        action="store_true",
        help="Judge tool_response_handling again, keeping the other saved judgments",
    )
    args = parser.parse_args()
    gold = load_gold("all")
    questions = {q["id"]: q for q in gold["questions"]}
    tools = available_tools()
    traces = trace_index()
    targets = []
    for folder in args.folders:
        runs = sorted(p.parent for p in folder.glob("run-*/messages"))
        if runs:
            targets += [
                (run, f"{folder.name}/{run.name}", orchestrate_answers(run))
                for run in runs
            ]
        else:
            targets.append((folder, folder.name, harness_answers(folder, traces)))
    for out_dir, name, (answers, previews) in targets:
        if args.handling_only:
            saved = {
                r["id"]: r
                for r in json.loads((out_dir / "phoenix_evals.json").read_text())
            }
            fresh = asyncio.run(
                judge_all(answers, questions, tools, handling_only=True)
            )
            rows = [
                {
                    **saved[r["id"]],
                    "tool_response_handling": r["tool_response_handling"],
                }
                for r in fresh
            ]
        else:
            rows = asyncio.run(judge_all(answers, questions, tools))
        (out_dir / "phoenix_evals.json").write_text(json.dumps(rows, indent=1))
        summary = summarize(name, rows, previews)
        (out_dir / "phoenix_evals.md").write_text(summary)
        print("\n".join(summary.splitlines()[:14]), flush=True)
        if not args.no_phoenix:
            log_to_phoenix(name, rows, gold)
    return 0


if __name__ == "__main__":
    sys.exit(main())
