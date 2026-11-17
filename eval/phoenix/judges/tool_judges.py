"""Phoenix's built-in tool evaluators: tool selection, tool invocation, and tool
response handling, each judged by the watsonx.ai model."""

from __future__ import annotations

from phoenix.evals.metrics import (
    ToolInvocationEvaluator,
    ToolResponseHandlingEvaluator,
    ToolSelectionEvaluator,
)

from judges.llm import judge_llm

_cache: dict[str, object] = {}


def _get(kind):
    if kind.__name__ not in _cache:
        _cache[kind.__name__] = kind(llm=judge_llm())
    return _cache[kind.__name__]


async def tool_selection(input: str, available_tools: str, selected: str):  # noqa: A002
    """Were the right tools chosen for the question (or rightly none)?"""
    scores = await _get(ToolSelectionEvaluator).async_evaluate(
        {"input": input, "available_tools": available_tools, "tool_selection": selected}
    )
    return scores[0]


async def tool_invocation(input: str, available_tools: str, invocations: str):  # noqa: A002
    """Were the tools called with correct, complete arguments?"""
    scores = await _get(ToolInvocationEvaluator).async_evaluate(
        {
            "input": input,
            "available_tools": available_tools,
            "tool_selection": invocations,
        }
    )
    return scores[0]


async def tool_response_handling(
    input: str, tool_call: str, tool_result: str, output: str
):  # noqa: A002
    """Did the answer use this tool's response correctly, without inventing data?"""
    scores = await _get(ToolResponseHandlingEvaluator).async_evaluate(
        {
            "input": input,
            "tool_call": tool_call,
            "tool_result": tool_result,
            "output": output or "(no answer)",
        }
    )
    return scores[0]
