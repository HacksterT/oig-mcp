"""Prompts submodule — reusable conversation starters.

Prompts appear in the client UI as slash commands / preset starters. Each
prompt module exposes a `register(mcp)` function; this file aggregates them
into `register_prompts(mcp)`.
"""

from __future__ import annotations

from oig_mcp.prompts import workflows


def register_prompts(mcp) -> None:
    """Register all prompts with the MCP server."""
    workflows.register(mcp)


__all__ = ["register_prompts"]
