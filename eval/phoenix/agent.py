"""The assistant under test, connected only to this server's tools over HTTP.

Claude runs through Anthropic's API (run_question); IBM models run through
watsonx.ai (run_question_watsonx), as IBM's mcp-eval-wxai skill describes.

The system prompt is the server's own `instructions`, which is what any MCP host
receives. Nothing about OIG is added here, because the evaluation measures what the
server gives an assistant that knows nothing else. It connects with the bearer
token, so every run also exercises the deployed authentication path.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from typing import Any

import anthropic
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

MAX_TURNS = 15
MAX_TOKENS = 16000
PREVIEW_CHARS = 1500


def mcp_client(url: str, token: str) -> Client:
    transport = StreamableHttpTransport(
        f"{url.rstrip('/')}/mcp", headers={"Authorization": f"Bearer {token}"}
    )
    return Client(transport, timeout=180)


async def _run_tool(client: Client, name: str, arguments: dict) -> tuple[str, dict]:
    """Call one MCP tool; return its text and a record of the call."""
    started = time.perf_counter()
    result = await client.call_tool(name, arguments, raise_on_error=False)
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    text = "\n".join(
        item.text for item in result.content if getattr(item, "text", None)
    )
    record = {
        "tool": name,
        "arguments": arguments,
        "ms": elapsed_ms,
        "is_error": bool(result.is_error),
        "result_chars": len(text),
        "result_preview": text[:PREVIEW_CHARS],
    }
    return text, record


async def _call_tool(client: Client, block: Any) -> tuple[dict, dict]:
    """Run one Claude tool call; return its API result block and a record."""
    text, record = await _run_tool(client, block.name, block.input)
    api_result = {
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": text or "(empty result)",
        "is_error": record["is_error"],
    }
    return api_result, record


async def run_question(
    question: str,
    *,
    llm: anthropic.AsyncAnthropic,
    model: str,
    effort: str,
    url: str,
    token: str,
) -> dict:
    """Answer one question and return the answer, tool calls, and usage."""
    usage = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
    calls: list[dict] = []
    started = time.perf_counter()
    stop_reason = None
    answer = ""

    async with mcp_client(url, token) as client:
        instructions = client.instructions or ""
        tools = [
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema,
            }
            for tool in await client.list_tools()
        ]
        messages: list[dict] = [{"role": "user", "content": question}]
        for _ in range(MAX_TURNS):
            response = await llm.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                system=instructions,
                tools=tools,
                messages=messages,
                output_config={"effort": effort},
                cache_control={"type": "ephemeral"},
            )
            usage["input"] += response.usage.input_tokens
            usage["output"] += response.usage.output_tokens
            usage["cache_write"] += response.usage.cache_creation_input_tokens or 0
            usage["cache_read"] += response.usage.cache_read_input_tokens or 0
            stop_reason = response.stop_reason
            answer = "\n".join(
                block.text for block in response.content if block.type == "text"
            )
            # Thinking blocks stay in the history, unchanged, as the API requires.
            messages.append({"role": "assistant", "content": response.content})

            if stop_reason == "pause_turn":
                continue
            if stop_reason != "tool_use":
                break
            pending = [b for b in response.content if b.type == "tool_use"]
            outcomes = await asyncio.gather(
                *(_call_tool(client, block) for block in pending)
            )
            calls.extend(record for _, record in outcomes)
            messages.append(
                {"role": "user", "content": [result for result, _ in outcomes]}
            )

    return {
        "answer": answer,
        "tool_calls": calls,
        "stop_reason": stop_reason,
        "usage": usage,
        "seconds": round(time.perf_counter() - started, 1),
    }


def _span(tracer: Any, name: str, kind: str, **attributes: Any):
    """An OpenInference span when tracing, otherwise a no-op."""
    if tracer is None:
        return contextlib.nullcontext(None)
    return tracer.start_as_current_span(
        name,
        attributes={
            "openinference.span.kind": kind,
            **{k: v for k, v in attributes.items() if v is not None},
        },
    )


async def run_question_watsonx(
    question: str,
    *,
    chat: Any,
    model: str,
    url: str,
    token: str,
    tracer: Any = None,
) -> dict:
    """Answer one question with a watsonx.ai model, the same way as run_question.

    The system prompt is the server's own instructions, the tools are the server's,
    and temperature is 0, as the skill sets it. Tool calls run one at a time, in the
    order the model asked for them.
    """
    from watsonx import function_tools

    usage = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
    calls: list[dict] = []
    started = time.perf_counter()
    stop_reason = None
    answer = ""

    with _span(tracer, "question", "AGENT", **{"input.value": question}) as root:
        async with mcp_client(url, token) as client:
            instructions = client.instructions or ""
            tools = function_tools(await client.list_tools())
            messages: list[dict] = [
                {"role": "system", "content": instructions},
                {"role": "user", "content": question},
            ]
            for _ in range(MAX_TURNS):
                with _span(tracer, "chat", "LLM", **{"llm.model_name": model}) as span:
                    response = await chat.chat(model, messages, tools)
                    used = response.get("usage") or {}
                    usage["input"] += used.get("prompt_tokens", 0)
                    usage["output"] += used.get("completion_tokens", 0)
                    if span is not None:
                        span.set_attribute(
                            "llm.token_count.prompt", used.get("prompt_tokens", 0)
                        )
                        span.set_attribute(
                            "llm.token_count.completion",
                            used.get("completion_tokens", 0),
                        )
                choice = response["choices"][0]
                message = choice.get("message") or {}
                stop_reason = choice.get("finish_reason")
                content = message.get("content") or ""
                tool_calls = message.get("tool_calls") or []
                if content:
                    answer = content
                assistant: dict[str, Any] = {"role": "assistant", "content": content}
                if tool_calls:
                    assistant["tool_calls"] = tool_calls
                messages.append(assistant)
                if not tool_calls:
                    break
                for call in tool_calls:
                    function = call.get("function") or {}
                    name = function.get("name", "")
                    raw = function.get("arguments") or "{}"
                    try:
                        arguments = json.loads(raw) if isinstance(raw, str) else raw
                    except json.JSONDecodeError:
                        arguments = None
                    if not isinstance(arguments, dict):
                        text = f"Arguments were not valid JSON: {str(raw)[:200]}"
                        record = {
                            "tool": name,
                            "arguments": {"_unparsed": str(raw)[:PREVIEW_CHARS]},
                            "ms": 0,
                            "is_error": True,
                            "result_chars": 0,
                            "result_preview": text,
                        }
                    else:
                        with _span(
                            tracer,
                            name or "tool",
                            "TOOL",
                            **{"tool.name": name, "input.value": json.dumps(arguments)},
                        ) as span:
                            text, record = await _run_tool(client, name, arguments)
                            if span is not None:
                                span.set_attribute("output.value", text[:PREVIEW_CHARS])
                    calls.append(record)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id", ""),
                            "content": text or "(empty result)",
                        }
                    )
        if root is not None:
            root.set_attribute("output.value", answer)

    return {
        "answer": answer,
        "tool_calls": calls,
        "stop_reason": stop_reason,
        "usage": usage,
        "seconds": round(time.perf_counter() - started, 1),
    }


async def preflight(url: str, token: str, snapshot: dict) -> None:
    """Refuse to score against data other than the pinned snapshot."""
    async with mcp_client(url, token) as client:
        result = await client.call_tool("vaoig_get_dataset_status", {})
    status = json.loads(result.content[0].text)
    counts = status.get("counts", {})
    observed = {
        "data_as_of": status.get("data_as_of"),
        "reports": counts.get("reports"),
        "recommendations": counts.get("recommendations"),
        "open": counts.get("open"),
        "facilities": counts.get("facilities"),
        "inspections": counts.get("inspections"),
        "facility_responses": counts.get("facility_responses"),
    }
    expected = {key: snapshot[key] for key in observed}
    if observed != expected:
        raise SystemExit(
            f"The server's data does not match the pinned snapshot: {observed} "
            f"against {expected}. Gold answers would not apply."
        )
