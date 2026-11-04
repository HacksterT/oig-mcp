"""MCP server entry point.

Keep this file THIN. It only:
  1. creates the FastMCP instance,
  2. registers tools / prompts / resources / routes from the submodules, and
  3. decides which transport to run (stdio locally vs. HTTP when deployed).

All real logic lives in the submodules:
  - tools/      one file per tool (each exposes `register(mcp)`)
  - prompts/    reusable conversation starters
  - resources/  static/semi-static data the client can read directly
  - routes.py   HTTP-only infrastructure (health check, etc.)
  - config.py   settings loaded from env vars / .env
  - models.py   Pydantic models & enums for tool parameters
  - utils.py    shared helpers (HTTP client, formatting, pagination)
"""

from __future__ import annotations

import os

import fastmcp
from fastmcp import FastMCP

from oig_mcp.auth import SharedTokenVerifier
from oig_mcp.config import settings
from oig_mcp.prompts import register_prompts
from oig_mcp.resources import register_resources
from oig_mcp.routes import register_routes
from oig_mcp.tools import register_tools

# The startup banner checks PyPI for a newer FastMCP. Turn it off, so the data API
# really is the only origin this server contacts.
fastmcp.settings.show_server_banner = False
fastmcp.settings.check_for_updates = "off"

# The server name is what MCP clients display.
mcp = FastMCP(
    name="VA OIG Recommendations",
    instructions=(
        "Answers questions across VA Office of Inspector General reports and "
        "recommendations using a structured copy of what OIG publishes at "
        "vaoig.gov. Cite the report number and link for every finding, state "
        "the data_as_of date, and flag stale data. Read vaoig://about for the "
        "data's scope and citation rules. Start with vaoig_get_dataset_status "
        "when current status matters. Use search to find findings and the "
        "analysis tool to count them; a search total is never a count. Pass on "
        "any caveat or basis text a tool returns."
    ),
    auth=SharedTokenVerifier(settings.mcp_auth_token)
    if settings.mcp_auth_token
    else None,
)

# Wire up everything the server exposes. Each aggregator lives in its submodule.
register_tools(mcp)
register_prompts(mcp)
register_resources(mcp)
register_routes(mcp)


def _require_http_auth() -> None:
    """Refuse to expose /mcp without a token, so a bad deploy cannot start open."""
    if not settings.mcp_auth_token:
        raise SystemExit(
            "MCP_AUTH_TOKEN must be set to serve over HTTP. "
            "Generate one with: openssl rand -hex 32"
        )


def main() -> None:
    """Start the server, choosing a transport based on the environment.

    Precedence:
      1. A platform-injected `PORT` (IBM Code Engine sets this) → run HTTP on
         that port.
      2. `MCP_TRANSPORT=streamable-http` in the environment → run HTTP on
         `MCP_HOST`:`MCP_PORT` (see config.py / .env).
      3. Otherwise → stdio, which is how local clients (Claude Desktop, Claude
         Code, Zed) launch the server as a subprocess.

    Both HTTP paths require MCP_AUTH_TOKEN. Stdio does not use it.

    HTTP runs stateless. Every tool is a read-only request and response, so no
    session is needed, and a session kept in memory would break whenever the
    platform restarted the container or sent a request to a second instance.
    """
    platform_port = os.getenv("PORT")

    if platform_port:
        _require_http_auth()
        mcp.run(
            transport="http",
            host="0.0.0.0",
            port=int(platform_port),
            stateless_http=True,
        )
    elif settings.mcp_transport == "streamable-http":
        _require_http_auth()
        mcp.run(
            transport="streamable-http",
            host=settings.mcp_host,
            port=settings.mcp_port,
            stateless_http=True,
        )
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
