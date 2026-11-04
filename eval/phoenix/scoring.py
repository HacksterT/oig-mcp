"""Score one answer against its gold record.

Facts, lists, tool choice, and citations are scored by code, so they are repeatable.
A judge model scores what code cannot: whether required caveats and behaviors are
really there, and whether the answer as a whole agrees with the gold reference.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import anthropic
from pydantic import BaseModel

REPORT_NUMBER = re.compile(r"\b(?:\d{2}-\d{5}-\d{1,4}|\d{4}-\d{5}-[A-Z]{2}-\d{4})\b")
VAOIG_URL = re.compile(r"https?://(?:www\.)?vaoig\.gov/[^\s)\]>\"'`|]+")
GOLD_DIR = Path(__file__).parent.parent / "gold"
# OIG pages the server's own responses link to that are not reports.
KNOWN_PAGES = {
    "https://vaoig.gov/recommendations-all",
    "https://vaoig.gov/reports/data-dashboard",
}
PRICES = {  # Dollars per million tokens: input, output, cache read.
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
}
CACHE_WRITE_MULTIPLIER = 1.25


class CriterionVerdict(BaseModel):
    criterion: int
    passed: bool
    reason: str


class JudgeVerdict(BaseModel):
    agrees_with_reference: bool
    reason: str
    criteria: list[CriterionVerdict]


JUDGE_PROMPT = """You are scoring an AI assistant's answer about VA Office of \
Inspector General (OIG) records, using gold information computed directly from the \
data.

<question>{question}</question>

<gold_reference>{reference}</gold_reference>

<answer>{answer}</answer>

<criteria>
{criteria}
</criteria>

Decide two things.

1. agrees_with_reference: true if the answer's facts and conclusion agree with the \
gold reference. Ignore formatting, rounding to a sensible precision, and extra \
accurate context. A list of examples in the reference is not exhaustive unless it \
says so. Set false if the answer states a contradicting fact or omits the fact the \
question asked for.

2. For each numbered criterion, whether the answer meets it. Judge what the answer \
says, not what the assistant could have said. Return one entry per criterion, using \
its number. Return an empty list if there are none.

Keep each reason to one sentence."""


def load_index() -> tuple[set[str], set[str]]:
    index = json.loads((GOLD_DIR / "report_index.json").read_text())
    return set(index["report_numbers"]), set(index["urls"])


def _normalize_url(url: str) -> str:
    return url.rstrip(".,;:*_").replace("://www.", "://").rstrip("/")


def score_code(gold: dict, run: dict, numbers: set[str], urls: set[str]) -> dict:
    """Everything that can be decided without a model."""
    answer = run["answer"]
    called = {call["tool"] for call in run["tool_calls"]}

    checks = [
        {
            "label": check["label"],
            "passed": any(re.search(pattern, answer) for pattern in check["any_of"]),
        }
        for check in gold["checks"]
    ]
    cited_numbers = sorted(set(REPORT_NUMBER.findall(answer)))
    cited_urls = sorted({_normalize_url(url) for url in VAOIG_URL.findall(answer)})
    known_urls = {_normalize_url(url) for url in urls} | KNOWN_PAGES

    report_list = None
    if gold["report_list"]:
        expected = set(gold["report_list"]["gold"])
        hits = expected & set(cited_numbers)
        precision = len(hits) / len(cited_numbers) if cited_numbers else 0.0
        recall = len(hits) / len(expected)
        if gold["report_list"]["mode"] == "exact":
            passed = hits == expected and len(cited_numbers) == len(expected)
        else:
            passed = len(hits) >= gold["report_list"]["min_hits"]
        report_list = {
            "mode": gold["report_list"]["mode"],
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "passed": passed,
            "extra": sorted(set(cited_numbers) - expected),
            "missed": sorted(expected - set(cited_numbers))
            if gold["report_list"]["mode"] == "exact"
            else [],
        }

    required = gold["required_tools"]
    return {
        "checks": checks,
        "exact_pass": all(c["passed"] for c in checks) if checks else None,
        "report_list": report_list,
        "tools_pass": all(called & set(group) for group in required)
        if required
        else None,
        "tools_called": sorted(called),
        "tool_errors": sum(call["is_error"] for call in run["tool_calls"]),
        "cited_numbers": cited_numbers,
        "unknown_numbers": [n for n in cited_numbers if n not in numbers],
        "cited_urls": cited_urls,
        "unknown_urls": [u for u in cited_urls if u not in known_urls],
        "citation_present": bool(cited_numbers and cited_urls)
        if gold["requires_citation"]
        else None,
        "data_date_stated": bool(
            re.search(
                r"2026-11-04|(?:November|Nov\.?)\s+4,?\s+2026|4\s+November\s+2026"
                r"|11/4/2026",
                answer,
            )
        )
        if gold["requires_data_date"]
        else None,
    }


async def score_judge(
    gold: dict, run: dict, llm: anthropic.AsyncAnthropic, model: str
) -> dict:
    """Ask the judge model about agreement with the reference, and the criteria."""
    criteria = "\n".join(
        f"{number}. {text}" for number, text in enumerate(gold["criteria"], 1)
    )
    prompt = JUDGE_PROMPT.format(
        question=gold["question"],
        reference=gold["reference"],
        answer=run["answer"] or "(no answer)",
        criteria=criteria or "(none)",
    )
    response = await llm.messages.parse(
        model=model,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
        output_format=JudgeVerdict,
        output_config={"effort": "high"},
    )
    verdict = response.parsed_output
    by_number = {item.criterion: item for item in verdict.criteria}
    outcomes = []
    for number, text in enumerate(gold["criteria"], 1):
        item = by_number.get(number)
        outcomes.append(
            {
                "criterion": text,
                "passed": bool(item and item.passed),
                "reason": item.reason if item else "The judge did not score this.",
            }
        )
    return {
        "agrees_with_reference": verdict.agrees_with_reference,
        "reason": verdict.reason,
        "criteria": outcomes,
        "usage": {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
        },
    }


def question_passed(score: dict) -> bool:
    """A question passes only if every scored dimension passed."""
    gates = [
        score["exact_pass"],
        score["report_list"]["passed"] if score["report_list"] else None,
        score["tools_pass"],
        score["citation_present"],
        score["data_date_stated"],
        score["judge"]["agrees_with_reference"],
        not score["unknown_numbers"],
        not score["unknown_urls"],
    ]
    gates.extend(item["passed"] for item in score["judge"]["criteria"])
    return all(gate for gate in gates if gate is not None)


def cost(usage: dict, model: str) -> float:
    """Estimated dollars at list prices for one model's token counts."""
    if model not in PRICES:
        return 0.0
    input_price, output_price, cache_read = PRICES[model]
    return (
        usage.get("input", 0) * input_price
        + usage.get("output", 0) * output_price
        + usage.get("cache_read", 0) * cache_read
        + usage.get("cache_write", 0) * input_price * CACHE_WRITE_MULTIPLIER
    ) / 1_000_000
