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

# The argument on each question's critical path: a wrong value means a wrong
# answer. Everything else is set to Ignored. Fuzzy where the server accepts more
# than one form (labels or slugs, names or cities, codes or state names).
CRITICAL_ARGS = {
    "count-open-total": [
        ("filters.status", "Exact", '["open"], if the agent used the analysis tool'),
    ],
    "count-hfi-2026": [
        ("filters.report_type", "Fuzzy", "healthcare-facility-inspection")
    ],
    "count-peak-year": [("group_by", "Exact", "year")],
    "count-two-states": [
        ("filters.state", "Fuzzy", "Texas, then North Carolina"),
        ("filters.status", "Exact", '["open"]'),
    ],
    "trend-suicide": [("keywords", "Fuzzy", "suicide"), ("group_by", "Exact", "year")],
    "closure-vba-median": [
        ("filters.action_office", "Fuzzy", "VBA or Veterans Benefits Administration")
    ],
    "closure-vha-rate": [
        ("filters.action_office", "Fuzzy", "VHA or Veterans Health Administration")
    ],
    "aging-oit": [
        ("filters.action_office", "Fuzzy", "OIT or Information and Technology"),
        ("filters.status", "Exact", '["open"]'),
    ],
    "list-top-offices": [
        ("group_by", "Exact", "office"),
        ("filters.status", "Exact", '["open"]'),
    ],
    "facility-el-paso-counts": [("facility", "Fuzzy", "El Paso")],
    "facility-el-paso-oldest": [("facility", "Fuzzy", "El Paso")],
    "facility-el-paso-next": [("facility", "Fuzzy", "El Paso")],
    "facility-clean-inspection": [("facility", "Fuzzy", "North Texas")],
    "list-durham-inspections": [("facility", "Fuzzy", "Durham")],
    "report-el-paso-2026": [("report_number", "Exact", "25-00193-155")],
    "cluster-top-hfi": [
        ("report_type", "Fuzzy", "healthcare-facility-inspection, on the clusters tool")
    ],
    "search-plain-language": [("question", "Fuzzy", "medication carts left unlocked")],
    "search-peer-actions": [("question", "Fuzzy", "securing medication carts")],
    "brief-el-paso": [("facility", "Fuzzy", "El Paso")],
    "behave-ambiguous-facility": [("facility", "Fuzzy", "New York")],
    "behave-unanswerable": [("facility", "Fuzzy", "Durham, if the agent looked it up")],
    "behave-no-prediction": [
        ("facility", "Fuzzy", "El Paso, if the agent looked it up")
    ],
}

# Summaries for the UI where the gold reference names examples that a correct
# answer may not repeat, which text match would count against it.
UI_SUMMARY = {
    "behave-ambiguous-facility": (
        "Several VA facilities match 'New York VA'. The answer says so, lists "
        "matching facilities, and asks which one is meant, rather than choosing one."
    ),
}

