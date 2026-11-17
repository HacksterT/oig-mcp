"""LLM-as-judge evaluators built with arize-phoenix-evals, as IBM's mcp-eval-wxai skill
specifies, judged by a watsonx.ai model.

- `match_expected_response`: the answer against the gold reference (the skill's
  correctness judge).
- `check_answer_scope`: answered in scope, or refused what is out of scope (the
  skill's relevance judge).
- `tool_selection`, `tool_invocation`, `tool_response_handling`: Phoenix's built-in
  tool evaluators, for the right tool, the right arguments, and correct use of what
  the tool returned.

The judge model is JUDGE_MODEL, by default the skill's meta-llama/llama-3-3-70b-instruct,
reached through LiteLLM's watsonx provider with WATSONX_URL, WATSONX_API_KEY, and
WATSONX_PROJECT_ID from `.env`.
"""

from judges.correctness_judge import match_expected_response
from judges.llm import judge_llm, judge_model
from judges.scope_judge import check_answer_scope
from judges.tool_judges import tool_invocation, tool_response_handling, tool_selection

__all__ = [
    "check_answer_scope",
    "judge_llm",
    "judge_model",
    "match_expected_response",
    "tool_invocation",
    "tool_response_handling",
    "tool_selection",
]
