"""Check watsonx.ai before an evaluation run, as IBM's mcp-eval-wxai skill advises.

    uv run --group eval python eval/phoenix/watsonx_smoke.py [--model MODEL_ID]

Confirms the credentials and project, that the model is listed for tool calling in
this region, a plain chat call, and that the model actually calls a tool. Prints no
credential.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from watsonx import DEFAULT_MODEL, WatsonxChat, WatsonxError  # noqa: E402

ADD_TOOL = {
    "type": "function",
    "function": {
        "name": "add",
        "description": "Add two integers.",
        "parameters": {
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
    },
}


async def main_async(model: str) -> int:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    try:
        chat = WatsonxChat()
    except WatsonxError as exc:
        print(f"FAIL  credentials: {exc}")
        return 2
    try:
        models = await chat.function_calling_models()
        listed = model in models
        print(
            f"{'PASS' if listed else 'WARN'}  {model} listed for tool calling: {listed}"
        )
        if not listed:
            print("      Tool-calling models here:", ", ".join(sorted(models)[:20]))

        reply = await chat.chat(model, [{"role": "user", "content": "Say OK."}])
        text = (reply["choices"][0]["message"].get("content") or "").strip()
        print(f"PASS  chat: {text[:60]!r}")

        reply = await chat.chat(
            model,
            [{"role": "user", "content": "What is 2 plus 4? Use the tool."}],
            [ADD_TOOL],
        )
        calls = reply["choices"][0]["message"].get("tool_calls") or []
        if not calls:
            print("FAIL  tool calling: the model answered without calling the tool")
            return 1
        function = calls[0]["function"]
        raw = function.get("arguments") or "{}"
        arguments = json.loads(raw) if isinstance(raw, str) else raw
        print(f"PASS  tool calling: {function['name']}({arguments})")
        return 0
    except WatsonxError as exc:
        print(f"FAIL  {exc}")
        return 1
    finally:
        await chat.aclose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return asyncio.run(main_async(parser.parse_args().model))


if __name__ == "__main__":
    sys.exit(main())
