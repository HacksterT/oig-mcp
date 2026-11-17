"""The judge model, on watsonx.ai through Phoenix's LiteLLM wrapper."""

from __future__ import annotations

import os
from functools import cache

from dotenv import load_dotenv
from phoenix.evals import LLM

DEFAULT_JUDGE = "meta-llama/llama-3-3-70b-instruct"


def judge_model() -> str:
    return os.getenv("JUDGE_MODEL_WATSONX", DEFAULT_JUDGE)


@cache
def judge_llm() -> LLM:
    """One shared LLM wrapper. LiteLLM reads WATSONX_APIKEY, so the skill's
    WATSONX_API_KEY is mirrored to it; nothing is printed or passed in code."""
    load_dotenv()
    if os.getenv("WATSONX_API_KEY") and not os.getenv("WATSONX_APIKEY"):
        os.environ["WATSONX_APIKEY"] = os.environ["WATSONX_API_KEY"]
    return LLM(provider="litellm", model=f"watsonx/{judge_model()}", temperature=0.0)
