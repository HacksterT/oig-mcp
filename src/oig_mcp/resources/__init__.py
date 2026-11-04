"""Resources submodule — static/semi-static data the client can read directly.

Planned additions: OIG's topic taxonomy, the action-office list, the facility
list with VISN and state, and dataset freshness.
"""

from __future__ import annotations

from oig_mcp.resources import about


def register_resources(mcp) -> None:
    """Register all resources with the MCP server."""
    about.register(mcp)


__all__ = ["register_resources"]
