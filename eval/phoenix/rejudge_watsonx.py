"""Judge saved answers again with a watsonx.ai model, and compare with the Claude judge.

    uv run --group eval python eval/phoenix/rejudge_watsonx.py eval/results/<run> [...]

IBM's mcp-eval-wxai skill judges answers with a watsonx.ai model. This asks a
watsonx.ai judge (Llama 3.3 70B by default, the skill's default) the same question
the Claude judge was asked, with the same prompt: does the answer agree with the gold
reference, and does it meet each criterion. It reads each run's records.json, makes
no calls to the MCP server or the data API, and writes judge_watsonx.json and
judge-comparison.md beside it. Code checks are not repeated; they do not depend on
the judge.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent))
from scoring import JUDGE_PROMPT, JudgeVerdict, load_gold, question_passed  # noqa: E402
from watsonx import DEFAULT_MODEL, WatsonxChat, WatsonxError  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]

JSON_INSTRUCTIONS = """

Reply with one JSON object and nothing else, in exactly this shape:
{"agrees_with_reference": true or false, "reason": "one sentence",
 "criteria": [{"criterion": 1, "passed": true or false, "reason": "one sentence"}]}"""


def parse_verdict(text: str) -> JudgeVerdict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in the reply")
    return JudgeVerdict.model_validate(json.loads(match.group(0)))


async def judge(chat: WatsonxChat, model: str, gold: dict, answer: str) -> dict:
    criteria = "\n".join(f"{n}. {text}" for n, text in enumerate(gold["criteria"], 1))
    prompt = (
        JUDGE_PROMPT.format(
            question=gold["question"],
            reference=gold["reference"],
            answer=answer or "(no answer)",
            criteria=criteria or "(none)",
        )
        + JSON_INSTRUCTIONS
    )
    messages = [{"role": "user", "content": prompt}]
    usage = {"input": 0, "output": 0}
    for _attempt in range(3):
        response = await chat.chat(model, messages, max_tokens=1500)
        used = response.get("usage") or {}
        usage["input"] += used.get("prompt_tokens", 0)
        usage["output"] += used.get("completion_tokens", 0)
        text = response["choices"][0]["message"].get("content") or ""
        try:
            verdict = parse_verdict(text)
            break
        except (ValueError, json.JSONDecodeError, ValidationError) as exc:
            messages += [
                {"role": "assistant", "content": text},
                {
                    "role": "user",
                    "content": f"That was not valid ({exc}). Reply with the JSON object only.",
                },
            ]
    else:
        return {"error": "no valid verdict after three tries", "usage": usage}
    by_number = {item.criterion: item for item in verdict.criteria}
    return {
        "agrees_with_reference": verdict.agrees_with_reference,
        "reason": verdict.reason,
        "criteria": [
            {
                "criterion": text,
                "passed": bool(by_number.get(n) and by_number[n].passed),
                "reason": by_number[n].reason if n in by_number else "Not scored.",
            }
            for n, text in enumerate(gold["criteria"], 1)
        ],
        "usage": usage,
    }


def share(values: list[bool]) -> str:
    return f"{sum(values)} of {len(values)}" if values else "n/a"


def compare(folder: Path, records: list[dict], ibm: dict, model: str) -> str:
    rows, agree_ref, agree_crit, agree_pass = [], [], [], []
    claude_pass, ibm_pass = [], []
    for record in records:
        verdict = ibm.get(record["id"]) or {}
        if "agrees_with_reference" not in verdict:
            rows.append(f"| {record['id']} | - | - | - | - | judge error |")
            continue
        claude = record["score"]["judge"]
        swapped = {**record["score"], "judge": verdict}
        passed_c = question_passed(record["score"])
        passed_i = question_passed(swapped)
        claude_pass.append(passed_c)
        ibm_pass.append(passed_i)
        agree_ref.append(
            claude["agrees_with_reference"] == verdict["agrees_with_reference"]
        )
        for a, b in zip(claude["criteria"], verdict["criteria"], strict=False):
            agree_crit.append(a["passed"] == b["passed"])
        agree_pass.append(passed_c == passed_i)
        mark = {True: "yes", False: "NO"}
        note = "" if passed_c == passed_i else verdict["reason"]
        rows.append(
            f"| {record['id']} | {mark[claude['agrees_with_reference']]} "
            f"| {mark[verdict['agrees_with_reference']]} | {mark[passed_c]} "
            f"| {mark[passed_i]} | {note} |"
        )
    lines = [
        f"# Judge comparison: {folder.name}",
        "",
        f"The same answers, judged by the Claude judge recorded in the run and by "
        f"`{model}` on IBM watsonx.ai with the same prompt. Code checks are the same "
        "for both, so only the judged parts can differ.",
        "",
        "| Measure | Claude judge | watsonx.ai judge | Agreement |",
        "|---|---|---|---|",
        f"| Questions passing every check | {share(claude_pass)} | {share(ibm_pass)} "
        f"| {share(agree_pass)} |",
        f"| Agrees with the gold reference | "
        f"{share([r['score']['judge']['agrees_with_reference'] for r in records])} | "
        f"{share([v['agrees_with_reference'] for v in ibm.values() if 'agrees_with_reference' in v])} "
        f"| {share(agree_ref)} |",
        f"| Criteria verdicts | | | {share(agree_crit)} |",
        "",
        "| Question | Claude: agrees | watsonx: agrees | Claude: passes | watsonx: passes "
        "| watsonx reason, where the pass differs |",
        "|---|---|---|---|---|---|",
        *rows,
        "",
    ]
    return "\n".join(lines)


async def main_async(folders: list[Path], model: str, concurrency: int) -> int:
    load_dotenv(REPO_ROOT / ".env")
    gold = {q["id"]: q for q in load_gold("all")["questions"]}
    try:
        chat = WatsonxChat()
    except WatsonxError as exc:
        print(exc)
        return 2
    gate = asyncio.Semaphore(concurrency)
    try:
        for folder in folders:
            records = json.loads((folder / "records.json").read_text())

            async def one(record: dict) -> tuple[str, dict]:
                async with gate:
                    try:
                        verdict = await judge(
                            chat, model, gold[record["id"]], record["run"]["answer"]
                        )
                    except WatsonxError as exc:
                        verdict = {"error": str(exc)}
                return record["id"], verdict

            ibm = dict(await asyncio.gather(*(one(r) for r in records)))
            (folder / "judge_watsonx.json").write_text(
                json.dumps({"judge_model": model, "verdicts": ibm}, indent=1)
            )
            report = compare(folder, records, ibm, model)
            (folder / "judge-comparison.md").write_text(report)
            print(report.split("\n\n| Question")[0], "\n")
    finally:
        await chat.aclose()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folders", nargs="+", type=Path)
    parser.add_argument("--judge-model", default=DEFAULT_MODEL)
    parser.add_argument("--concurrency", type=int, default=3)
    args = parser.parse_args()
    return asyncio.run(main_async(args.folders, args.judge_model, args.concurrency))


if __name__ == "__main__":
    sys.exit(main())
