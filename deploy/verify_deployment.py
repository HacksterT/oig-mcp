"""Check both authenticated connections of a running oig-mcp server from outside.

    Client  --(MCP_AUTH_TOKEN bearer)-->  oig-mcp  --(Cloudflare Access token)-->  API

Run it against the server wherever it is:

    uv run python deploy/verify_deployment.py --url https://<APP_URL>

It needs MCP_AUTH_TOKEN in the environment. If the data API's URL and the Access
token are also set, it tests the API directly too; a clone with no Access token
skips those checks and says so. Secrets are read from the environment or `.env`
and never printed. Exit code 0 means every check that ran passed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

EXPECTED_TOOLS = {
    "vaoig_analyze_recommendations",
    "vaoig_find_systemic_clusters",
    "vaoig_get_dataset_status",
    "vaoig_get_facility_profile",
    "vaoig_get_inspection_brief",
    "vaoig_get_report",
    "vaoig_search_findings",
}
INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "verify-deployment", "version": "0"},
    },
}
MCP_ACCEPT = {"Accept": "application/json, text/event-stream"}


class Report:
    """Collect pass, fail, and skip lines, and the secrets to watch for."""

    def __init__(self, secrets: list[str]) -> None:
        self.failed = 0
        self.passed = 0
        self.secrets = [secret for secret in secrets if secret]

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.passed += ok
        self.failed += not ok
        print(
            f"  {'PASS' if ok else 'FAIL'}  {name}{f'  ({detail})' if detail else ''}"
        )

    def skip(self, name: str, reason: str) -> None:
        print(f"  SKIP  {name}  ({reason})")

    def has_no_secret(self, text: str) -> bool:
        return not any(secret in text for secret in self.secrets)


def load_dotenv(path: Path) -> None:
    """Read KEY=VALUE lines without overriding the environment."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        key, separator, value = line.partition("=")
        key = key.strip()
        if separator and key and not key.startswith("#"):
            os.environ.setdefault(key, value.strip().strip("'\""))


def tool_payload(result) -> dict:
    """The tool's result, from its first text block."""
    return json.loads(result.content[0].text)


def verify_mcp_gate(report: Report, url: str, token: str, access: dict) -> None:
    """Connection 1: who may reach /mcp."""
    print("\nClient to MCP server")
    with httpx.Client(base_url=url, timeout=30, follow_redirects=False) as client:
        for path in ("/health", "/version"):
            response = client.get(path)
            report.check(f"{path} is open", response.status_code == 200)

        def status(headers: dict) -> int:
            return client.post(
                "/mcp", json=INITIALIZE, headers={**MCP_ACCEPT, **headers}
            ).status_code

        refused = {
            "no credentials": {},
            "wrong bearer token": {"Authorization": "Bearer " + "x" * 64},
            "right token, one character short": {
                "Authorization": f"Bearer {token[:-1]}"
            },
            "right token, Basic scheme": {"Authorization": f"Basic {token}"},
            "token in a custom header": {"X-API-Key": token},
        }
        if access:
            refused["Access token headers instead of the bearer token"] = access
            refused["Access secret used as a bearer token"] = {
                "Authorization": f"Bearer {access['CF-Access-Client-Secret']}"
            }
        for name, headers in refused.items():
            got = status(headers)
            report.check(f"refuses {name}", got == 401, f"HTTP {got}")

        # A stateless server has no event stream, so GET returns 405 to anyone.
        # The token in a query string is tested in tests/, not here, because
        # sending it would write the real token into the platform's access log.
        got = client.get("/mcp", headers=MCP_ACCEPT).status_code
        report.check("serves nothing on GET", got in {401, 405}, f"HTTP {got}")

        response = client.post(
            "/mcp",
            json=INITIALIZE,
            headers={**MCP_ACCEPT, "Authorization": f"Bearer {token}"},
        )
        report.check(
            "accepts the right token",
            response.status_code == 200 and "VA OIG Recommendations" in response.text,
            f"HTTP {response.status_code}",
        )
        report.check(
            "keeps no session, so restarts and extra instances are safe",
            "mcp-session-id" not in response.headers,
        )


async def verify_end_to_end(report: Report, url: str, token: str) -> None:
    """Connection 2 as a client sees it: tools that succeed crossed both gates."""
    print("\nMCP server to data API, through the tools")
    transport = StreamableHttpTransport(
        f"{url}/mcp", headers={"Authorization": f"Bearer {token}"}
    )
    async with Client(transport, timeout=120) as client:
        names = {tool.name for tool in await client.list_tools()}
        report.check("tools/list returns the seven tools", names == EXPECTED_TOOLS)

        status = tool_payload(await client.call_tool("vaoig_get_dataset_status", {}))
        text = json.dumps(status)
        report.check(
            "status tool returns live data",
            "error" not in status and bool(status.get("data_as_of")),
            f"data_as_of {status.get('data_as_of')}, or {status.get('error')}",
        )
        report.check("status response carries no secret", report.has_no_secret(text))

        found = tool_payload(
            await client.call_tool(
                "vaoig_search_findings", {"question": "unlocked medication carts"}
            )
        )
        report.check(
            "search returns findings with report links",
            "error" not in found
            and bool(found.get("provenance", {}).get("source_urls")),
            str(found.get("error", "")),
        )
        report.check(
            "search response carries no secret", report.has_no_secret(str(found))
        )


def verify_api_gate(report: Report, api_url: str, token: str, access: dict) -> None:
    """Connection 2 directly: who may reach the data API."""
    print("\nData API, called directly")
    if not api_url or not api_url.startswith("https://") or not access:
        report.skip("direct API checks", "needs the hosted API URL and Access token")
        return
    with httpx.Client(base_url=api_url, timeout=30, follow_redirects=False) as client:
        refused = {
            "no credentials": {},
            "wrong Access token": {
                "CF-Access-Client-Id": "wrong.access",
                "CF-Access-Client-Secret": "wrong",
            },
            "MCP bearer token": {"Authorization": f"Bearer {token}"},
        }
        for name, headers in refused.items():
            response = client.get("meta", headers=headers)
            leaked = "data_as_of" in response.text
            report.check(
                f"refuses {name}",
                response.status_code in {401, 403} and not leaked,
                f"HTTP {response.status_code}",
            )
        response = client.get("meta", headers=access)
        report.check(
            "accepts the Access token",
            response.status_code == 200 and "data_as_of" in response.text,
            f"HTTP {response.status_code}",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", required=True, help="Server base URL, without /mcp")
    args = parser.parse_args()

    load_dotenv(Path(".env"))
    url = args.url.rstrip("/").removesuffix("/mcp")
    token = os.environ.get("MCP_AUTH_TOKEN", "")
    if not token:
        print("MCP_AUTH_TOKEN must be set to the token the server was given.")
        return 2

    client_id = os.environ.get("CF_ACCESS_CLIENT_ID", "")
    client_secret = os.environ.get("CF_ACCESS_CLIENT_SECRET", "")
    access = (
        {"CF-Access-Client-Id": client_id, "CF-Access-Client-Secret": client_secret}
        if client_id and client_secret
        else {}
    )
    report = Report([token, client_id, client_secret])

    verify_mcp_gate(report, url, token, access)
    try:
        asyncio.run(verify_end_to_end(report, url, token))
    except Exception as exc:  # A failed connection is a result here, not a crash.
        report.check("MCP client session", False, type(exc).__name__)
    verify_api_gate(report, os.environ.get("OIG_DATA_API_BASE_URL", ""), token, access)

    print(f"\n{report.passed} passed, {report.failed} failed")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
