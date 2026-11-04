"""Resources submodule — static/semi-static data the client can read directly.

Resources: what the server is and how to cite it, OIG's facet values, and the
facility registry.
"""

from __future__ import annotations

from oig_mcp.resources import about, reference


def register_resources(mcp) -> None:
    """Register all resources with the MCP server."""
    about.register(mcp)
    reference.register(mcp)


__all__ = ["register_resources"]
