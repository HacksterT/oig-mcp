"""match_expected_response: is the answer correct against the gold reference?"""

from __future__ import annotations

from phoenix.evals import ClassificationEvaluator

from judges.llm import judge_llm

TEMPLATE = """You are grading an AI assistant's answer to a question about VA Office of \
Inspector General (OIG) reports and recommendations, against a reference answer \
computed directly from the data.

[Question]
{input}

[Reference answer]
{reference}

[Assistant's answer]
{output}

Grade the answer "correct" if every fact the reference requires (numbers, report \
numbers, names, years) appears in the answer with the same value, or the answer \
reaches the same conclusion the reference states. Tolerate formatting differences, \
surrounding prose, extra accurate context, units, rounding of a stated percentage to \
the nearest whole number, and hyphen or dash styles in report numbers. Grade it \
"incorrect" if a required fact is missing, a value differs, or the answer contradicts \
the reference. For a question the reference says cannot be answered from the data, \
the answer is correct if it says so instead of inventing an answer."""

_evaluator = None


def _get() -> ClassificationEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = ClassificationEvaluator(
            name="match_expected_response",
            llm=judge_llm(),
            prompt_template=TEMPLATE,
            choices={"correct": 1, "incorrect": 0},
        )
    return _evaluator


async def match_expected_response(input: str, output: str, reference: str):  # noqa: A002
    """One Score: correct (1) or incorrect (0), with the judge's explanation."""
    scores = await _get().async_evaluate(
        {"input": input, "output": output or "(no answer)", "reference": reference}
    )
    return scores[0]
