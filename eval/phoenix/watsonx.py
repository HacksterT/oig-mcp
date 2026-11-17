"""watsonx.ai chat with tool calling, for running the agent on IBM's models.

IBM's mcp-eval-wxai skill drives the agent through LangChain's ChatWatsonx. This
calls the same watsonx.ai chat endpoint directly, so the harness needs no LangChain.
Credentials use the skill's names: WATSONX_URL, WATSONX_API_KEY, and
WATSONX_PROJECT_ID (or WATSONX_SPACE_ID). The API key is exchanged for an IAM token,
refreshed before it expires, and never logged.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import httpx

IAM_URL = "https://iam.cloud.ibm.com/identity/token"
API_VERSION = "2024-10-10"
DEFAULT_MODEL = "meta-llama/llama-3-3-70b-instruct"
RETRY_STATUSES = {429, 500, 502, 503, 504}


class WatsonxError(RuntimeError):
    """A watsonx.ai request that failed after retries."""


def configured() -> bool:
    """True when the watsonx.ai credentials are present in the environment."""
    return bool(
        os.getenv("WATSONX_URL")
        and os.getenv("WATSONX_API_KEY")
        and (os.getenv("WATSONX_PROJECT_ID") or os.getenv("WATSONX_SPACE_ID"))
    )


def function_tools(mcp_tools: list[Any]) -> list[dict]:
    """MCP tool definitions in the function-calling form the chat API takes."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": getattr(tool, "input_schema", None) or tool.inputSchema,
            },
        }
        for tool in mcp_tools
    ]


class WatsonxChat:
    """One authenticated client for the watsonx.ai chat endpoint."""

    def __init__(self, timeout: float = 180) -> None:
        if not configured():
            raise WatsonxError(
                "Set WATSONX_URL, WATSONX_API_KEY, and WATSONX_PROJECT_ID "
                "(or WATSONX_SPACE_ID) in .env."
            )
        self.base = os.environ["WATSONX_URL"].rstrip("/")
        self._api_key = os.environ["WATSONX_API_KEY"]
        self._scope = (
            {"project_id": os.environ["WATSONX_PROJECT_ID"]}
            if os.getenv("WATSONX_PROJECT_ID")
            else {"space_id": os.environ["WATSONX_SPACE_ID"]}
        )
        self._http = httpx.AsyncClient(timeout=timeout)
        self._token = ""
        self._expires = 0.0
        self._lock = asyncio.Lock()

    async def _bearer(self) -> str:
        async with self._lock:
            if time.time() < self._expires - 120:
                return self._token
            response = await self._http.post(
                IAM_URL,
                data={
                    "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                    "apikey": self._api_key,
                },
                headers={"Accept": "application/json"},
            )
            if response.status_code != 200:
                raise WatsonxError(
                    f"IAM token request failed: HTTP {response.status_code}"
                )
            body = response.json()
            self._token = body["access_token"]
            self._expires = time.time() + float(body.get("expires_in", 3600))
            return self._token

    async def chat(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> dict:
        """One chat completion. Returns the API's JSON response."""
        body: dict[str, Any] = {
            "model_id": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **self._scope,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice_option"] = "auto"
        url = f"{self.base}/ml/v1/text/chat?version={API_VERSION}"
        for attempt in range(4):
            headers = {"Authorization": f"Bearer {await self._bearer()}"}
            response = await self._http.post(url, json=body, headers=headers)
            if response.status_code == 200:
                return response.json()
            if response.status_code in RETRY_STATUSES and attempt < 3:
                await asyncio.sleep(2 ** (attempt + 1))
                continue
            raise WatsonxError(
                f"watsonx.ai chat failed: HTTP {response.status_code}: "
                f"{response.text[:400]}"
            )
        raise WatsonxError("watsonx.ai chat failed after retries")

    async def function_calling_models(self) -> list[str]:
        """Model IDs this region lists for tool calling (a public endpoint)."""
        response = await self._http.get(
            f"{self.base}/ml/v1/foundation_model_specs",
            params={
                "version": API_VERSION,
                "filters": "task_function_calling,!lifecycle_withdrawn:and",
                "limit": 200,
            },
        )
        response.raise_for_status()
        return [r["model_id"] for r in response.json().get("resources", [])]

    async def aclose(self) -> None:
        await self._http.aclose()