UI_CONTEXT = {
    "behave-ambiguous-facility": (
        "You want to know what OIG has found at a New York VA facility but do not "
        "know its exact name. If asked which facility, say you want to know which "
        "facilities match before choosing."
    ),
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
                "kind": "observed",
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


# The agent's only instruction, set in Orchestrate. Recorded here so every run
# states what it measured. Domain behavior stays in the server's tools.
AGENT_INSTRUCTIONS = (
    "Answer only from what the OIG tools return. Do not use general knowledge or "
    "information outside the tool results."
)

# Single-criterion judges for Orchestrate's custom LLM-as-a-Judge metrics. IBM
# scores them 1 for pass and 0 for fail, and each reads the agent's response.
JUDGES = {
    "Cites its findings": """\
You are judging a response from an assistant that answers questions with VA Office
of Inspector General (OIG) data tools. Judge only whether findings are cited.
Return 1 if every OIG finding, recommendation, or report the response describes
has its OIG report number (for example 25-00193-155), or if the response describes
no specific findings (for example, it gives only counts or explains why a question
cannot be answered).
Return 0 if it describes any finding, recommendation, or report without its report
number.""",
    "States the data date": """\
You are judging a response from an assistant that answers questions with VA OIG
data tools. Judge only whether the data date is stated.
Return 1 if the response states the date of the data (for example "as of
November 4, 2026"), or if it gives no counts, totals, percentages, or statuses.
Return 0 if it gives counts, totals, percentages, or statuses without the data
date.""",
    "Stays within the data": """\
You are judging a response from an assistant that answers questions with VA OIG
data tools. Judge only whether it claims more than the data supports.
Return 0 if any of the following are true:
- It rates, ranks, or labels a facility or person as better or worse than others.
- It presents target dates as missed deadlines, or gives an on-time rate or a
  share of recommendations that missed their targets.
- It predicts what OIG will find or cite.
- It gives a next inspection date without calling it an estimate.
Return 1 otherwise.""",
    "Concise (informational)": """\
You are an AI assistant trained to judge if a response is longer than it needs to
be and uses excess verbiage. Evaluate the response based on the efficiency of
communications, not correctness, helpfulness, or writing quality.
Caveats, notices, the data date, report numbers, links, and statements of what
the data cannot show are required content and never count as excess.
Return 0 if any of the following are true:
- The response repeats the same idea multiple times.
- The response contains unnecessary explanations that do not add meaningful
  content.
Return 1 otherwise.""",
}


REPORT_NUMBER = re.compile(r"\d{2}-\d{5}-\d+")
DATE = re.compile(
    r"\d{4}-\d{2}-\d{2}|\b(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\b"
)


def ui_keywords(question: dict) -> list[str]:
    """Keywords for the UI, where every one must appear in the answer.

    Only values the agent cannot word differently: report numbers and whole
    numbers from 10 to 999. Dates, percentages, thousands, and words vary
    ("January 29, 2027" or "2027-01-29"), so the response summary covers them.
    """
    found = []
    for word in keywords(question):
        if DATE.search(word):
            continue
        for token in re.findall(r"\d{2}-\d{5}-\d+|\b\d+(?:[.,]\d+)*\b", word):
            if REPORT_NUMBER.fullmatch(token) or (
                token.isdigit() and 10 <= int(token) <= 999
            ):
                if token not in found:
                    found.append(token)
    return found


def bank_markdown(questions: list[dict]) -> str:
    """The test bank as a page to work from in the Orchestrate UI."""
    lines = [
        "# Test bank for the Orchestrate UI",
        "",
        "Generated by `build_tests.py` from `eval/gold/questions.json`. Data as of",
        '2026-11-04. Field names follow IBM\'s "Managing test cases and evaluations".',
        "",
        "## For each question",
        "",
        "1. Ask it in the preview chat, exactly as written, and click **Save as test**.",
        "2. **Response summary:** replace the generated text with the block below and",
        "   turn on its evaluation toggle. Text match compares the answer with it;",
        "   with the toggle off, text match shows as not applicable.",
        "3. **Tool calls:** the tool chosen is always checked. Set the parameter",
        "   on the question's critical path as shown under Tool parameters, and",
        "   everything else to **Ignored**. If the agent used a different valid",
        "   tool than the one listed, set its matching argument the same way.",
        "   Keep only the tool calls listed under Tool expected and delete any",
        "   others the agent made, such as a vaoig_get_dataset_status check. A run",
        "   that skips an optional call is still right, but would fail recall.",
        "   There is no bulk upload: each test is set up on its own.",
        "4. **Advanced options, keywords:** enter the keywords listed, if any. Every",
        "   keyword must appear in the answer for the test to pass, so only values",
        "   the agent cannot word differently are listed.",
        "5. **Conversation context** guides the simulated user if the agent asks a",
        "   follow-up. The generated text is fine unless a different one is given.",
        "",
        "Save a test only from a run whose answer matches the summary: the saved",
        "tool path becomes the standard. Correctness is also scored on the Mac with",
        "the project's own judge and the data API's traces.",
        "",
        "## Agent under test",
        "",
        "Agent `gsa-oig-assist-TES`, toolkit `oig_mcp_TES` (7 tools), and this one",
        "instruction, with no guidelines. Keep it unchanged across runs.",
        "",
        "```text",
        AGENT_INSTRUCTIONS,
        "```",
        "",
        "## Custom LLM-as-a-Judge metrics",
        "",
        "Evaluate tab, Manage metrics, Custom LLM-as-a-Judge, Create: one metric per",
        "block. IBM scores 1 for pass and 0 for fail. Treat Concise as information:",
        "this server is meant to pass on caveats.",
        "",
    ]
    for title, prompt in JUDGES.items():
        lines += [f"### {title}", "", "```text", prompt, "```", ""]
    for number, question in enumerate(questions, start=1):
        summary = UI_SUMMARY.get(question["id"], question["reference"])
        checks = [] if question["id"] in UI_SUMMARY else policy_checks(question)
        if checks:
            summary += " The answer must also: " + " ".join(checks)
        tools = " then ".join(
            " or ".join(group) for group in question["required_tools"]
        )
        words = ui_keywords(question)
        lines += [
            f"## {number}. {question['id']}",
            "",
            f"**Ask:** {question['question']}",
            "",
            "**Response summary:**",
            "",
            "```text",
            summary,
            "```",
            "",
            f"**Keywords:** {', '.join(f'`{w}`' for w in words) if words else 'none'}",
            "",
        ]
        critical = CRITICAL_ARGS.get(question["id"], [])
        if critical:
            settings = "; ".join(
                f"`{name}` **{match}** (saved call should show {value})"
                for name, match, value in critical
            )
            lines += [f"**Tool parameters:** {settings}; everything else Ignored.", ""]
        else:
            lines += ["**Tool parameters:** none critical; set any to Ignored.", ""]
        context = UI_CONTEXT.get(question["id"])
        if context:
            lines += [f"**Conversation context:** {context}", ""]
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
