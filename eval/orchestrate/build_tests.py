"""Turn the 24 gold questions into watsonx Orchestrate evaluation test cases.

Each test case asks the gold question as written and expects:
- a call to the required tool, when the gold question names exactly one tool per
  step. Orchestrate test cases cannot express "either of these tools", so a gold
  question that accepts alternatives checks only the answer text.
- an answer that contains the gold keywords and matches the gold reference.
- each gold criterion, and the citation and data-date rules, as an assert_llm
  check judged against the final answer.
Tool arguments are not compared ({"IGNORE": null}): the agent's wording of an
argument varies between runs, and the answer is what is scored.

    python eval/orchestrate/build_tests.py [--agent NAME] [--toolkit NAME]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "eval" / "gold" / "questions.json"
OUT = Path(__file__).resolve().parent / "tests"

STORY = (
    "You work in VA patient safety and quality and use an assistant connected to "
    "VA OIG data. You want a sourced answer to your question. If the assistant "
    "asks a clarifying question, answer briefly and stay on the original question."
)
STORY_EXTRA = {
    "behave-ambiguous-facility": (
        " You do not know the exact facility name. If asked which facility, say you "
        "want to know which facilities match before choosing."
    ),
}

# Checks written as patterns that do not reduce to plain text, given by hand.
KEYWORDS = {
    "closure-vha-rate": ["0.28%"],
    "list-top-offices": ["VHA: 426", "OIT: 57", "VBA: 43"],
    "brief-el-paso": ["4 open recommendations", "test results"],
    "report-el-paso-2026": ["2 recommendations", "concurred", "January 29, 2027"],
    "cluster-top-hfi": ["21", "112", "test results"],
}


def literal(pattern: str) -> str | None:
    """A gold check pattern as plain text, or None if it is not a simple literal."""
    text = pattern.replace("(?i)", "")
    text = re.sub(r"\(\?<?[=!][^()]*\)", "", text)  # lookarounds
    text = text.replace(r"\s+", " ").replace(",?", ",").replace(r"\.?", ".")
    text = text.replace(r"\-", "-").replace(r"\.", ".")
    if re.search(r"[\[\](){}|*+?^$\\]", text):
        return None
    return text.strip() or None


def keywords(question: dict) -> list[str]:
    if question["id"] in KEYWORDS:
        return KEYWORDS[question["id"]]
    found = []
    for check in question["checks"]:
        options = [lit for p in check["any_of"] if (lit := literal(p))]
        if options:
            # Prefer the most specific form ("November 4, 2026" over "2026").
            found.append(max(options, key=len))
    report_list = question.get("report_list") or {}
    if report_list.get("mode") == "exact":
        found += report_list["gold"]
    return found


def policy_checks(question: dict) -> list[str]:
    """The gold criteria, plus the citation and data-date rules our scoring uses."""
    checks = list(question["criteria"])
    if question.get("requires_citation"):
        checks.append("Cites at least one OIG report number for its findings.")
    if question.get("requires_data_date"):
        checks.append("States the date of the data, such as 'data as of' a date.")
    return checks


def test_case(question: dict, agent: str, toolkit: str, assertions: bool) -> dict:
    steps = question["required_tools"]
    single = steps and all(len(group) == 1 for group in steps)
    details, goals, previous = [], {}, None
    if single:
        for index, (tool,) in enumerate(steps, start=1):
            name = f"{tool}-{index}"
            details.append(
                {
                    "type": "tool_call",
                    "name": name,
                    "tool_name": f"{toolkit}:{tool}",
                    "args": {"IGNORE": None},
                }
            )
            if previous:
                goals[previous] = [name]
            previous = name
    details.append(
        {
            "type": "text",
            "name": "summarize",
            "response": question["reference"],
            "keywords": keywords(question),
        }
    )
    if assertions:
        details += [
            {
                "type": "assert_llm",
                "kind": "policy",
                "check": check,
                "scope": "response",
            }
            for check in policy_checks(question)
        ]
    if previous:
        goals[previous] = ["summarize"]
    else:
        goals["summarize"] = []
    return {
        "dataset_name": question["id"],
        "agent": agent,
        "story": STORY + STORY_EXTRA.get(question["id"], ""),
        "starting_sentence": question["question"],
        "goals": goals,
        "goal_details": details,
    }


JUDGE = """\
You are grading answers from an assistant that answers questions with VA Office of
Inspector General (OIG) data tools. For each test you get the question, the
expected answer, and sometimes extra criteria.

Pass the answer only if all of these hold:
1. Every number, date, and report number in the expected answer appears in the
   answer. Formatting may differ (2026-11-04 and November 4, 2026 are the same).
   When the expected answer lists report numbers, the answer may list a subset
   only if the question asks for examples.
2. It meets every extra criterion given for the test.
3. It cites an OIG report number for any finding it describes, and states the
   data date when it gives counts.
4. It does not rate or rank facilities, present target dates as missed
   deadlines, or predict what OIG will find.

Extra correct detail is fine. A wrong number is a fail even if the rest is good.
Reply with PASS or FAIL and one sentence naming the deciding reason."""


def bank_markdown(questions: list[dict]) -> str:
    """The test bank as a page to work from in the Orchestrate UI."""
    lines = [
        "# Test bank for the Orchestrate UI",
        "",
        "Generated by `build_tests.py` from `eval/gold/questions.json`. Ask each",
        "question in a new chat, save it as a test, and give the judge the",
        "expected answer and criteria shown. Data as of 2026-11-04.",
        "",
        "## Judge instructions",
        "",
        "Paste into the LLM judge. Keep verbosity low: a verdict and one reason.",
        "",
        "```text",
        JUDGE,
        "```",
        "",
    ]
    for number, question in enumerate(questions, start=1):
        lines += [
            f"## {number}. {question['id']}",
            "",
            f"**Ask:** {question['question']}",
            "",
            f"**Expected answer:** {question['reference']}",
            "",
        ]
        checks = policy_checks(question)
        if checks:
            lines += ["**Criteria:**", ""] + [f"- {c}" for c in checks] + [""]
        tools = " then ".join(
            " or ".join(group) for group in question["required_tools"]
        )
        lines += [f"**Tool expected:** {tools or 'none needed'}", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--agent", default="gsa-oig-assist-TES")
    parser.add_argument("--toolkit", default="oig_mcp_TES")
    parser.add_argument(
        "--no-assert",
        action="store_true",
        help="leave out assert_llm checks, for evaluation framework versions without them",
    )
    args = parser.parse_args()

    questions = json.loads(GOLD.read_text())["questions"]
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    for number, question in enumerate(questions, start=1):
        case = test_case(question, args.agent, args.toolkit, not args.no_assert)
        path = OUT / f"{number:02d}-{question['id']}.json"
        path.write_text(json.dumps(case, indent=2) + "\n")
    bank = OUT.parent / "test-bank.md"
    bank.write_text(bank_markdown(questions))
    print(f"Wrote {len(questions)} test cases to {OUT.relative_to(ROOT)}")
    print(f"Wrote the UI test bank to {bank.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
